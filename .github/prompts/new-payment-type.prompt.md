---
description: "TDD checklist for adding a new payment type to the discriminated union"
---

# New Payment Type — TDD Checklist

Use this prompt when adding a new `TipoPagamento` subtype. Follow each step strictly — write tests first, confirm they fail, then implement. Do not skip steps or combine them.

## Before You Start

Ask the user:
1. What is the new `tipo` name? (e.g. `HONORARIO`)
2. What fields does the subtype need? (names, types, required/optional)
3. Does this type support the `pagar` action via `POST /api/pagamento/<id>/pagar`?
4. Does this type have a `data_vencimento` (overdue tracking)?

## Step 1 — Model Tests

Write tests in `pagamento/tests/test_models.py` verifying:
- The new `TipoPagamento.XYZ` choice value exists
- A `Pagamento` with `tipo=TipoPagamento.XYZ` can be created and saved
- The new subtype model can be created and linked via OneToOneField
- `pagamento.detalhes` returns the subtype instance, not the base `Pagamento`

Run `uv run python manage.py test pagamento.tests.test_models` — tests must fail. Present to user for approval.

## Step 2 — Model Implementation

After approval:
- Add `XYZ = "XYZ", "Display Name"` to `TipoPagamento` in `pagamento/models.py`
- Create `PagamentoXyz(models.Model)` with:
  - `pagamento = OneToOneField(Pagamento, on_delete=CASCADE, primary_key=True, related_name="xyz")`
  - `status = CharField(choices=StatusPagamento.choices, default=StatusPagamento.PLANEJADO)`
  - All type-specific fields
  - `class Meta: verbose_name = "..."`
- Update `Pagamento.detalhes` property: add `elif self.tipo == TipoPagamento.XYZ: return self.xyz`
- `uv run python manage.py makemigrations && uv run python manage.py migrate`

Run tests — must pass.

## Step 3 — Write Serializer Tests

Write tests in `pagamento/tests/test_serializers.py` or `test_views.py` verifying:
- POST to the new endpoint with valid data returns 201
- Both `Pagamento` and `PagamentoXyz` records are created in the DB
- Required fields return 400 with the correct field name when missing
- Unauthenticated → 401
- Non-superuser → 403

Present to user for approval.

## Step 4 — Write Serializer + View

After approval:
- Create `PagamentoXyzSerializer(serializers.Serializer)` in `pagamento/serializers/write.py`
- Override `create()` decorated with `@transaction.atomic`:
  ```python
  @transaction.atomic
  def create(self, validated_data):
      pagamento = Pagamento.objects.create(tipo=TipoPagamento.XYZ, processo=...)
      PagamentoXyz.objects.create(pagamento=pagamento, ...)
      return pagamento
  ```
- Create `CreateAPIView` with `permission_classes = [IsSuperUser]`
- Register URL in `pagamento/urls.py`

Run tests — must pass.

## Step 5 — Read Serializer Tests

Write tests verifying:
- `GET /api/pagamento` lists the new payment type
- Response includes `detalhe` field with subtype data
- If overdue-capable: when `data_vencimento` is in the past and status is not `PAGO`, status in response is `ATRASADO`

Present to user for approval.

## Step 6 — Read Serializer

After approval:
- Create `PagamentoXyzReaderSerializer(serializers.ModelSerializer)` in `pagamento/serializers/read.py`
- If overdue-capable, override `to_representation()` to set `status = StatusPagamento.ATRASADO` when appropriate
- Add branch in `PagamentoReaderSerializer.to_representation()`:
  ```python
  elif obj.tipo == TipoPagamento.XYZ:
      detalhe = PagamentoXyzReaderSerializer(obj.xyz).data
  ```
- Add `select_related("xyz")` to the list view queryset

Run tests — must pass.

## Step 7 — Pagar Tests (skip if not payable)

Write tests in `pagamento/tests/test_services.py` verifying:
- POST to `/api/pagamento/<id>/pagar` returns 200
- Status is updated to `PAGO` or `PARCIALMENTE_PAGO` correctly
- Overpayment returns 400

Present to user for approval.

## Step 8 — Service (skip if not payable)

After approval:
- Add `_pagar_xyz(pagamento, valor_pago, data_pagamento)` in `PagamentoService`
- Wire into `pagar()` dispatch: `elif tipo == TipoPagamento.XYZ: self._pagar_xyz(...)`

Run full suite — all must pass.

## Finish

```
uv run black .
uv run ruff check .
uv run python manage.py spectacular --color --file schema.yml
```
