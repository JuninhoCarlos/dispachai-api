# Commission Calculation Rules

This document is the single source of truth for how commissions are computed across all
payment types. Consult it before implementing or modifying any feature that touches
`comissao`, `receita`, `relatorio`, or payment distribution.

---

## Parties

| Party | Description |
|---|---|
| **Escritório** | The office. Keeps whatever is not paid out to advogado or corretor. |
| **Advogado** | The lawyer on the processo. Always present. Commission resolved from `processo.comissao_ajustada_advogado` if set, otherwise `advogado.comissao_padrao`. |
| **Corretor** | Optional referral agent on the processo. Commission resolved from `processo.comissao_ajustada_corretor` if set, otherwise `corretor.comissao_padrao`. |

---

## Implantação

> **Rule: Corretor cuts from `escritorio_base` first; advogado cuts from what remains.**

The recorded payment (`PagamentoEvento.valor_recebido`) **is already the office
amount** — the client only pays the office its slice, not the full benefit. So
`escritorio_base` equals the registered payment directly; there is no
`× porcentagem_escritorio` step in the distribution. The benefit and split are still
stored on the implantação as `valor_beneficio` and `porcentagem_escritorio`, and the
office amount is derived by the `PagamentoImplantacao.valor_escritorio` property
(`valor_beneficio × porcentagem_escritorio%`) — that is the amount registered as paid.

```
escritorio_base = valor_recebido            ← already the office amount
corretor_valor  = escritorio_base × corretor%    ← first, from escritorio_base
restante        = escritorio_base - corretor_valor
advogado_valor  = restante × advogado%
escritorio      = restante - advogado_valor
```

**Example:** valor_beneficio = 100, escritorio = 30% → valor_recebido (office) = 30;
advogado = 30%, corretor = 10%

| Party | Calculation | Amount |
|---|---|---|
| escritorio_base | valor_recebido | 30 |
| corretor | 30 × 10% | 3 |
| restante | 30 − 3 | 27 |
| advogado | 27 × 30% | 8.10 |
| escritório | 27 − 8.10 | 18.90 |
| **Total** | 3 + 8.10 + 18.90 | **30** ✓ |

**Audit fields per pagamento entry:**

| Field | Advogado entry | Corretor entry |
|---|---|---|
| `receita` | `restante` (after corretor) | `escritorio_base` |
| `comissao_porcentagem` | advogado% | corretor% |
| `comissao_valor` | `advogado_valor` | `corretor_valor` |

For both entries: `receita × comissao_porcentagem / 100 = comissao_valor` ✓

---

## Contrato (Parcela / Entrada)

> **Rule: Corretor cuts from the total first; advogado cuts from what remains.**

```
corretor_valor  = total_recebido × corretor%     ← first, from the full amount
restante        = total_recebido - corretor_valor
advogado_valor  = restante × advogado%
escritorio      = restante - advogado_valor
```

**Example:** total_recebido = 100, advogado = 50%, corretor = 10%

| Party | Calculation | Amount |
|---|---|---|
| corretor | 100 × 10% | 10 |
| restante | 100 − 10 | 90 |
| advogado | 90 × 50% | 45 |
| escritório | 90 − 45 | 45 |
| **Total** | 10 + 45 + 45 | **100** ✓ |

**Audit fields per pagamento entry:**

| Field | Advogado entry | Corretor entry |
|---|---|---|
| `receita` | `restante` (after corretor) | `total_recebido` |
| `comissao_porcentagem` | advogado% | corretor% |
| `comissao_valor` | `advogado_valor` | `corretor_valor` |

For both entries: `receita × comissao_porcentagem / 100 = comissao_valor` ✓

---

## No Corretor

When `processo.corretor` is `None`, set `corretor_valor = 0` and skip the corretor
entry entirely. The formulas above still hold — `restante = total_recebido` for
contrato, and `advogado_net = advogado_bruto` for implantação.

---

## Commission Resolution (Both Types)

```python
advogado_porcentagem = processo.comissao_ajustada_advogado ?? advogado.comissao_padrao
corretor_porcentagem = processo.comissao_ajustada_corretor ?? corretor.comissao_padrao
```

`comissao_ajustada_*` is `None` when not overridden on the processo. The fallback is
always the party's `comissao_padrao`. A `comissao_ajustada` of `0` is not valid
(model enforces `MinValueValidator(0.01)`), so Python's truthiness fallback is safe.

---

## `total_receita` in the Relatorio

`total_receita` = sum of the **distributable base** for all payments in the period:

- Implantação → `escritorio_base` (= the recorded payment, already the office's slice)
- Contrato → `total_recebido` (the full received amount)

`total_escritorio = total_receita − Σ advogado_net − Σ corretor_valor`

The invariant always holds: `total_receita = total_escritorio + Σ advogado + Σ corretor`

---

## Implementation

Logic lives in `pagamento/services/relatorio_service.py`:

- `_calcular_implantacao(total_recebido, advogado_porcentagem, corretor_porcentagem)`
  (`total_recebido` is already the office amount → `escritorio_base = total_recebido`)
  → returns `(escritorio_base, corretor_valor, restante, advogado_valor, escritorio_liquido)`
- `_calcular_contrato(total_recebido, advogado_porcentagem, corretor_porcentagem)`
  → returns `(corretor_valor, restante, advogado_valor, escritorio_liquido)`
- `build_relatorio(eventos, data_inicio, data_fim)` — orchestrates both
