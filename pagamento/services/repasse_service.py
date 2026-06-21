from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from ..models import PagamentoEvento, Repasse, TipoPagamento, TipoRepasse
from .relatorio_service import (
    _calcular_contrato,
    _calcular_implantacao,
    _resolve_porcentagem,
)


class RepasseService:
    @classmethod
    def repassar(cls, pagamento, tipo, data_repasse):
        processo = pagamento.processo

        eventos = PagamentoEvento.objects.filter(
            pagamento=pagamento,
            data_pagamento__year=data_repasse.year,
            data_pagamento__month=data_repasse.month,
        )

        if not eventos.exists():
            raise ValidationError(
                {"data_repasse": "Não há eventos de pagamento no mês de referência."}
            )

        if tipo == TipoRepasse.CORRETOR and processo.corretor is None:
            raise ValidationError({"tipo": "Este processo não possui corretor."})

        if Repasse.objects.filter(
            pagamento=pagamento,
            tipo=tipo,
            data_repasse__year=data_repasse.year,
            data_repasse__month=data_repasse.month,
        ).exists():
            raise ValidationError(
                {
                    "non_field_errors": (
                        "Já existe um repasse registrado para este período."
                    )
                }
            )

        valor_total = eventos.aggregate(total=Sum("valor_recebido"))[
            "total"
        ] or Decimal("0.00")

        advogado = processo.advogado
        corretor = processo.corretor

        advogado_porcentagem = _resolve_porcentagem(
            processo.comissao_ajustada_advogado, advogado.comissao_padrao
        )
        corretor_porcentagem = Decimal("0.00")
        if corretor:
            corretor_porcentagem = _resolve_porcentagem(
                processo.comissao_ajustada_corretor, corretor.comissao_padrao
            )

        if pagamento.tipo == TipoPagamento.IMPLANTACAO:
            # valor_total is the aggregated event sum — already the office amount.
            _, corretor_valor, _, advogado_valor, _ = _calcular_implantacao(
                valor_total,
                advogado_porcentagem,
                corretor_porcentagem,
            )
        else:
            corretor_valor, _, advogado_valor, _ = _calcular_contrato(
                valor_total, advogado_porcentagem, corretor_porcentagem
            )

        if tipo == TipoRepasse.ADVOGADO:
            valor_repassado = advogado_valor
            comissao_porcentagem = advogado_porcentagem
        else:
            valor_repassado = corretor_valor
            comissao_porcentagem = corretor_porcentagem

        repasse = Repasse.objects.create(
            pagamento=pagamento,
            tipo=tipo,
            advogado=advogado if tipo == TipoRepasse.ADVOGADO else None,
            corretor=corretor if tipo == TipoRepasse.CORRETOR else None,
            valor_repassado=valor_repassado,
            valor_total=valor_total,
            comissao_porcentagem=comissao_porcentagem,
            data_repasse=data_repasse,
        )
        repasse.eventos.set(eventos)

        return repasse
