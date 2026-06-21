from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pagamento.models import PagamentoEvento, StatusPagamento
from pagamento.tests import (
    create_advogado,
    create_implantacao,
    create_parcela,
    create_processo,
    create_superuser,
    create_user,
)
from pessoa.models import Corretor


def create_corretor(advogado, **kwargs):
    defaults = {
        "nome": "Corretor Teste",
        "email": "corretor@example.com",
        "comissao_padrao": Decimal("10.00"),
    }
    defaults.update(kwargs)
    return Corretor.objects.create(advogado=advogado, **defaults)


def create_evento(pagamento, valor_recebido, data_pagamento):
    return PagamentoEvento.objects.create(
        pagamento=pagamento,
        valor_recebido=valor_recebido,
        data_pagamento=data_pagamento,
    )


class RelatorioRecolhimentoAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("relatorio_recolhimento")
        self.superuser = create_superuser()
        self.user = create_user()
        # advogado with comissao_padrao=30% (default from create_advogado)
        self.advogado = create_advogado()

    def test_recolhimento_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_recolhimento_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recolhimento_returns_planejado_pagamentos(self):
        """PLANEJADO payments appear in the result."""
        processo = create_processo(advogado=self.advogado)
        pagamento, _ = create_implantacao(
            processo,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["advogados"]), 1)
        self.assertEqual(len(response.data["advogados"][0]["pagamentos"]), 1)
        self.assertEqual(
            response.data["advogados"][0]["pagamentos"][0]["pagamento_id"],
            pagamento.id,
        )

    def test_recolhimento_returns_parcialmente_pago_pagamentos(self):
        """PARCIALMENTE_PAGO payments appear in the result."""
        processo = create_processo(advogado=self.advogado)
        pagamento, _ = create_implantacao(
            processo,
            status=StatusPagamento.PARCIALMENTE_PAGO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["advogados"]), 1)
        self.assertEqual(
            response.data["advogados"][0]["pagamentos"][0]["pagamento_id"],
            pagamento.id,
        )
        self.assertEqual(
            response.data["advogados"][0]["pagamentos"][0]["status"],
            StatusPagamento.PARCIALMENTE_PAGO,
        )

    def test_recolhimento_excludes_pago_pagamentos(self):
        """PAGO payments are not returned."""
        processo = create_processo(advogado=self.advogado)
        create_implantacao(
            processo,
            status=StatusPagamento.PAGO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["advogados"], [])

    def test_recolhimento_filter_by_advogado_id(self):
        """Only pagamentos for the given advogado_id are returned."""
        advogado2 = create_advogado(
            nome="Outro Advogado",
            oab_numero="999999",
            email="outro@example.com",
        )
        processo1 = create_processo(advogado=self.advogado)
        processo2 = create_processo(advogado=advogado2)
        create_implantacao(
            processo1,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        create_implantacao(
            processo2,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url,
            {
                "data_inicio": "2025-01-01",
                "data_fim": "2025-01-31",
                "advogado_id": self.advogado.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["advogados"]), 1)
        self.assertEqual(response.data["advogados"][0]["id"], self.advogado.id)

    def test_recolhimento_filter_by_date_range(self):
        """Only pagamentos with data_vencimento within the range are returned."""
        processo = create_processo(advogado=self.advogado)
        # inside range
        create_implantacao(
            processo,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        # outside range
        create_implantacao(
            processo,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 3, 1),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["advogados"][0]["pagamentos"]), 1)

    def test_recolhimento_without_corretor(self):
        """When processo has no corretor, corretor fields are null."""
        processo = create_processo(advogado=self.advogado)
        create_implantacao(
            processo,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pagamento_data = response.data["advogados"][0]["pagamentos"][0]
        self.assertIsNone(pagamento_data["corretor_nome"])
        self.assertIsNone(pagamento_data["comissao_corretor_porcentagem"])
        self.assertIsNone(pagamento_data["comissao_corretor_valor"])

    def test_recolhimento_with_corretor(self):
        """When processo has a corretor, corretor fields are populated."""
        corretor = create_corretor(self.advogado)
        processo = create_processo(advogado=self.advogado, corretor=corretor)
        create_implantacao(
            processo,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pagamento_data = response.data["advogados"][0]["pagamentos"][0]
        self.assertEqual(pagamento_data["corretor_nome"], corretor.nome)
        self.assertIsNotNone(pagamento_data["comissao_corretor_porcentagem"])
        self.assertIsNotNone(pagamento_data["comissao_corretor_valor"])

    def test_recolhimento_commission_implantacao(self):
        """
        IMPLANTACAO with corretor:
          valor_beneficio=1000, porcentagem_escritorio=30% → office amount = 300
          advogado=30%, corretor=10%
          escritorio_base = valor_pendente = 300, corretor_valor = 30, restante = 270
          advogado_valor = 81, escritorio_liquido = 189
        """
        corretor = create_corretor(self.advogado, comissao_padrao=Decimal("10.00"))
        processo = create_processo(advogado=self.advogado, corretor=corretor)
        create_implantacao(
            processo,
            valor_beneficio=Decimal("1000.00"),
            porcentagem_escritorio=Decimal("30.00"),
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pagamento_data = response.data["advogados"][0]["pagamentos"][0]
        self.assertEqual(pagamento_data["tipo"], "IMPLANTACAO")
        self.assertEqual(pagamento_data["valor_pendente"], Decimal("300.00"))
        self.assertEqual(
            pagamento_data["comissao_advogado_porcentagem"], Decimal("30.00")
        )
        self.assertEqual(pagamento_data["comissao_advogado_valor"], Decimal("81.00"))
        self.assertEqual(pagamento_data["valor_escritorio"], Decimal("189.00"))
        self.assertEqual(
            pagamento_data["comissao_corretor_porcentagem"], Decimal("10.00")
        )
        self.assertEqual(pagamento_data["comissao_corretor_valor"], Decimal("30.00"))

    def test_recolhimento_commission_contrato(self):
        """
        CONTRATO_PARCELA with corretor:
          valor_parcela=1000, advogado=30%, corretor=10%
          corretor_valor = 100, restante = 900
          advogado_valor = 270, escritorio_liquido = 630
        """
        corretor = create_corretor(self.advogado, comissao_padrao=Decimal("10.00"))
        processo = create_processo(advogado=self.advogado, corretor=corretor)
        create_parcela(
            processo,
            valor_parcela=Decimal("1000.00"),
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pagamento_data = response.data["advogados"][0]["pagamentos"][0]
        self.assertEqual(pagamento_data["tipo"], "CONTRATO_PARCELA")
        self.assertEqual(pagamento_data["valor_pendente"], Decimal("1000.00"))
        self.assertEqual(
            pagamento_data["comissao_advogado_porcentagem"], Decimal("30.00")
        )
        self.assertEqual(pagamento_data["comissao_advogado_valor"], Decimal("270.00"))
        self.assertEqual(pagamento_data["valor_escritorio"], Decimal("630.00"))
        self.assertEqual(
            pagamento_data["comissao_corretor_porcentagem"], Decimal("10.00")
        )
        self.assertEqual(pagamento_data["comissao_corretor_valor"], Decimal("100.00"))

    def test_recolhimento_valor_pendente_parcialmente_pago(self):
        """
        PARCIALMENTE_PAGO: valor_pendente = office amount - soma dos eventos.
          valor_beneficio=1000, porcentagem_escritorio=30% → office amount = 300
          received=180 → valor_pendente=120
          advogado=30%, no corretor:
          escritorio_base = 120, restante = 120
          advogado_valor = 36, escritorio_liquido = 84
        """
        processo = create_processo(advogado=self.advogado)
        pagamento, _ = create_implantacao(
            processo,
            valor_beneficio=Decimal("1000.00"),
            porcentagem_escritorio=Decimal("30.00"),
            status=StatusPagamento.PARCIALMENTE_PAGO,
            data_vencimento=date(2025, 1, 15),
        )
        create_evento(pagamento, Decimal("180.00"), date(2025, 1, 10))
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pagamento_data = response.data["advogados"][0]["pagamentos"][0]
        self.assertEqual(pagamento_data["valor_pendente"], Decimal("120.00"))
        self.assertEqual(pagamento_data["comissao_advogado_valor"], Decimal("36.00"))
        self.assertEqual(pagamento_data["valor_escritorio"], Decimal("84.00"))

    def test_recolhimento_total_recolhimento_aggregated(self):
        """
        total_recolhimento = sum of valor_escritorio across all pagamentos.
          pag1: valor_beneficio=1000, pct_esc=30% → office 300, adv=30% → escritorio=210
          pag2: valor_beneficio=500,  pct_esc=30% → office 150, adv=30% → escritorio=105
          total = 315
        """
        processo = create_processo(advogado=self.advogado)
        create_implantacao(
            processo,
            valor_beneficio=Decimal("1000.00"),
            porcentagem_escritorio=Decimal("30.00"),
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 15),
        )
        create_implantacao(
            processo,
            valor_beneficio=Decimal("500.00"),
            porcentagem_escritorio=Decimal("30.00"),
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2025, 1, 20),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["advogados"][0]["total_recolhimento"], Decimal("315.00")
        )

    def test_recolhimento_no_date_filter_returns_all(self):
        """No date params → all PLANEJADO/PARCIALMENTE_PAGO pagamentos are returned,
        regardless of data_vencimento month or year."""
        processo = create_processo(advogado=self.advogado)
        # two pagamentos in completely different months
        create_implantacao(
            processo,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2020, 3, 1),
        )
        create_implantacao(
            processo,
            status=StatusPagamento.PLANEJADO,
            data_vencimento=date(2030, 11, 15),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["advogados"][0]["pagamentos"]), 2)
        self.assertIsNone(response.data["periodo"]["inicio"])
        self.assertIsNone(response.data["periodo"]["fim"])
