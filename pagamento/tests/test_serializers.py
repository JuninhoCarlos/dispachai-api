from datetime import date

from django.test import TestCase

from pagamento.models import (
    Pagamento,
    PagamentoContrato,
    PagamentoImplantacao,
    PagamentoParcela,
    TipoPagamento,
    TipoParcela,
)
from pagamento.serializers.write import (
    PagamentoContratoSerializer,
    PagamentoImplantacaoSerializer,
    PagarSerializer,
    ProcessoSerializer,
    validate_cpf,
)
from pagamento.tests import create_advogado, create_cliente, create_processo


class ValidateCpfTestCase(TestCase):
    def test_valid_cpf_returns_true(self):
        self.assertTrue(validate_cpf("529.982.247-25"))

    def test_invalid_cpf_all_same_digits_returns_false(self):
        self.assertFalse(validate_cpf("111.111.111-11"))

    def test_invalid_cpf_wrong_check_digits_returns_false(self):
        # Flip last digit of a valid CPF
        self.assertFalse(validate_cpf("529.982.247-26"))

    def test_invalid_cpf_too_short_returns_false(self):
        self.assertFalse(validate_cpf("123.456"))

    def test_cpf_without_formatting_is_accepted(self):
        self.assertTrue(validate_cpf("52998224725"))


class ProcessoSerializerTestCase(TestCase):
    def setUp(self):
        self.advogado = create_advogado()

    def test_create_with_cpf_creates_cliente_and_processo(self):
        from pessoa.models import Cliente

        data = {
            "advogado": self.advogado.id,
            "cliente": "João Silva",
            "cpf": "529.982.247-25",
        }
        serializer = ProcessoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        processo = serializer.save()
        self.assertIsNotNone(processo.cliente)
        self.assertEqual(processo.cliente.nome, "João Silva")
        self.assertEqual(Cliente.objects.count(), 1)

    def test_create_with_cpf_reuses_existing_cliente(self):
        from pessoa.models import Cliente

        Cliente.objects.create(nome="Existente", cpf="529.982.247-25")
        data = {
            "advogado": self.advogado.id,
            "cliente": "Outro Nome",
            "cpf": "529.982.247-25",
        }
        serializer = ProcessoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(Cliente.objects.count(), 1)

    def test_create_with_nome_only_creates_cliente_without_cpf(self):
        from pessoa.models import Cliente

        data = {"advogado": self.advogado.id, "cliente": "Sem CPF"}
        serializer = ProcessoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        processo = serializer.save()
        self.assertIsNone(processo.cliente.cpf)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_create_without_nome_or_cpf_raises_validation_error(self):
        from django.core.exceptions import ValidationError as DjangoValidationError

        data = {"advogado": self.advogado.id}
        serializer = ProcessoSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        with self.assertRaises(DjangoValidationError):
            serializer.save()

    def test_invalid_cpf_raises_validation_error(self):
        data = {
            "advogado": self.advogado.id,
            "cliente": "Teste",
            "cpf": "111.111.111-11",
        }
        serializer = ProcessoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("cpf", serializer.errors)


class PagamentoImplantacaoSerializerTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        self.valid_data = {
            "processo": self.processo.id,
            "valor_beneficio": "1000.00",
            "porcentagem_escritorio": "30.00",
            "data_vencimento": "2025-06-01",
        }

    def test_valid_data_creates_implantacao_and_pagamento(self):
        serializer = PagamentoImplantacaoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(Pagamento.objects.count(), 1)
        self.assertEqual(Pagamento.objects.first().tipo, TipoPagamento.IMPLANTACAO)
        self.assertEqual(PagamentoImplantacao.objects.count(), 1)

    def test_valor_beneficio_zero_raises_validation_error(self):
        data = {**self.valid_data, "valor_beneficio": "0.00"}
        serializer = PagamentoImplantacaoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_beneficio", serializer.errors)

    def test_valor_beneficio_negative_raises_validation_error(self):
        data = {**self.valid_data, "valor_beneficio": "-100.00"}
        serializer = PagamentoImplantacaoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_beneficio", serializer.errors)

    def test_valor_beneficio_missing_raises_validation_error(self):
        data = {k: v for k, v in self.valid_data.items() if k != "valor_beneficio"}
        serializer = PagamentoImplantacaoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_beneficio", serializer.errors)

    def test_porcentagem_above_100_raises_validation_error(self):
        data = {**self.valid_data, "porcentagem_escritorio": "101.00"}
        serializer = PagamentoImplantacaoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("porcentagem_escritorio", serializer.errors)

    def test_porcentagem_below_zero_raises_validation_error(self):
        data = {**self.valid_data, "porcentagem_escritorio": "-1.00"}
        serializer = PagamentoImplantacaoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("porcentagem_escritorio", serializer.errors)

    def test_local_pagamento_is_optional(self):
        serializer = PagamentoImplantacaoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class PagamentoContratoSerializerTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        # entrada=200 + valor_parcela=100 * numero_parcelas=8 = 1000
        self.valid_data = {
            "processo": self.processo.id,
            "valor_total": "1000.00",
            "entrada": "200.00",
            "valor_parcela": "100.00",
            "numero_parcelas": 8,
            "vencimento_entrada": "2025-01-01",
            "vencimento_parcela": "2025-02-01",
        }

    def test_valid_data_creates_contrato_entrada_and_parcelas(self):
        serializer = PagamentoContratoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(PagamentoContrato.objects.count(), 1)
        # 1 entrada + 8 parcelas = 9 Pagamento records
        self.assertEqual(Pagamento.objects.count(), 9)
        self.assertEqual(PagamentoParcela.objects.count(), 9)
        self.assertEqual(
            PagamentoParcela.objects.filter(tipo=TipoParcela.ENTRADA).count(), 1
        )
        self.assertEqual(
            PagamentoParcela.objects.filter(tipo=TipoParcela.PARCELA).count(), 8
        )

    def test_validate_sum_mismatch_raises_error(self):
        data = {**self.valid_data, "valor_total": "999.00"}
        serializer = PagamentoContratoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_total", serializer.errors)

    def test_parcelas_have_sequential_dates(self):
        serializer = PagamentoContratoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        parcelas = PagamentoParcela.objects.filter(tipo=TipoParcela.PARCELA).order_by(
            "numero_parcela"
        )
        self.assertEqual(parcelas[0].data_vencimento, date(2025, 2, 1))
        self.assertEqual(parcelas[1].data_vencimento, date(2025, 3, 1))
        self.assertEqual(parcelas[7].data_vencimento, date(2025, 9, 1))

    def test_parcelas_have_correct_numero_parcela(self):
        serializer = PagamentoContratoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        numeros = list(
            PagamentoParcela.objects.filter(tipo=TipoParcela.PARCELA)
            .order_by("numero_parcela")
            .values_list("numero_parcela", flat=True)
        )
        self.assertEqual(numeros, list(range(1, 9)))


class PagamentoContratoParcelaFinalSerializerTestCase(TestCase):
    def setUp(self):
        advogado = create_advogado()
        cliente = create_cliente()
        self.processo = create_processo(advogado=advogado, cliente=cliente)
        # 5000 + 12×400 + 200 = 10000 ✓
        self.valid_data = {
            "processo": self.processo.id,
            "valor_total": "10000.00",
            "entrada": "5000.00",
            "valor_parcela": "400.00",
            "numero_parcelas": 12,
            "vencimento_entrada": "2025-01-01",
            "vencimento_parcela": "2025-02-01",
            "parcela_final": "200.00",
        }

    def test_parcela_final_creates_13_parcelas(self):
        serializer = PagamentoContratoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(
            PagamentoParcela.objects.filter(tipo=TipoParcela.PARCELA).count(), 13
        )

    def test_parcela_final_last_parcela_has_custom_value(self):
        from decimal import Decimal

        serializer = PagamentoContratoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        ultima = (
            PagamentoParcela.objects.filter(tipo=TipoParcela.PARCELA)
            .order_by("numero_parcela")
            .last()
        )
        self.assertEqual(ultima.numero_parcela, 13)
        self.assertEqual(ultima.valor_parcela, Decimal("200.00"))

    def test_parcela_final_last_parcela_has_correct_date(self):
        serializer = PagamentoContratoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        ultima = (
            PagamentoParcela.objects.filter(tipo=TipoParcela.PARCELA)
            .order_by("numero_parcela")
            .last()
        )
        self.assertEqual(ultima.data_vencimento, date(2026, 2, 1))

    def test_parcela_final_updates_contrato_numero_parcelas(self):
        serializer = PagamentoContratoSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        contrato = PagamentoContrato.objects.get()
        self.assertEqual(contrato.numero_parcelas, 13)

    def test_parcela_final_valor_total_must_include_it(self):
        # valor_total only covers entrada + regular parcelas, missing parcela_final
        data = {
            **self.valid_data,
            "valor_total": "9800.00",  # 5000 + 12×400, excludes 200
        }
        serializer = PagamentoContratoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_total", serializer.errors)

    def test_parcela_final_zero_raises_validation_error(self):
        data = {**self.valid_data, "parcela_final": "0.00"}
        serializer = PagamentoContratoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("parcela_final", serializer.errors)

    def test_without_parcela_final_existing_behavior_unchanged(self):
        data = {
            "processo": self.processo.id,
            "valor_total": "1000.00",
            "entrada": "200.00",
            "valor_parcela": "100.00",
            "numero_parcelas": 8,
            "vencimento_entrada": "2025-01-01",
            "vencimento_parcela": "2025-02-01",
        }
        serializer = PagamentoContratoSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(
            PagamentoParcela.objects.filter(tipo=TipoParcela.PARCELA).count(), 8
        )


class PagarSerializerTestCase(TestCase):
    def test_valid_data_passes(self):
        serializer = PagarSerializer(
            data={"valor_pago": "100.00", "data_pagamento": "2025-01-01"}
        )
        self.assertTrue(serializer.is_valid())

    def test_valor_pago_zero_raises_validation_error(self):
        serializer = PagarSerializer(
            data={"valor_pago": "0.00", "data_pagamento": "2025-01-01"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_pago", serializer.errors)

    def test_valor_pago_negative_raises_validation_error(self):
        serializer = PagarSerializer(
            data={"valor_pago": "-50.00", "data_pagamento": "2025-01-01"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("valor_pago", serializer.errors)

    def test_missing_data_pagamento_raises_validation_error(self):
        serializer = PagarSerializer(data={"valor_pago": "100.00"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("data_pagamento", serializer.errors)
