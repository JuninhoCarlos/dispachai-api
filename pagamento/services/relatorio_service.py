from decimal import Decimal

from ..models import TipoPagamento


def _add_pagamento_to_processo(
    processos_map, processo, pagamento, receita, comissao_porcentagem, comissao_valor
):
    processo_id = processo.id
    if processo_id not in processos_map:
        processos_map[processo_id] = {
            "processo_id": processo.id,
            "cliente": processo.cliente.nome if processo.cliente else None,
            "pagamentos": [],
        }
    processos_map[processo_id]["pagamentos"].append(
        {
            "pagamento_id": pagamento.id,
            "tipo": pagamento.tipo,
            "receita": receita,
            "comissao_porcentagem": comissao_porcentagem,
            "comissao_valor": comissao_valor,
        }
    )


def _resolve_porcentagem(ajustada, padrao):
    return ajustada if ajustada is not None else padrao


def _calcular_implantacao(total_recebido, porcentagem_escritorio, advogado_porcentagem):
    """
    Implantação distribution:
      escritorio_base = total_recebido × porcentagem_escritorio%
      advogado_bruto  = escritorio_base × advogado%
      corretor_valor  = advogado_bruto × corretor%   (cuts from advogado's gross)
      advogado_net    = advogado_bruto - corretor_valor
      escritorio      = escritorio_base - advogado_bruto
    Returns (escritorio_base, advogado_bruto, escritorio_liquido).
    """
    escritorio_base = total_recebido * (porcentagem_escritorio / Decimal("100"))
    advogado_bruto = escritorio_base * (advogado_porcentagem / Decimal("100"))
    escritorio_liquido = escritorio_base - advogado_bruto
    return escritorio_base, advogado_bruto, escritorio_liquido


def _calcular_contrato(total_recebido, advogado_porcentagem, corretor_porcentagem):
    """
    Contrato (parcela/entrada) distribution:
      corretor_valor = total_recebido × corretor%   (corretor cuts first)
      restante       = total_recebido - corretor_valor
      advogado_valor = restante × advogado%
      escritorio     = restante - advogado_valor
    Returns (corretor_valor, restante, advogado_valor, escritorio_liquido).
    """
    corretor_valor = total_recebido * (corretor_porcentagem / Decimal("100"))
    restante = total_recebido - corretor_valor
    advogado_valor = restante * (advogado_porcentagem / Decimal("100"))
    escritorio_liquido = restante - advogado_valor
    return corretor_valor, restante, advogado_valor, escritorio_liquido


def build_relatorio(eventos, data_inicio, data_fim):
    pagamento_totais = {}
    for evento in eventos:
        pagamento_id = evento.pagamento_id
        if pagamento_id not in pagamento_totais:
            pagamento_totais[pagamento_id] = {
                "pagamento": evento.pagamento,
                "total_recebido": Decimal("0.00"),
            }
        pagamento_totais[pagamento_id]["total_recebido"] += evento.valor_recebido

    advogado_map = {}
    corretor_map = {}
    total_receita = Decimal("0.00")
    total_escritorio = Decimal("0.00")

    for item in pagamento_totais.values():
        pagamento = item["pagamento"]
        total_recebido = item["total_recebido"]
        processo = pagamento.processo
        advogado = processo.advogado
        corretor = processo.corretor

        advogado_porcentagem = _resolve_porcentagem(
            processo.comissao_ajustada_advogado, advogado.comissao_padrao
        )

        if pagamento.tipo == TipoPagamento.IMPLANTACAO:
            porcentagem_escritorio = pagamento.implantacao.porcentagem_escritorio
            escritorio_base, advogado_bruto, escritorio_liquido = _calcular_implantacao(
                total_recebido, porcentagem_escritorio, advogado_porcentagem
            )

            corretor_valor = Decimal("0.00")
            corretor_porcentagem = None
            if corretor:
                corretor_porcentagem = _resolve_porcentagem(
                    processo.comissao_ajustada_corretor, corretor.comissao_padrao
                )
                corretor_valor = advogado_bruto * (
                    corretor_porcentagem / Decimal("100")
                )

            advogado_valor = advogado_bruto - corretor_valor
            receita_total = escritorio_base
            receita_advogado = escritorio_base
            receita_corretor = advogado_bruto

        else:  # CONTRATO_PARCELA or CONTRATO_ENTRADA
            corretor_porcentagem = None
            corretor_porcentagem_valor = Decimal("0.00")
            if corretor:
                corretor_porcentagem = _resolve_porcentagem(
                    processo.comissao_ajustada_corretor, corretor.comissao_padrao
                )
                corretor_porcentagem_valor = corretor_porcentagem

            corretor_valor, restante, advogado_valor, escritorio_liquido = (
                _calcular_contrato(
                    total_recebido, advogado_porcentagem, corretor_porcentagem_valor
                )
            )
            receita_total = total_recebido
            receita_advogado = restante
            receita_corretor = total_recebido

        total_receita += receita_total
        total_escritorio += escritorio_liquido

        if advogado.id not in advogado_map:
            advogado_map[advogado.id] = {
                "id": advogado.id,
                "nome": advogado.nome,
                "total_comissao": Decimal("0.00"),
                "processos": {},
            }
        advogado_map[advogado.id]["total_comissao"] += advogado_valor
        _add_pagamento_to_processo(
            advogado_map[advogado.id]["processos"],
            processo,
            pagamento,
            receita_advogado,
            advogado_porcentagem,
            advogado_valor,
        )

        if corretor:
            if corretor.id not in corretor_map:
                corretor_map[corretor.id] = {
                    "id": corretor.id,
                    "nome": corretor.nome,
                    "total_comissao": Decimal("0.00"),
                    "processos": {},
                }
            corretor_map[corretor.id]["total_comissao"] += corretor_valor
            _add_pagamento_to_processo(
                corretor_map[corretor.id]["processos"],
                processo,
                pagamento,
                receita_corretor,
                corretor_porcentagem,
                corretor_valor,
            )

    for advogado_entry in advogado_map.values():
        advogado_entry["processos"] = list(advogado_entry["processos"].values())
    for corretor_entry in corretor_map.values():
        corretor_entry["processos"] = list(corretor_entry["processos"].values())

    return {
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "total_receita": total_receita,
        "escritorio": {"total_comissao": total_escritorio},
        "advogados": list(advogado_map.values()),
        "corretores": list(corretor_map.values()),
    }
