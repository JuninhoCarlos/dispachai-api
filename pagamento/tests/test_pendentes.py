from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pagamento.models import (
    Pagamento,
    PagamentoContrato,
    PagamentoEvento,
    PagamentoParcela,
    StatusPagamento,
    TipoPagamento,
    TipoParcela,
)
from pagamento.tests import (
    create_advogado,
    create_cliente,
    create_implantacao,
    create_parcela,
    create_processo,
    create_superuser,
    create_user,
)

PAST_DATE = date(2025, 1, 1)
FUTURE_DATE = date(2027, 1, 1)


class ProcessoPendentesAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = create_superuser()
        self.user = create_user()
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        self.url = reverse(
            "processo_pendentes", kwargs={"processo_id": self.processo.id}
        )

    def test_pendentes_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pendentes_requires_superuser(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pendentes_processo_not_found_returns_404(self):
        self.client.force_authenticate(user=self.superuser)
        url = reverse("processo_pendentes", kwargs={"processo_id": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pendentes_returns_atrasado_implantacao(self):
        pagamento, implantacao = create_implantacao(
            self.processo,
            data_vencimento=PAST_DATE,
            status=StatusPagamento.PLANEJADO,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["pagamento_id"], pagamento.id)
        self.assertEqual(item["tipo"], TipoPagamento.IMPLANTACAO)
        self.assertEqual(item["status"], StatusPagamento.ATRASADO)
        self.assertEqual(item["data_vencimento"], str(PAST_DATE))
        self.assertEqual(Decimal(item["valor_pendente"]), implantacao.valor_total)

    def test_pendentes_returns_parcialmente_pago_implantacao(self):
        pagamento, implantacao = create_implantacao(
            self.processo,
            data_vencimento=FUTURE_DATE,
            status=StatusPagamento.PARCIALMENTE_PAGO,
        )
        PagamentoEvento.objects.create(
            pagamento=pagamento,
            valor_recebido=Decimal("300.00"),
            data_pagamento=date(2026, 1, 1),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["status"], StatusPagamento.PARCIALMENTE_PAGO)
        self.assertEqual(Decimal(item["valor_pendente"]), Decimal("700.00"))

    def test_pendentes_returns_atrasado_contrato_parcela(self):
        pagamento, parcela = create_parcela(
            self.processo,
            data_vencimento=PAST_DATE,
            status=StatusPagamento.PLANEJADO,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["tipo"], TipoPagamento.PARCELA)
        self.assertEqual(item["status"], StatusPagamento.ATRASADO)
        self.assertEqual(item["parcela"], parcela.numero_parcela)
        self.assertIn("valor_pago", item)
        self.assertEqual(Decimal(item["valor_pago"]), Decimal("0"))
        self.assertEqual(Decimal(item["valor_pendente"]), parcela.valor_parcela)

    def test_pendentes_returns_parcialmente_pago_contrato_parcela(self):
        pagamento, parcela = create_parcela(
            self.processo,
            data_vencimento=FUTURE_DATE,
            status=StatusPagamento.PARCIALMENTE_PAGO,
        )
        PagamentoEvento.objects.create(
            pagamento=pagamento,
            valor_recebido=Decimal("200.00"),
            data_pagamento=date(2026, 1, 1),
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data[0]
        self.assertEqual(item["status"], StatusPagamento.PARCIALMENTE_PAGO)
        self.assertEqual(Decimal(item["valor_pago"]), Decimal("200.00"))
        self.assertEqual(
            Decimal(item["valor_pendente"]), parcela.valor_parcela - Decimal("200.00")
        )

    def test_pendentes_returns_atrasado_contrato_entrada(self):
        contrato = PagamentoContrato.objects.create(
            entrada=Decimal("200.00"),
            valor_parcela=Decimal("100.00"),
            numero_parcelas=1,
            vencimento_entrada=PAST_DATE,
        )
        pagamento = Pagamento.objects.create(
            processo=self.processo, tipo=TipoPagamento.ENTRADA
        )
        PagamentoParcela.objects.create(
            pagamento=pagamento,
            contrato=contrato,
            tipo=TipoParcela.ENTRADA,
            valor_parcela=Decimal("200.00"),
            numero_parcela=None,
            data_vencimento=PAST_DATE,
            status=StatusPagamento.PLANEJADO,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["tipo"], TipoPagamento.ENTRADA)
        self.assertIsNone(item["parcela"])

    def test_pendentes_excludes_pago_payments(self):
        create_implantacao(
            self.processo,
            data_vencimento=PAST_DATE,
            status=StatusPagamento.PAGO,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_pendentes_excludes_planejado_not_overdue(self):
        create_implantacao(
            self.processo,
            data_vencimento=FUTURE_DATE,
            status=StatusPagamento.PLANEJADO,
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
