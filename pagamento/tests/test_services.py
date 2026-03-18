from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from pagamento.models import (
    PagamentoEvento,
    PagamentoImplantacao,
    StatusPagamento,
    TipoPagamento,
)
from pagamento.services.pagamento_service import (
    PagamentoEventoService,
    PagamentoService,
)
from pagamento.tests import (
    create_advogado,
    create_cliente,
    create_implantacao,
    create_parcela,
    create_processo,
)


class PagamentoEventoServiceTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        processo = create_processo(advogado=advogado, cliente=cliente)
        self.pagamento, self.implantacao = create_implantacao(processo)

    def test_calcular_total_pago_returns_zero_with_no_events(self):
        total = PagamentoEventoService.calcular_total_pago(self.pagamento)
        self.assertEqual(total, 0)

    def test_calcular_total_pago_sums_single_event(self):
        PagamentoEvento.objects.create(
            pagamento=self.pagamento,
            valor_recebido=Decimal("500.00"),
            data_pagamento=date(2025, 1, 1),
        )
        total = PagamentoEventoService.calcular_total_pago(self.pagamento)
        self.assertEqual(total, Decimal("500.00"))

    def test_calcular_total_pago_sums_multiple_events(self):
        PagamentoEvento.objects.create(
            pagamento=self.pagamento,
            valor_recebido=Decimal("300.00"),
            data_pagamento=date(2025, 1, 1),
        )
        PagamentoEvento.objects.create(
            pagamento=self.pagamento,
            valor_recebido=Decimal("200.00"),
            data_pagamento=date(2025, 1, 2),
        )
        total = PagamentoEventoService.calcular_total_pago(self.pagamento)
        self.assertEqual(total, Decimal("500.00"))

    def test_calcular_total_pago_ignores_other_pagamento_events(self):
        advogado2 = create_advogado(
            nome="Outro Adv", oab_numero="999", email="outro@example.com"
        )
        processo2 = create_processo(advogado=advogado2)
        outro_pagamento, _ = create_implantacao(processo2)
        PagamentoEvento.objects.create(
            pagamento=outro_pagamento,
            valor_recebido=Decimal("500.00"),
            data_pagamento=date(2025, 1, 1),
        )
        total = PagamentoEventoService.calcular_total_pago(self.pagamento)
        self.assertEqual(total, 0)

    def test_criar_evento_pagamento_persists_record(self):
        PagamentoEventoService.criar_evento_pagamento(
            self.pagamento, Decimal("400.00"), date(2025, 1, 1)
        )
        self.assertEqual(PagamentoEvento.objects.count(), 1)
        evento = PagamentoEvento.objects.first()
        self.assertEqual(evento.valor_recebido, Decimal("400.00"))
        self.assertEqual(evento.pagamento, self.pagamento)


class PagamentoServiceValidacaoTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        processo = create_processo(advogado=advogado, cliente=cliente)
        self.pagamento, self.implantacao = create_implantacao(processo)
        self.pagamento_parcela, self.parcela = create_parcela(processo)

    def test_validar_raises_if_already_pago(self):
        self.implantacao.status = StatusPagamento.PAGO
        self.implantacao.save()
        with self.assertRaises(ValidationError) as ctx:
            PagamentoService._validar_pagamento(self.implantacao, Decimal("100.00"), 0)
        self.assertIn("status", ctx.exception.detail)

    def test_validar_raises_if_overpayment_implantacao(self):
        # historico=800 + valor_pago=300 = 1100 > valor_total=1000
        with self.assertRaises(ValidationError) as ctx:
            PagamentoService._validar_pagamento(
                self.implantacao, Decimal("300.00"), Decimal("800.00")
            )
        self.assertIn("erro", ctx.exception.detail)

    def test_validar_raises_if_overpayment_parcela(self):
        # historico=400 + valor_pago=200 = 600 > valor_parcela=500
        with self.assertRaises(ValidationError) as ctx:
            PagamentoService._validar_pagamento(
                self.parcela, Decimal("200.00"), Decimal("400.00")
            )
        self.assertIn("erro", ctx.exception.detail)

    def test_validar_passes_exact_payment(self):
        # historico=0 + valor_pago=1000 == valor_total=1000 — no exception
        PagamentoService._validar_pagamento(
            self.implantacao, Decimal("1000.00"), Decimal("0.00")
        )

    def test_validar_passes_partial_payment(self):
        # historico=0 + valor_pago=500 < 1000 — no exception
        PagamentoService._validar_pagamento(
            self.implantacao, Decimal("500.00"), Decimal("0.00")
        )


class PagamentoServicePagarImplantacaoTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        processo = create_processo(advogado=advogado, cliente=cliente)
        self.pagamento, self.implantacao = create_implantacao(processo)

    def test_full_payment_sets_status_pago(self):
        PagamentoService.pagar(self.pagamento, Decimal("1000.00"), date(2025, 1, 1))
        self.implantacao.refresh_from_db()
        self.assertEqual(self.implantacao.status, StatusPagamento.PAGO)

    def test_partial_payment_sets_status_parcialmente_pago(self):
        PagamentoService.pagar(self.pagamento, Decimal("500.00"), date(2025, 1, 1))
        self.implantacao.refresh_from_db()
        self.assertEqual(self.implantacao.status, StatusPagamento.PARCIALMENTE_PAGO)

    def test_payment_creates_evento(self):
        PagamentoService.pagar(self.pagamento, Decimal("500.00"), date(2025, 1, 1))
        self.assertEqual(
            PagamentoEvento.objects.filter(pagamento=self.pagamento).count(), 1
        )

    def test_second_partial_completes_payment(self):
        PagamentoService.pagar(self.pagamento, Decimal("600.00"), date(2025, 1, 1))
        PagamentoService.pagar(self.pagamento, Decimal("400.00"), date(2025, 1, 2))
        self.implantacao.refresh_from_db()
        self.assertEqual(self.implantacao.status, StatusPagamento.PAGO)
        self.assertEqual(
            PagamentoEvento.objects.filter(pagamento=self.pagamento).count(), 2
        )

    def test_raises_if_already_pago(self):
        PagamentoService.pagar(self.pagamento, Decimal("1000.00"), date(2025, 1, 1))
        with self.assertRaises(ValidationError):
            PagamentoService.pagar(self.pagamento, Decimal("100.00"), date(2025, 1, 2))

    def test_rollback_on_error(self):
        with patch.object(
            PagamentoImplantacao, "save", side_effect=Exception("forced error")
        ):
            with self.assertRaises(Exception):
                PagamentoService.pagar(
                    self.pagamento, Decimal("500.00"), date(2025, 1, 1)
                )
        self.assertEqual(PagamentoEvento.objects.count(), 0)


class PagamentoServicePagarParcelaTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        self.pagamento, self.parcela = create_parcela(
            self.processo, valor_parcela=Decimal("500.00")
        )

    def test_full_payment_sets_status_pago(self):
        PagamentoService.pagar(self.pagamento, Decimal("500.00"), date(2025, 1, 1))
        self.parcela.refresh_from_db()
        self.assertEqual(self.parcela.status, StatusPagamento.PAGO)

    def test_partial_payment_sets_status_parcialmente_pago(self):
        PagamentoService.pagar(self.pagamento, Decimal("300.00"), date(2025, 1, 1))
        self.parcela.refresh_from_db()
        self.assertEqual(self.parcela.status, StatusPagamento.PARCIALMENTE_PAGO)

    def test_payment_creates_evento(self):
        PagamentoService.pagar(self.pagamento, Decimal("500.00"), date(2025, 1, 1))
        self.assertEqual(
            PagamentoEvento.objects.filter(pagamento=self.pagamento).count(), 1
        )

    def test_entrada_full_payment_sets_status_pago(self):
        from pagamento.models import TipoParcela

        pagamento_entrada, parcela_entrada = create_parcela(
            self.processo,
            valor_parcela=Decimal("200.00"),
            tipo=TipoParcela.ENTRADA,
        )
        # Override pagamento tipo to ENTRADA
        pagamento_entrada.tipo = TipoPagamento.ENTRADA
        pagamento_entrada.save()

        PagamentoService.pagar(pagamento_entrada, Decimal("200.00"), date(2025, 1, 1))
        parcela_entrada.refresh_from_db()
        self.assertEqual(parcela_entrada.status, StatusPagamento.PAGO)

    def test_unsupported_tipo_raises_validation_error(self):
        from pagamento.models import Pagamento

        pagamento_invalido = Pagamento.objects.create(
            processo=self.processo, tipo=TipoPagamento.IMPLANTACAO
        )
        # Create pagamento without the required OneToOne implantacao
        # so accessing .implantacao raises — simulate unsupported type by patching tipo
        with patch.object(
            type(pagamento_invalido),
            "tipo",
            new_callable=lambda: property(lambda self: "TIPO_INVALIDO"),
        ):
            with self.assertRaises(ValidationError) as ctx:
                PagamentoService.pagar(
                    pagamento_invalido, Decimal("100.00"), date(2025, 1, 1)
                )
            self.assertIn("tipo", ctx.exception.detail)
