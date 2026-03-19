from datetime import date
from decimal import Decimal

from rest_framework import serializers

from ..models import (
    Pagamento,
    PagamentoImplantacao,
    PagamentoParcela,
    Processo,
    StatusPagamento,
    TipoPagamento,
)
from ..services.pagamento_service import PagamentoEventoService


class ProcessoDetailSerializer(serializers.ModelSerializer):
    pagamentos = serializers.SerializerMethodField()

    class Meta:
        model = Processo
        fields = ["id", "cliente", "criado_em", "pagamentos"]

    def get_pagamentos(self, obj):
        implantacoes = obj.get_pagamentos_implantacoes()
        parcelas = obj.get_pagamentos_parcelas()

        serialized_implantacoes = PagamentoImplantacaoReaderSerializer(
            [pagamento.implantacao for pagamento in implantacoes], many=True
        ).data

        serialized_parcelas = PagamentoParcelaReaderSerializer(
            [pagamento.parcela for pagamento in parcelas], many=True
        ).data

        return {
            "implantacoes": serialized_implantacoes,
            "parcelas": serialized_parcelas,
        }


class StatusMixin:
    def get_status(self, obj):
        if obj.data_vencimento < date.today() and (
            obj.status != StatusPagamento.PAGO
            and obj.status != StatusPagamento.PARCIALMENTE_PAGO
        ):
            return StatusPagamento.ATRASADO

        return obj.status


class PagamentoImplantacaoReaderSerializer(StatusMixin, serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = PagamentoImplantacao
        fields = [
            "pagamento",
            "valor_total",
            "data_vencimento",
            "status",
            "local_pagamento",
        ]


class ParcelasSerializer(StatusMixin, serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = PagamentoParcela
        fields = [
            "numero_parcela",
            "valor_parcela",
            "data_vencimento",
            "status",
        ]


class PagamentoParcelaReaderSerializer(StatusMixin, serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = PagamentoParcela
        fields = [
            "tipo",
            "contrato",
            "pagamento",
            "valor_parcela",
            "numero_parcela",
            "data_vencimento",
            "status",
        ]


class PagamentoReaderSerializer(serializers.ModelSerializer):
    processo = serializers.SerializerMethodField()

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
            "id_cliente": obj.processo.cliente.id,
            "cliente": obj.processo.cliente.nome,
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
            data["detalhe"] = PagamentoParcelaReaderSerializer(instance.parcela).data
        else:
            data["detalhe"] = None  # Default to None if no matching type

        return data


class PendentesImplantacaoSerializer(StatusMixin, serializers.ModelSerializer):
    pagamento_id = serializers.IntegerField(source="pagamento.id")
    tipo = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    valor_pendente = serializers.SerializerMethodField()

    class Meta:
        model = PagamentoImplantacao
        fields = ["pagamento_id", "tipo", "status", "data_vencimento", "valor_pendente"]

    def get_tipo(self, obj):
        return TipoPagamento.IMPLANTACAO

    def get_valor_pendente(self, obj):
        if obj.status == StatusPagamento.PARCIALMENTE_PAGO:
            total_pago = PagamentoEventoService.calcular_total_pago(obj.pagamento)
            return obj.valor_total - Decimal(str(total_pago))
        return obj.valor_total


class PendentesParcelaSerializer(StatusMixin, serializers.ModelSerializer):
    pagamento_id = serializers.IntegerField(source="pagamento.id")
    tipo = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    valor_pendente = serializers.SerializerMethodField()
    valor_pago = serializers.SerializerMethodField()
    parcela = serializers.IntegerField(source="numero_parcela", allow_null=True)

    class Meta:
        model = PagamentoParcela
        fields = [
            "pagamento_id",
            "tipo",
            "status",
            "data_vencimento",
            "valor_pendente",
            "valor_pago",
            "parcela",
        ]

    def get_tipo(self, obj):
        return obj.pagamento.tipo

    def get_valor_pendente(self, obj):
        if obj.status == StatusPagamento.PARCIALMENTE_PAGO:
            total_pago = PagamentoEventoService.calcular_total_pago(obj.pagamento)
            return obj.valor_parcela - Decimal(str(total_pago))
        return obj.valor_parcela

    def get_valor_pago(self, obj):
        return PagamentoEventoService.calcular_total_pago(obj.pagamento)
