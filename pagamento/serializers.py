from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from rest_framework import serializers
from .models import (
    PagamentoImplantacao,
    PagamentoContrato,
    Processo,
    TipoPagamento,
    PagamentoParcela,
    StatusPagamento,
    Pagamento,
)


class ProcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Processo
        fields = [
            "id",
            "cliente",
            "advogado",
            "corretor",
        ]


class PagamentoContratoSerializer(serializers.ModelSerializer):
    tipo = serializers.SerializerMethodField(read_only=True)
    vencimento_parcela = serializers.DateField(
        write_only=True,
        required=True,
        help_text="Data de vencimento da primeira parcela.",
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
            "tipo",
        ]
        read_only_fields = ["tipo"]

    def validate(self, data):
        """
        Validações de alto nível envolvendo múltiplos campos.
        """

        # 1. Validar data do pagamento: deve ser uma data futura
        vencimento = data.get("vencimento_entrada")
        if vencimento and vencimento <= date.today():
            raise serializers.ValidationError(
                {"vencimento_entrada": "A data deve ser futura."}
            )

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

    def get_tipo(self, obj):
        return TipoPagamento.CONTRATO

    def create(self, validated_data):
        vencimento_parcela = validated_data.pop("vencimento_parcela")
        validated_data["tipo"] = TipoPagamento.CONTRATO
        contrato = super().create(validated_data)

        # self._create_parcelas(contrato, vencimento_parcela)

        return contrato

    def _create_parcelas(self, contrato, vencimento_parcela):
        parcelas = []

        for i in range(contrato.numero_parcelas):
            parcelas.append(
                PagamentoParcela(
                    contrato=contrato,
                    valor_parcela=contrato.valor_parcela,
                    numero_parcela=i + 1,
                    data_vencimento=vencimento_parcela + relativedelta(months=i),
                    status=StatusPagamento.PLANEJADO,
                    valor_pago=None,
                    tipo=TipoPagamento.PARCELA,
                    processo=contrato.processo,
                )
            )

        PagamentoParcela.objects.bulk_create(parcelas, batch_size=200)


class PagamentoImplantacaoSerializer(serializers.ModelSerializer):
    tipo = serializers.SerializerMethodField()
    processo = serializers.PrimaryKeyRelatedField(
        queryset=Processo.objects.all(), write_only=True
    )
    valor_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, write_only=True
    )
    porcentagem_escritorio = serializers.DecimalField(max_digits=5, decimal_places=2)
    data_vencimento = serializers.DateField()

    class Meta:
        model = PagamentoImplantacao
        fields = [
            "id",
            "tipo",
            "processo",
            "valor_total",
            "porcentagem_escritorio",
            "data_vencimento",
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
        if porcentagem is not None and not (0 < porcentagem <= 100):
            raise serializers.ValidationError(
                {"porcentagem_escritorio": "A porcentagem deve estar entre 0 e 100."}
            )

        # validar data_vencimento no futuro
        vencimento = data.get("data_vencimento")
        if vencimento is not None and vencimento < date.today():
            raise serializers.ValidationError(
                {"data_vencimento": "A data de vencimento deve ser futura."}
            )

        return data

    def get_tipo(self, obj):
        return TipoPagamento.IMPLANTACAO

    def create(self, validated_data):
        processo = validated_data.pop("processo")
        tipo = validated_data.pop("tipo", TipoPagamento.IMPLANTACAO)
        valor_total = validated_data.pop("valor_total")

        pagamento = Pagamento.objects.create(
            processo=processo,
            tipo=tipo,
            valor_total=valor_total,
        )
        validated_data["pagamento"] = pagamento

        return super().create(validated_data)


class PagamentoImplantacaoReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoImplantacao
        fields = [
            "id",
            "valor_total",
            "porcentagem_escritorio",
            "data_vencimento",
            "status",
            "criado_em",
        ]


class PagamentoContratoReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoContrato
        fields = [
            "id",
            "valor_total",
            "entrada",
            "valor_parcela",
            "numero_parcelas",
            "vencimento_entrada",
            "status_entrada",
            "criado_em",
        ]


class PagamentoSerializer(serializers.ModelSerializer):
    detalhe = serializers.SerializerMethodField()

    class Meta:
        model = Pagamento
        fields = [
            "valor_total",
            "criado_em",
            "tipo",
            "detalhe",
        ]

    def get_detalhe(self, obj):
        obj = obj.cast()
        if isinstance(obj, PagamentoImplantacao):
            return PagamentoImplantacaoReaderSerializer(obj).data

        if isinstance(obj, PagamentoContrato):
            return PagamentoContratoReaderSerializer(obj).data

        # fallback
        return None


class ProcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Processo
        fields = [
            "id",
            "cliente",
            "advogado",
            "corretor",
        ]


class ProcessoReaderSerializer(serializers.ModelSerializer):
    id_processo = serializers.IntegerField(source="id", read_only=True)
    pagamentos = serializers.SerializerMethodField()
    advogado = serializers.CharField(source="advogado.nome", read_only=True)
    corretor = serializers.CharField(source="corretor.nome", read_only=True)

    class Meta:
        model = Processo
        fields = [
            "id_processo",
            "cliente",
            "advogado",
            "corretor",
            "pagamentos",
        ]

    def get_pagamentos(self, obj):
        pagamentos = obj.pagamentos.all()
        return PagamentoSerializer(pagamentos, many=True).data
