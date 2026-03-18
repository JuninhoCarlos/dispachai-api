# Helper function to validate CPF
import re

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from rest_framework import serializers

from pessoa.models import Cliente

from ..models import (
    Pagamento,
    PagamentoContrato,
    PagamentoImplantacao,
    PagamentoParcela,
    Processo,
    StatusPagamento,
    TipoPagamento,
    TipoParcela,
)


def validate_cpf(cpf):
    cpf = re.sub(r"[^0-9]", "", cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def calc_digit(digs):
        s = sum(int(d) * w for d, w in zip(digs, range(len(digs) + 1, 1, -1)))
        return str((s * 10 % 11) % 10)

    return calc_digit(cpf[:9]) == cpf[9] and calc_digit(cpf[:10]) == cpf[10]


class PagamentoBaseSerializer(serializers.ModelSerializer):
    processo = serializers.PrimaryKeyRelatedField(
        queryset=Processo.objects.all(), write_only=True
    )

    tipo = None  # to be defined in subclasses

    class Meta:
        model = Pagamento
        fields = ["processo", "valor_total"]

    def create_pagamento(self, validated_data, tipo=None):
        processo = validated_data.pop("processo")

        return Pagamento.objects.create(
            processo=processo,
            tipo=tipo or self.tipo,
        )


class PagamentoContratoSerializer(PagamentoBaseSerializer):
    vencimento_parcela = serializers.DateField(
        write_only=True,
        required=True,
        help_text="Data de vencimento da primeira parcela.",
    )

    valor_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, write_only=True
    )

    class Meta:
        model = PagamentoContrato
        fields = [
            "processo",
            "valor_total",
            "entrada",
            "valor_parcela",
            "numero_parcelas",
            "vencimento_entrada",
            "vencimento_parcela",
        ]

    def validate(self, data):
        """
        Validações de alto nível envolvendo múltiplos campos.
        """

        # 2. Validar: entrada + valor_parcela * numero_parcelas == valor_total
        valor_total = data.get("valor_total")
        entrada = data.get("entrada")
        valor_parcela = data.get("valor_parcela")
        numero_parcelas = data.get("numero_parcelas")

        if all([valor_total, entrada, valor_parcela, numero_parcelas]):
            calculado = entrada + (valor_parcela * numero_parcelas)
            if calculado != valor_total:
                raise serializers.ValidationError(
                    {
                        "valor_total": (
                            "O valor_total deve ser igual a entrada + "
                            "valor_parcela * numero_parcelas."
                        )
                    }
                )

        return data

    def create(self, validated_data):
        vencimento_parcela = validated_data.get("vencimento_parcela")
        processo = validated_data.pop("processo")
        validated_data.pop("valor_total")

        contrato = super().create(validated_data)

        self._create_entrada(contrato, processo)
        self._create_parcelas(contrato, processo, vencimento_parcela)

        return contrato

    def _create_entrada(self, contrato, processo):
        pagamento_entrada = Pagamento.objects.create(
            processo=processo, tipo=TipoPagamento.ENTRADA
        )

        PagamentoParcela.objects.create(
            pagamento=pagamento_entrada,
            contrato=contrato,
            valor_parcela=contrato.entrada,
            tipo=TipoParcela.ENTRADA,
            numero_parcela=None,
            data_vencimento=contrato.vencimento_entrada,
            status=StatusPagamento.PLANEJADO,
        )

    def _create_parcelas(self, contrato, processo, vencimento_parcela):
        parcelas = []

        for i in range(contrato.numero_parcelas):
            pagamento = Pagamento.objects.create(
                processo=processo, tipo=TipoPagamento.PARCELA
            )
            parcelas.append(
                PagamentoParcela(
                    pagamento=pagamento,
                    contrato=contrato,
                    valor_parcela=contrato.valor_parcela,
                    numero_parcela=i + 1,
                    data_vencimento=vencimento_parcela + relativedelta(months=i),
                    tipo=TipoParcela.PARCELA,
                    status=StatusPagamento.PLANEJADO,
                )
            )

        PagamentoParcela.objects.bulk_create(parcelas, batch_size=200)


class PagamentoImplantacaoSerializer(PagamentoBaseSerializer):
    tipo = TipoPagamento.IMPLANTACAO
    porcentagem_escritorio = serializers.DecimalField(max_digits=5, decimal_places=2)
    data_vencimento = serializers.DateField()
    local_pagamento = serializers.CharField(max_length=255, required=False)

    class Meta:
        model = PagamentoImplantacao
        fields = [
            "processo",
            "valor_total",
            "porcentagem_escritorio",
            "data_vencimento",
            "local_pagamento",
        ]

    def validate(self, data):
        # validar valor_total > 0
        valor_total = data.get("valor_total")
        if valor_total is not None and valor_total <= 0:
            raise serializers.ValidationError(
                {"valor_total": "O valor total deve ser maior que zero."}
            )

        # validar porcentagem_escritorio entre 0 e 100
        porcentagem = data.get("porcentagem_escritorio")
        if porcentagem is not None and not (0 <= porcentagem <= 100):
            raise serializers.ValidationError(
                {"porcentagem_escritorio": "A porcentagem deve estar entre 0 e 100."}
            )

        return data

    def create(self, validated_data):

        pagamento = self.create_pagamento(validated_data)
        validated_data["pagamento"] = pagamento
        return super().create(validated_data)


class ProcessoSerializer(serializers.ModelSerializer):
    cliente = serializers.CharField(write_only=True, required=False)
    cpf = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Processo
        fields = [
            "id",
            "cliente",
            "cpf",
            "advogado",
            "corretor",
            "criado_em",
            "observacao",
        ]

    def validate(self, data):
        cpf = data.get("cpf")
        if cpf and not validate_cpf(cpf):
            raise ValidationError({"cpf": "CPF inválido."})
        return data

    def create(self, validated_data):
        cliente_nome = validated_data.pop("cliente", None)
        cpf = validated_data.pop("cpf", None)

        if cpf:
            cliente = Cliente.objects.filter(cpf=cpf).first()
            if not cliente:
                cliente = Cliente.objects.create(nome=cliente_nome, cpf=cpf)
        elif cliente_nome:
            cliente = Cliente.objects.create(nome=cliente_nome)
        else:
            raise ValidationError("É necessário fornecer o nome do cliente ou o CPF.")

        validated_data["cliente"] = cliente
        return super().create(validated_data)


class PagarSerializer(serializers.Serializer):
    valor_pago = serializers.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = serializers.DateField()

    def validate_valor_pago(self, value):
        if value <= 0:
            raise serializers.ValidationError("O valor pago deve ser maior que zero.")
        return value
