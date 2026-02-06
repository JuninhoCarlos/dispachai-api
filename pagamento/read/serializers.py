from rest_framework import serializers
from ..models import (
    Pagamento,
    PagamentoImplantacao,
    TipoPagamento,
    PagamentoParcela,
)


class PagamentoImplantacaoReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoImplantacao
        fields = [
            "pagamento",
            "valor_total",
            "data_vencimento",
            "status",
        ]


class ParcelasSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoParcela
        fields = [
            "numero_parcela",
            "valor_parcela",
            "data_vencimento",
            "status",
        ]


class PagamentoParcelaReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoParcela
        fields = [
            "tipo",
            "contrato",
            "valor_parcela",
            "numero_parcela",
            "data_vencimento",
            "status",
        ]


class PagamentoReaderSerializer(serializers.ModelSerializer):
    # processo = serializers.SerializerMethodField()

    class Meta:
        model = Pagamento
        fields = [
            "tipo",
            "criado_em",
            "processo",
        ]

    def get_processo(self, obj):
        return {
            "id_processo": obj.processo.id,
            "cliente": obj.processo.cliente,
            "advogado": obj.processo.advogado.nome,
            "corretor": obj.processo.corretor.nome if obj.processo.corretor else None,
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Dynamically add the "detalhe" field based on the "tipo"
        if instance.tipo == TipoPagamento.IMPLANTACAO:
            data["detalhe"] = PagamentoImplantacaoReaderSerializer(
                instance.implantacao
            ).data
        # This fetch a contrato in Pagamentos table
        elif instance.tipo in [TipoPagamento.ENTRADA, TipoPagamento.PARCELA]:
            data["detalhe"] = PagamentoParcelaReaderSerializer(
                instance.parcelas_contrato
            ).data
        else:
            data["detalhe"] = None  # Default to None if no matching type

        return data
