from rest_framework import serializers
from .models import (
    PagamentoImplantacao,
    PagamentoContrato,
    Processo,
    TipoPagamento,
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

    class Meta:
        model = PagamentoContrato
        fields = [
            "processo",
            "valor_total",
            "entrada",
            "valor_parcela",
            "numero_parcelas",
            "vencimento_entrada",
            "tipo",
        ]
        read_only_fields = ["tipo"]

    # TODO: Validar data do pagamento: deve ser uma data futura
    # TODO: validar parcela*meses + entrada == valor_total

    def get_tipo(self, obj):
        return TipoPagamento.CONTRATO

    def create(self, validated_data):
        validated_data["tipo"] = TipoPagamento.CONTRATO
        return super().create(validated_data)


class PagamentoImplantacaoSerializer(serializers.ModelSerializer):
    tipo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PagamentoImplantacao
        fields = [
            "tipo",
            "processo",
            "valor_total",
            "porcentagem_escritorio",
            "data_vencimento",
        ]
        read_only_fields = ["tipo"]

    # TODO: Validar data do pagamento: deve ser uma data futura
    # TODO: Validar porcentagem do escritório: deve estar entre 0 e 100
    # TODO: Validar valor total: deve ser maior que zero

    def get_tipo(self, obj):
        return TipoPagamento.IMPLANTACAO

    def create(self, validated_data):
        validated_data["tipo"] = TipoPagamento.IMPLANTACAO
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
