from rest_framework import serializers
from ..models import (
    Processo,
    Pagamento,
    PagamentoImplantacao,
    TipoPagamento,
    TipoParcela,
    PagamentoParcela,
    StatusPagamento,
    PagamentoContrato,
)


class PagamentoImplantacaoSerializer(serializers.ModelSerializer):
    detalhe = serializers.SerializerMethodField()
    contratos_mapping = {}

    class Meta:
        model = Pagamento
        fields = [
            "criado_em",
            "tipo",
            "detalhe",
        ]

    def isContrato(self, tipo):
        return tipo == TipoPagamento.ENTRADA or tipo == TipoPagamento.PARCELA

    def get_detalhe(self, obj):

        if obj.tipo == TipoPagamento.IMPLANTACAO:
            return PagamentoImplantacaoReaderSerializer(obj.detalhes).data

        if self.isContrato(obj.tipo):
            if obj.parcelas_contrato.contrato.id not in self.contratos_mapping:
                self.contratos_mapping[obj.parcelas_contrato.contrato.id] = True

                return PagamentoContratoReaderSerializer(
                    obj.parcelas_contrato.contrato
                ).data
            else:
                print("skipping contrato id", obj.parcelas_contrato.contrato.id)

        return None


class PagamentoImplantacaoReaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagamentoImplantacao
        fields = [
            "pagamento",
            "valor_total",
            "porcentagem_escritorio",
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


class PagamentoContratoReaderSerializer(serializers.ModelSerializer):
    parcelas = serializers.SerializerMethodField()
    entrada = serializers.SerializerMethodField()

    class Meta:
        model = PagamentoContrato
        fields = [
            "valor_parcela",
            "numero_parcelas",
            "entrada",
            "parcelas",
        ]

    def get_parcelas(self, obj):
        parcelas = obj.parcelas.all()
        return ParcelasSerializer(parcelas, many=True).data

    def get_entrada(self, obj):

        entrada = obj.parcelas.filter(tipo=TipoParcela.ENTRADA).first()
        return EntradaSerializer(
            {
                "valor": entrada.valor_parcela,
                "vencimento": entrada.data_vencimento,
                "status": entrada.status,
            }
        ).data

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     if not instance.entrada_filter:
    #         data.pop("entrada", None)
    #     return data


class EntradaSerializer(serializers.Serializer):
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)
    vencimento = serializers.DateField()
    status = serializers.ChoiceField(choices=StatusPagamento.choices)


class PagamentoReaderSerializer(serializers.ModelSerializer):
    processo = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()

    class Meta:
        model = Pagamento
        fields = [
            "criado_em",
            "processo",
            "tipo",
        ]

    def get_tipo(self, obj):
        if obj.tipo == TipoPagamento.ENTRADA or obj.tipo == TipoPagamento.PARCELA:
            return TipoPagamento.CONTRATO

        return obj.tipo

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
        elif instance.tipo in [TipoPagamento.ENTRADA]:
            data["detalhe"] = PagamentoContratoReaderSerializer(
                instance.parcelas_contrato.contrato
            ).data
        else:
            data["detalhe"] = None  # Default to None if no matching type

        return data
