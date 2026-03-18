from datetime import date, timedelta

from django.test import TestCase

from pagamento.models import (
    Pagamento,
    PagamentoImplantacao,
    StatusPagamento,
    TipoPagamento,
)
from pagamento.read.serializers import StatusMixin
from pagamento.tests import (
    create_advogado,
    create_cliente,
    create_implantacao,
    create_parcela,
    create_processo,
)


class ProcessoModelTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        self.pagamento_implantacao, _ = create_implantacao(self.processo)
        self.pagamento_implantacao2, _ = create_implantacao(self.processo)
        self.pagamento_parcela, _ = create_parcela(self.processo)
        self.pagamento_entrada, _ = create_parcela(self.processo)
        self.pagamento_entrada.tipo = TipoPagamento.ENTRADA
        self.pagamento_entrada.save()

    def test_get_pagamentos_implantacoes_returns_only_implantacao(self):
        qs = self.processo.get_pagamentos_implantacoes()
        tipos = list(qs.values_list("tipo", flat=True))
        self.assertTrue(all(t == TipoPagamento.IMPLANTACAO for t in tipos))
        self.assertEqual(len(tipos), 2)

    def test_get_pagamentos_parcelas_returns_entrada_and_parcela(self):
        qs = self.processo.get_pagamentos_parcelas()
        tipos = set(qs.values_list("tipo", flat=True))
        self.assertIn(TipoPagamento.PARCELA, tipos)
        self.assertIn(TipoPagamento.ENTRADA, tipos)
        self.assertNotIn(TipoPagamento.IMPLANTACAO, tipos)

    def test_get_pagamentos_implantacoes_select_related_avoids_n_plus_1(self):
        # select_related: iterating related objects after fetch needs 0 extra queries
        pagamentos = list(self.processo.get_pagamentos_implantacoes())
        with self.assertNumQueries(0):
            for p in pagamentos:
                _ = p.implantacao.valor_total

    def test_get_pagamentos_parcelas_select_related_avoids_n_plus_1(self):
        pagamentos = list(self.processo.get_pagamentos_parcelas())
        with self.assertNumQueries(0):
            for p in pagamentos:
                _ = p.parcela.valor_parcela


class PagamentoDetalhesPropertyTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        processo = create_processo(advogado=advogado, cliente=cliente)
        self.pagamento_implantacao, self.implantacao = create_implantacao(processo)
        self.pagamento_parcela, self.parcela = create_parcela(processo)

    def test_detalhes_returns_implantacao_for_implantacao_tipo(self):
        detalhes = self.pagamento_implantacao.detalhes
        self.assertIsInstance(detalhes, PagamentoImplantacao)
        self.assertEqual(detalhes, self.implantacao)

    def test_detalhes_returns_self_for_parcela_tipo(self):
        detalhes = self.pagamento_parcela.detalhes
        self.assertIsInstance(detalhes, Pagamento)
        self.assertEqual(detalhes, self.pagamento_parcela)


class StatusMixinTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        processo = create_processo(advogado=advogado, cliente=cliente)
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)

        _, self.past_planejado = create_implantacao(
            processo,
            data_vencimento=yesterday,
            status=StatusPagamento.PLANEJADO,
        )
        _, self.past_pago = create_implantacao(
            processo,
            data_vencimento=yesterday,
            status=StatusPagamento.PAGO,
        )
        _, self.past_parcialmente = create_implantacao(
            processo,
            data_vencimento=yesterday,
            status=StatusPagamento.PARCIALMENTE_PAGO,
        )
        _, self.future_planejado = create_implantacao(
            processo,
            data_vencimento=tomorrow,
            status=StatusPagamento.PLANEJADO,
        )

    def test_get_status_returns_atrasado_for_past_due_planejado(self):
        mixin = StatusMixin()
        result = mixin.get_status(self.past_planejado)
        self.assertEqual(result, StatusPagamento.ATRASADO)

    def test_get_status_returns_pago_for_past_due_pago(self):
        mixin = StatusMixin()
        result = mixin.get_status(self.past_pago)
        self.assertEqual(result, StatusPagamento.PAGO)

    def test_get_status_returns_parcialmente_pago_for_past_due_parcialmente_pago(self):
        mixin = StatusMixin()
        result = mixin.get_status(self.past_parcialmente)
        self.assertEqual(result, StatusPagamento.PARCIALMENTE_PAGO)

    def test_get_status_returns_planejado_for_future_due_date(self):
        mixin = StatusMixin()
        result = mixin.get_status(self.future_planejado)
        self.assertEqual(result, StatusPagamento.PLANEJADO)
