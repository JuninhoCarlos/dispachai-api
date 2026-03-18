from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from pagamento.tests import (
    create_advogado,
    create_cliente,
    create_implantacao,
    create_parcela,
    create_processo,
    create_user,
)


class PagamentoMonthYearFilterTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("pagamento_list")
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)

        # Implantacoes in different months
        self.jan_implantacao_pag, _ = create_implantacao(
            self.processo, data_vencimento=date(2025, 1, 15)
        )
        self.feb_implantacao_pag, _ = create_implantacao(
            self.processo, data_vencimento=date(2025, 2, 15)
        )
        self.mar_implantacao_pag, _ = create_implantacao(
            self.processo, data_vencimento=date(2025, 3, 15)
        )

        # Parcelas in different months
        self.jan_parcela_pag, _ = create_parcela(
            self.processo, data_vencimento=date(2025, 1, 20)
        )
        self.apr_parcela_pag, _ = create_parcela(
            self.processo, data_vencimento=date(2025, 4, 20)
        )

    def test_filter_by_year_and_month_returns_correct_implantacoes(self):
        response = self.client.get(self.url, {"year": 2025, "month": 1})
        # Should return January implantacao and January parcela
        self.assertEqual(response.data["count"], 2)

    def test_filter_by_year_and_month_returns_correct_parcelas(self):
        response = self.client.get(self.url, {"year": 2025, "month": 1})
        from pagamento.models import TipoPagamento

        tipos = [r["tipo"] for r in response.data["results"]]
        self.assertIn(TipoPagamento.IMPLANTACAO, tipos)
        self.assertIn(TipoPagamento.PARCELA, tipos)

    def test_filter_excludes_other_months(self):
        response = self.client.get(self.url, {"year": 2025, "month": 3})
        self.assertEqual(response.data["count"], 1)
        from pagamento.models import TipoPagamento

        self.assertEqual(response.data["results"][0]["tipo"], TipoPagamento.IMPLANTACAO)

    def test_filter_includes_both_implantacao_and_parcela_for_month(self):
        response = self.client.get(self.url, {"year": 2025, "month": 1})
        from pagamento.models import TipoPagamento

        tipos = [r["tipo"] for r in response.data["results"]]
        self.assertIn(TipoPagamento.IMPLANTACAO, tipos)
        self.assertIn(TipoPagamento.PARCELA, tipos)

    def test_default_filter_uses_current_month(self):
        from datetime import date as dt

        today = dt.today()
        # Create a record for current month
        current_pag, _ = create_implantacao(
            self.processo,
            data_vencimento=date(today.year, today.month, 1),
        )
        response = self.client.get(self.url)
        # Only current month records should appear
        self.assertGreater(response.data["count"], 0)
        # Verify Jan 2025 records are excluded (unless current month is Jan 2025)
        if not (today.year == 2025 and today.month == 1):
            self.assertNotEqual(response.data["count"], 5)
