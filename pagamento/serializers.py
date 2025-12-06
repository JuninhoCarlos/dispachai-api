from rest_framework import serializers
from .models import PagamentoImplantacao, Pagamento, Processo, TipoPagamento


class ProcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Processo
        fields = [
            "id",
            "cliente",
            "advogado",
            "corretor",
        ]


class PagamentoImplantacaoSerializer(serializers.ModelSerializer):
    tipo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PagamentoImplantacao
        fields = [
            "tipo",
            "processo",
            "valor_total",
            "porcentagem_escritorio",
            "data_pagamento",
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
