from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pagamento.models import (
    Pagamento,
    PagamentoContrato,
    PagamentoImplantacao,
    PagamentoParcela,
    Processo,
    StatusPagamento,
)
from pagamento.tests import (
    create_advogado,
    create_cliente,
    create_full_fixture,
    create_implantacao,
    create_processo,
    create_superuser,
    create_user,
)
from pessoa.models import Cliente


class ProcessoListCreateAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("processo_list_create")
        self.superuser = create_superuser()
        self.user = create_user()
        self.advogado = create_advogado()
        self.valid_data = {
            "advogado": self.advogado.id,
            "cliente": "Maria Silva",
            "cpf": "529.982.247-25",
        }

    def test_get_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_regular_user_returns_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_with_superuser_returns_200(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_unauthenticated_returns_401(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_returns_201_and_creates_records(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Processo.objects.count(), 1)

    def test_create_creates_cliente_on_the_fly(self):
        self.client.force_authenticate(user=self.superuser)
        self.client.post(self.url, self.valid_data)
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(Cliente.objects.first().nome, "Maria Silva")

    def test_create_reuses_existing_cliente_by_cpf(self):
        Cliente.objects.create(nome="Existente", cpf="529.982.247-25")
        self.client.force_authenticate(user=self.superuser)
        self.client.post(self.url, self.valid_data)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_create_with_invalid_cpf_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        data = {**self.valid_data, "cpf": "111.111.111-11"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProcessoDetailAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = create_superuser()
        self.user = create_user()
        fixture = create_full_fixture()
        self.processo = fixture["processo"]
        self.url = reverse("processo_detail", kwargs={"processo_id": self.processo.id})

    def test_get_detail_returns_200_for_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_detail_returns_403_for_regular_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_detail_returns_404_for_nonexistent(self):
        self.client.force_authenticate(user=self.superuser)
        url = reverse("processo_detail", kwargs={"processo_id": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_contains_pagamentos_structure(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertIn("pagamentos", response.data)
        self.assertIn("implantacoes", response.data["pagamentos"])
        self.assertIn("parcelas", response.data["pagamentos"])


class ImplantacaoCreateAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("implantacao_create")
        self.superuser = create_superuser()
        self.user = create_user()
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        self.valid_data = {
            "processo": self.processo.id,
            "valor_total": "1000.00",
            "porcentagem_escritorio": "30.00",
            "data_vencimento": "2025-06-01",
        }

    def test_create_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_returns_201_and_creates_records(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Pagamento.objects.count(), 1)
        self.assertEqual(PagamentoImplantacao.objects.count(), 1)

    def test_create_valor_total_zero_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        data = {**self.valid_data, "valor_total": "0.00"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_porcentagem_invalid_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        data = {**self.valid_data, "porcentagem_escritorio": "150.00"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ContratoCreateAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("contrato_create")
        self.superuser = create_superuser()
        self.user = create_user()
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        self.valid_data = {
            "processo": self.processo.id,
            "valor_total": "1000.00",
            "entrada": "200.00",
            "valor_parcela": "100.00",
            "numero_parcelas": 8,
            "vencimento_entrada": "2025-01-01",
            "vencimento_parcela": "2025-02-01",
        }

    def test_create_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_returns_201_and_creates_all_records(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PagamentoContrato.objects.count(), 1)
        self.assertEqual(Pagamento.objects.count(), 9)
        self.assertEqual(PagamentoParcela.objects.count(), 9)

    def test_create_sum_mismatch_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        data = {**self.valid_data, "valor_total": "999.00"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("valor_total", response.data)


class PagarPagamentosGenericViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = create_superuser()
        self.user = create_user()
        fixture = create_full_fixture()
        self.pagamento = fixture["pagamento"]
        self.implantacao = fixture["implantacao"]
        self.url = reverse(
            "pagamento_pagar", kwargs={"pagamento_id": self.pagamento.id}
        )
        self.valid_data = {"valor_pago": "1000.00", "data_pagamento": "2025-01-01"}

    def test_pagar_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_returns_401(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagar_full_payment_returns_200_and_status_pago(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "OK")
        self.implantacao.refresh_from_db()
        self.assertEqual(self.implantacao.status, StatusPagamento.PAGO)

    def test_pagar_partial_payment_sets_parcialmente_pago(self):
        self.client.force_authenticate(user=self.superuser)
        self.client.post(
            self.url, {"valor_pago": "500.00", "data_pagamento": "2025-01-01"}
        )
        self.implantacao.refresh_from_db()
        self.assertEqual(self.implantacao.status, StatusPagamento.PARCIALMENTE_PAGO)

    def test_pagar_already_pago_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        self.client.post(self.url, self.valid_data)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pagar_overpayment_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url, {"valor_pago": "1100.00", "data_pagamento": "2025-01-01"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pagar_nonexistent_pagamento_returns_404(self):
        self.client.force_authenticate(user=self.superuser)
        url = reverse("pagamento_pagar", kwargs={"pagamento_id": 99999})
        response = self.client.post(url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pagar_valor_pago_zero_returns_400(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url, {"valor_pago": "0.00", "data_pagamento": "2025-01-01"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PagamentoListAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("pagamento_list")
        self.superuser = create_superuser()
        self.user = create_user()
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        # January 2025
        self.jan_pagamento, _ = create_implantacao(
            self.processo, data_vencimento=date(2025, 1, 15)
        )
        # February 2025
        self.feb_pagamento, _ = create_implantacao(
            self.processo, data_vencimento=date(2025, 2, 15)
        )

    def test_list_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_can_list_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"year": 2025, "month": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_month_and_year_returns_correct_results(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"year": 2025, "month": 1})
        self.assertEqual(response.data["count"], 1)

    def test_filter_excludes_other_month(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"year": 2025, "month": 2})
        self.assertEqual(response.data["count"], 1)
        # Verify the January record is not in the February results
        result_ids = [r.get("criado_em") for r in response.data["results"]]
        self.assertEqual(len(result_ids), 1)

    def test_response_includes_detalhe_field(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"year": 2025, "month": 1})
        self.assertIn("detalhe", response.data["results"][0])

    def test_response_includes_processo_field(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"year": 2025, "month": 1})
        result = response.data["results"][0]
        self.assertIn("processo", result)
        self.assertIn("id_processo", result["processo"])
        self.assertIn("cliente", result["processo"])
        self.assertIn("advogado", result["processo"])
