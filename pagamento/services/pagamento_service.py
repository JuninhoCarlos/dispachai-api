from rest_framework.exceptions import ValidationError
from django.db import transaction

from pagamento.models import (
    PagamentoImplantacao,
    StatusPagamento,
    PagamentoEvento,
    TipoPagamento,
)


class PagamentoService:

    @staticmethod
    @transaction.atomic
    def pagar_implantacao(
        implantacao: PagamentoImplantacao, valor_pago: float, data_pagamento: str
    ):
        if implantacao.status == StatusPagamento.PAGO:
            raise ValidationError({"status": "Esta implantação já foi paga."})

        if valor_pago > implantacao.pagamento.valor_total:
            raise ValidationError(
                {
                    "valor_pago": "O valor pago não pode ser maior que o valor total do pagamento."
                }
            )

        status = (
            StatusPagamento.PAGO
            if valor_pago == implantacao.pagamento.valor_total
            else StatusPagamento.PARCIALMENTE_PAGO
        )

        # Create Pagamento event
        PagamentoEvento.objects.create(
            pagamento=implantacao.pagamento_id,
            valor_recebido=valor_pago,
            data_pagamento=data_pagamento,
            tipo=TipoPagamento.IMPLANTACAO,
        )

        implantacao.status = status
        implantacao.save()
