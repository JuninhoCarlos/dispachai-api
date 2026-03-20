from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from pagamento.models import PagamentoEvento
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
        "comissao_padrao": Decimal("20.00"),
    }
    defaults.update(kwargs)
    return Corretor.objects.create(advogado=advogado, **defaults)


def create_evento(pagamento, valor_recebido, data_pagamento):
    return PagamentoEvento.objects.create(
        pagamento=pagamento,
        valor_recebido=valor_recebido,
        data_pagamento=data_pagamento,
    )


class RelatorioReceitaAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("relatorio_receita")
        self.superuser = create_superuser()
        self.user = create_user()
        # advogado with comissao_padrao=30% (default from create_advogado)
        self.advogado = create_advogado()
        # corretor with comissao_padrao=20%
        self.corretor = create_corretor(self.advogado)

    def test_relatorio_receita_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_relatorio_receita_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_relatorio_receita_empty_period(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_receita"], Decimal("0.00"))
        self.assertEqual(response.data["escritorio"]["total_comissao"], Decimal("0.00"))
        self.assertEqual(response.data["advogados"], [])
        self.assertEqual(response.data["corretores"], [])

    def test_relatorio_receita_implantacao_uses_porcentagem_escritorio(self):
        """receita for IMPLANTACAO = valor_recebido × (porcentagem_escritorio / 100)."""
        processo = create_processo(advogado=self.advogado)
        pagamento, _ = create_implantacao(
            processo,
            valor_total=Decimal("1000.00"),
            porcentagem_escritorio=Decimal("50.00"),
            data_vencimento=date(2025, 1, 1),
        )
        create_evento(pagamento, Decimal("500.00"), date(2025, 1, 15))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pagamento_entry = response.data["advogados"][0]["processos"][0]["pagamentos"][0]
        # base = 500 × 0.50 = 250
        self.assertEqual(pagamento_entry["receita"], Decimal("250.00"))
        self.assertEqual(pagamento_entry["pagamento_id"], pagamento.id)
        self.assertEqual(pagamento_entry["tipo"], "IMPLANTACAO")

    def test_relatorio_receita_contrato_uses_full_valor_recebido(self):
        """receita for PARCELA = valor_recebido (entire received amount)."""
        processo = create_processo(advogado=self.advogado)
        pagamento, _ = create_parcela(
            processo,
            valor_parcela=Decimal("500.00"),
            data_vencimento=date(2025, 1, 1),
        )
        create_evento(pagamento, Decimal("300.00"), date(2025, 1, 20))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pagamento_entry = response.data["advogados"][0]["processos"][0]["pagamentos"][0]
        self.assertEqual(pagamento_entry["receita"], Decimal("300.00"))
        self.assertIn(pagamento_entry["tipo"], ["CONTRATO_PARCELA", "CONTRATO_ENTRADA"])

    def test_relatorio_receita_uses_comissao_ajustada_when_set(self):
        """comissao_porcentagem uses comissao_ajustada_advogado when set on processo."""
        processo = create_processo(
            advogado=self.advogado,
            comissao_ajustada_advogado=Decimal("25.00"),
        )
        pagamento, _ = create_implantacao(
            processo,
            valor_total=Decimal("1000.00"),
            porcentagem_escritorio=Decimal("40.00"),
            data_vencimento=date(2025, 1, 1),
        )
        create_evento(pagamento, Decimal("1000.00"), date(2025, 1, 10))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pagamento_entry = response.data["advogados"][0]["processos"][0]["pagamentos"][0]
        self.assertEqual(pagamento_entry["comissao_porcentagem"], Decimal("25.00"))

    def test_relatorio_receita_falls_back_to_comissao_padrao(self):
        """comissao_porcentagem falls back to advogado.comissao_padrao."""
        processo = create_processo(
            advogado=self.advogado
        )  # no comissao_ajustada_advogado
        pagamento, _ = create_implantacao(
            processo,
            data_vencimento=date(2025, 1, 1),
        )
        create_evento(pagamento, Decimal("100.00"), date(2025, 1, 5))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pagamento_entry = response.data["advogados"][0]["processos"][0]["pagamentos"][0]
        self.assertEqual(
            pagamento_entry["comissao_porcentagem"], self.advogado.comissao_padrao
        )

    def test_relatorio_receita_implantacao_commission_rules(self):
        """
        Implantação rule: corretor takes % of advogado's gross, not of escritorio_base.

        escritorio_base = 500 × 50% = 250
        advogado_bruto  = 250 × 30% = 75
        corretor        = 75  × 20% = 15   ← % of advogado's gross
        advogado_net    = 75 - 15   = 60
        escritorio      = 250 - 75  = 175  ← keeps base minus advogado's gross
        """
        processo = create_processo(advogado=self.advogado, corretor=self.corretor)
        pagamento, _ = create_implantacao(
            processo,
            valor_total=Decimal("1000.00"),
            porcentagem_escritorio=Decimal("50.00"),
            data_vencimento=date(2025, 1, 1),
        )
        create_evento(pagamento, Decimal("500.00"), date(2025, 1, 15))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data["total_receita"], Decimal("250.00"))
        self.assertEqual(data["escritorio"]["total_comissao"], Decimal("175.00"))
        self.assertEqual(data["advogados"][0]["total_comissao"], Decimal("60.00"))
        self.assertEqual(data["corretores"][0]["total_comissao"], Decimal("15.00"))

        # Verify periodo is echoed
        self.assertEqual(data["periodo"]["inicio"], "2025-01-01")
        self.assertEqual(data["periodo"]["fim"], "2025-01-31")

        # Advogado entry: receita = escritorio_base; comissao_valor = net
        adv_entry = data["advogados"][0]
        self.assertEqual(adv_entry["id"], self.advogado.id)
        self.assertEqual(adv_entry["nome"], self.advogado.nome)

        adv_pag = adv_entry["processos"][0]["pagamentos"][0]
        self.assertEqual(adv_pag["pagamento_id"], pagamento.id)
        self.assertEqual(adv_pag["tipo"], "IMPLANTACAO")
        self.assertEqual(adv_pag["receita"], Decimal("250.00"))  # escritorio_base
        self.assertEqual(adv_pag["comissao_porcentagem"], Decimal("30.00"))
        self.assertEqual(adv_pag["comissao_valor"], Decimal("60.00"))  # net

        # Corretor entry: receita = advogado_bruto; valor = advogado_bruto × corretor%
        cor_pag = data["corretores"][0]["processos"][0]["pagamentos"][0]
        self.assertEqual(cor_pag["receita"], Decimal("75.00"))  # advogado_bruto
        self.assertEqual(cor_pag["comissao_porcentagem"], Decimal("20.00"))
        self.assertEqual(cor_pag["comissao_valor"], Decimal("15.00"))  # 75 × 20%

    def test_relatorio_receita_contrato_commission_rules(self):
        """
        Contrato rule: corretor takes % of total first; advogado takes % of remaining.

        total           = 100
        corretor        = 100 × 20% = 20
        restante        = 80
        advogado        = 80  × 30% = 24
        escritorio      = 80  - 24  = 56
        """
        processo = create_processo(advogado=self.advogado, corretor=self.corretor)
        pagamento, _ = create_parcela(
            processo,
            valor_parcela=Decimal("1000.00"),
            data_vencimento=date(2025, 1, 1),
        )
        create_evento(pagamento, Decimal("100.00"), date(2025, 1, 15))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data["total_receita"], Decimal("100.00"))
        self.assertEqual(data["escritorio"]["total_comissao"], Decimal("56.00"))
        self.assertEqual(data["advogados"][0]["total_comissao"], Decimal("24.00"))
        self.assertEqual(data["corretores"][0]["total_comissao"], Decimal("20.00"))

        # Advogado entry: receita = restante (after corretor deduction)
        adv_pag = data["advogados"][0]["processos"][0]["pagamentos"][0]
        self.assertEqual(adv_pag["receita"], Decimal("80.00"))  # restante
        self.assertEqual(adv_pag["comissao_porcentagem"], Decimal("30.00"))
        self.assertEqual(adv_pag["comissao_valor"], Decimal("24.00"))  # 80 × 30%

        # Corretor entry: receita = total_recebido
        cor_pag = data["corretores"][0]["processos"][0]["pagamentos"][0]
        self.assertEqual(cor_pag["receita"], Decimal("100.00"))  # total_recebido
        self.assertEqual(cor_pag["comissao_porcentagem"], Decimal("20.00"))
        self.assertEqual(cor_pag["comissao_valor"], Decimal("20.00"))  # 100 × 20%

    def test_relatorio_receita_default_to_current_month(self):
        """With no date params, defaults to current month."""
        today = timezone.now().date()
        processo = create_processo(advogado=self.advogado)
        pagamento, _ = create_implantacao(processo, data_vencimento=today)
        create_evento(pagamento, Decimal("100.00"), today)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)  # no params
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        first_of_month = today.replace(day=1).isoformat()
        self.assertEqual(response.data["periodo"]["inicio"], first_of_month)
        self.assertGreater(len(response.data["advogados"]), 0)

    def test_relatorio_receita_filter_by_advogado(self):
        """Only returns data for the specified advogado."""
        advogado2 = create_advogado(
            nome="Outro Advogado",
            oab_numero="999",
            email="outro@example.com",
        )
        processo1 = create_processo(advogado=self.advogado)
        processo2 = create_processo(advogado=advogado2)
        pagamento1, _ = create_implantacao(processo1, data_vencimento=date(2025, 1, 1))
        pagamento2, _ = create_implantacao(processo2, data_vencimento=date(2025, 1, 1))
        create_evento(pagamento1, Decimal("100.00"), date(2025, 1, 10))
        create_evento(pagamento2, Decimal("200.00"), date(2025, 1, 10))

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

    def test_relatorio_receita_excludes_events_outside_range(self):
        """Events outside the date range are not counted."""
        processo = create_processo(advogado=self.advogado)
        pagamento, _ = create_implantacao(
            processo,
            porcentagem_escritorio=Decimal("30.00"),
            data_vencimento=date(2025, 1, 1),
        )
        # Inside range
        create_evento(pagamento, Decimal("100.00"), date(2025, 1, 15))
        # Outside range — must be excluded
        create_evento(pagamento, Decimal("999.00"), date(2025, 2, 1))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Only the 100 event counted: base = 100 × 0.30 = 30
        pag_entry = response.data["advogados"][0]["processos"][0]["pagamentos"][0]
        self.assertEqual(pag_entry["receita"], Decimal("30.00"))

    def test_relatorio_receita_processo_without_corretor(self):
        """corretores list is empty when no processo has a corretor."""
        processo = create_processo(advogado=self.advogado)  # no corretor
        pagamento, _ = create_implantacao(processo, data_vencimento=date(2025, 1, 1))
        create_evento(pagamento, Decimal("100.00"), date(2025, 1, 15))

        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"data_inicio": "2025-01-01", "data_fim": "2025-01-31"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["corretores"], [])
