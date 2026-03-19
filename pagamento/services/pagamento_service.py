from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from pagamento.models import (
    Pagamento,
    PagamentoEvento,
    PagamentoImplantacao,
    PagamentoParcela,
    StatusPagamento,
    TipoPagamento,
)


class PagamentoEventoService:

    @staticmethod
    def criar_evento_pagamento(
        pagamento: Pagamento, valor_recebido: float, data_pagamento: str
    ):
        return PagamentoEvento.objects.create(
            pagamento=pagamento,
            valor_recebido=valor_recebido,
            data_pagamento=data_pagamento,
        )

    @staticmethod
    def calcular_total_pago(pagamento: Pagamento):
        total_pago = (
            PagamentoEvento.objects.filter(pagamento=pagamento).aggregate(
                total_valor_recebido=Sum("valor_recebido")
            )["total_valor_recebido"]
            or 0
        )
        return total_pago


class PagamentoService:

    @staticmethod
    @transaction.atomic
    def _pagar_implantacao(
        implantacao: PagamentoImplantacao,
        valor_pago: float,
        data_pagamento: str,
        historico_pagamento: float,
        quitar: bool = False,
    ):
        status = (
            StatusPagamento.PAGO
            if quitar or valor_pago + historico_pagamento == implantacao.valor_total
            else StatusPagamento.PARCIALMENTE_PAGO
        )

        # Create Pagamento event
        PagamentoEventoService.criar_evento_pagamento(
            pagamento=implantacao.pagamento,
            valor_recebido=valor_pago,
            data_pagamento=data_pagamento,
        )

        implantacao.status = status
        implantacao.save()

    @staticmethod
    @transaction.atomic
    def _pagar_parcela(
        parcela: PagamentoParcela,
        valor_pago: float,
        data_pagamento: str,
        historico_pagamento: float,
        quitar: bool = False,
    ):
        status = (
            StatusPagamento.PAGO
            if quitar or valor_pago + historico_pagamento == parcela.valor_parcela
            else StatusPagamento.PARCIALMENTE_PAGO
        )

        # Create Pagamento event
        PagamentoEventoService.criar_evento_pagamento(
            pagamento=parcela.pagamento,
            valor_recebido=valor_pago,
            data_pagamento=data_pagamento,
        )

        parcela.status = status
        parcela.save()

    @staticmethod
    def _validar_pagamento(
        pagamento: PagamentoImplantacao | PagamentoParcela,
        valor_pago: float,
        historico_pagamento: float,
        quitar: bool = False,
    ):
        if pagamento.status == StatusPagamento.PAGO:
            raise ValidationError({"status": "Este pagamento já foi pago."})

        valor_divida = (
            pagamento.valor_total
            if isinstance(pagamento, PagamentoImplantacao)
            else pagamento.valor_parcela
        )

        # valida pagamentos parciais:
        # valida valor pago não pode ser maior que o valor da dívida
        if valor_pago + historico_pagamento > valor_divida:
            raise ValidationError(
                {
                    "erro": "O valor pago excede o valor total do pagamento.",
                    "detalhes": {
                        "valor_pago": valor_pago,
                        "valor_ja_pago": historico_pagamento,
                        "valor_divida": valor_divida,
                        "valor_total_recebido": valor_pago + historico_pagamento,
                        "pagamento_id": pagamento.pagamento_id,
                    },
                }
            )

    @classmethod
    def pagar(
        cls,
        pagamento: Pagamento,
        valor_pago: float,
        data_pagamento: str,
        quitar: bool = False,
    ):
        historico_pagamento = PagamentoEventoService.calcular_total_pago(pagamento)

        if pagamento.tipo == TipoPagamento.IMPLANTACAO:
            implantacao = pagamento.implantacao
            cls._validar_pagamento(implantacao, valor_pago, historico_pagamento, quitar)
            cls._pagar_implantacao(
                implantacao, valor_pago, data_pagamento, historico_pagamento, quitar
            )
        elif (
            pagamento.tipo == TipoPagamento.ENTRADA
            or pagamento.tipo == TipoPagamento.PARCELA
        ):
            parcela = pagamento.parcela
            cls._validar_pagamento(parcela, valor_pago, historico_pagamento, quitar)
            cls._pagar_parcela(
                parcela, valor_pago, data_pagamento, historico_pagamento, quitar
            )
        else:
            raise ValidationError(
                {"tipo": "Tipo de pagamento não suportado para pagamento."}
            )
