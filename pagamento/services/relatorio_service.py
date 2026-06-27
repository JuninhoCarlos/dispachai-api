from decimal import Decimal

from django.db.models import Sum

from ..models import PagamentoEvento, Repasse, StatusPagamento, TipoPagamento


def _add_pagamento_to_processo(
    processos_map,
    processo,
    pagamento,
    receita,
    comissao_porcentagem,
    comissao_valor,
    repasse_status,
    data_vencimento,
    data_pagamento,
    parcela_fields,
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
            "repasse_status": repasse_status,
            "data_vencimento": data_vencimento,
            "data_pagamento": data_pagamento,
            **parcela_fields,
        }
    )


def _resolve_porcentagem(ajustada, padrao):
    return ajustada if ajustada is not None else padrao


def _calcular_implantacao(total_recebido, advogado_porcentagem, corretor_porcentagem):
    """
    Implantação distribution. ``total_recebido`` is already the office amount
    (escritorio_base) — the client only pays the office its slice.
      escritorio_base = total_recebido
      corretor_valor  = escritorio_base × corretor%   (cuts from escritorio_base first)
      restante        = escritorio_base - corretor_valor
      advogado_valor  = restante × advogado%
      escritorio      = restante - advogado_valor
    Returns (escritorio_base, corretor_valor, restante, advogado_valor,
    escritorio_liquido).
    """
    escritorio_base = total_recebido
    corretor_valor = escritorio_base * (corretor_porcentagem / Decimal("100"))
    restante = escritorio_base - corretor_valor
    advogado_valor = restante * (advogado_porcentagem / Decimal("100"))
    escritorio_liquido = restante - advogado_valor
    return escritorio_base, corretor_valor, restante, advogado_valor, escritorio_liquido


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
                "data_pagamento": evento.data_pagamento,
            }
        pagamento_totais[pagamento_id]["total_recebido"] += evento.valor_recebido
        if evento.data_pagamento > pagamento_totais[pagamento_id]["data_pagamento"]:
            pagamento_totais[pagamento_id]["data_pagamento"] = evento.data_pagamento

    pagamento_ids = list(pagamento_totais.keys())
    repassados = set(
        Repasse.objects.filter(pagamento_id__in=pagamento_ids).values_list(
            "pagamento_id", "tipo"
        )
    )

    advogado_map = {}
    corretor_map = {}
    total_receita = Decimal("0.00")
    total_escritorio = Decimal("0.00")

    for item in pagamento_totais.values():
        pagamento = item["pagamento"]
        total_recebido = item["total_recebido"]
        data_pagamento = item["data_pagamento"]
        processo = pagamento.processo
        advogado = processo.advogado
        corretor = processo.corretor

        advogado_porcentagem = _resolve_porcentagem(
            processo.comissao_ajustada_advogado, advogado.comissao_padrao
        )

        parcela_fields = {}
        if pagamento.tipo == TipoPagamento.IMPLANTACAO:
            corretor_porcentagem = None
            corretor_porcentagem_valor = Decimal("0.00")
            if corretor:
                corretor_porcentagem = _resolve_porcentagem(
                    processo.comissao_ajustada_corretor, corretor.comissao_padrao
                )
                corretor_porcentagem_valor = corretor_porcentagem

            (
                escritorio_base,
                corretor_valor,
                restante,
                advogado_valor,
                escritorio_liquido,
            ) = _calcular_implantacao(
                total_recebido,
                advogado_porcentagem,
                corretor_porcentagem_valor,
            )
            receita_total = escritorio_base
            receita_advogado = restante
            receita_corretor = escritorio_base
            data_vencimento = pagamento.implantacao.data_vencimento

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
            parcela = pagamento.parcela
            data_vencimento = parcela.data_vencimento
            parcela_fields = {
                "numero_parcela": parcela.numero_parcela,
                "total_parcelas": parcela.contrato.numero_parcelas,
            }

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
        repasse_status_adv = (
            "REPASSADO" if (pagamento.id, "ADVOGADO") in repassados else "PENDENTE"
        )
        _add_pagamento_to_processo(
            advogado_map[advogado.id]["processos"],
            processo,
            pagamento,
            receita_advogado,
            advogado_porcentagem,
            advogado_valor,
            repasse_status_adv,
            data_vencimento,
            data_pagamento,
            parcela_fields,
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
            repasse_status_corretor = (
                "REPASSADO" if (pagamento.id, "CORRETOR") in repassados else "PENDENTE"
            )
            _add_pagamento_to_processo(
                corretor_map[corretor.id]["processos"],
                processo,
                pagamento,
                receita_corretor,
                corretor_porcentagem,
                corretor_valor,
                repasse_status_corretor,
                data_vencimento,
                data_pagamento,
                parcela_fields,
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


def build_recolhimento(pagamentos, data_inicio, data_fim):
    pagamento_list = list(pagamentos)

    parcialmente_pago_ids = [
        pagamento.id
        for pagamento in pagamento_list
        if (
            pagamento.tipo == TipoPagamento.IMPLANTACAO
            and pagamento.implantacao.status == StatusPagamento.PARCIALMENTE_PAGO
        )
        or (
            pagamento.tipo in [TipoPagamento.PARCELA, TipoPagamento.ENTRADA]
            and pagamento.parcela.status == StatusPagamento.PARCIALMENTE_PAGO
        )
    ]

    recebidos_por_pagamento = {}
    if parcialmente_pago_ids:
        agregados = (
            PagamentoEvento.objects.filter(pagamento_id__in=parcialmente_pago_ids)
            .values("pagamento_id")
            .annotate(total=Sum("valor_recebido"))
        )
        for agregado in agregados:
            recebidos_por_pagamento[agregado["pagamento_id"]] = agregado["total"]

    advogado_map = {}

    for pagamento in pagamento_list:
        processo = pagamento.processo
        advogado = processo.advogado
        corretor = processo.corretor

        advogado_porcentagem = _resolve_porcentagem(
            processo.comissao_ajustada_advogado, advogado.comissao_padrao
        )

        corretor_porcentagem = None
        corretor_porcentagem_valor = Decimal("0.00")
        if corretor:
            corretor_porcentagem = _resolve_porcentagem(
                processo.comissao_ajustada_corretor, corretor.comissao_padrao
            )
            corretor_porcentagem_valor = corretor_porcentagem

        parcela_fields = {}
        if pagamento.tipo == TipoPagamento.IMPLANTACAO:
            implantacao = pagamento.implantacao
            valor_base = implantacao.valor_escritorio
            valor_ja_recebido = recebidos_por_pagamento.get(
                pagamento.id, Decimal("0.00")
            )
            valor_pendente = valor_base - valor_ja_recebido
            status_pagamento = implantacao.status
            data_vencimento = implantacao.data_vencimento

            (
                _escritorio_base,
                corretor_valor,
                _restante,
                advogado_valor,
                escritorio_liquido,
            ) = _calcular_implantacao(
                valor_pendente,
                advogado_porcentagem,
                corretor_porcentagem_valor,
            )

        else:  # CONTRATO_PARCELA or CONTRATO_ENTRADA
            parcela = pagamento.parcela
            valor_base = parcela.valor_parcela
            valor_ja_recebido = recebidos_por_pagamento.get(
                pagamento.id, Decimal("0.00")
            )
            valor_pendente = valor_base - valor_ja_recebido
            status_pagamento = parcela.status
            data_vencimento = parcela.data_vencimento
            parcela_fields = {
                "numero_parcela": parcela.numero_parcela,
                "total_parcelas": parcela.contrato.numero_parcelas,
            }

            corretor_valor, _restante, advogado_valor, escritorio_liquido = (
                _calcular_contrato(
                    valor_pendente,
                    advogado_porcentagem,
                    corretor_porcentagem_valor,
                )
            )

        if advogado.id not in advogado_map:
            advogado_map[advogado.id] = {
                "id": advogado.id,
                "nome": advogado.nome,
                "total_recolhimento": Decimal("0.00"),
                "pagamentos": [],
            }

        advogado_map[advogado.id]["total_recolhimento"] += escritorio_liquido
        advogado_map[advogado.id]["pagamentos"].append(
            {
                "pagamento_id": pagamento.id,
                "cliente": processo.cliente.nome if processo.cliente else None,
                "tipo": pagamento.tipo,
                "status": status_pagamento,
                "valor_pendente": valor_pendente,
                "data_vencimento": data_vencimento,
                "comissao_advogado_porcentagem": advogado_porcentagem,
                "comissao_advogado_valor": advogado_valor,
                "valor_escritorio": escritorio_liquido,
                "corretor_nome": corretor.nome if corretor else None,
                "comissao_corretor_porcentagem": corretor_porcentagem,
                "comissao_corretor_valor": corretor_valor if corretor else None,
                **parcela_fields,
            }
        )

    return {
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "advogados": list(advogado_map.values()),
    }
