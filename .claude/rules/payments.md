# Payment Architecture

## Pattern: Manual Discriminated Union

Polymorphic payments use a manual discriminated union. Never use `django-polymorphic` or
multi-table inheritance with automatic downcasting.

The pattern:
- `Pagamento` is the base record with a `tipo` CharField (discriminator)
- Each payment subtype has its own model with a `OneToOneField(Pagamento, primary_key=True)`
- The `detalhes` property on `Pagamento` returns the correct subtype based on `tipo`
- Joins to subtype tables only happen when explicitly requested via `select_related`

Current subtypes:
- `IMPLANTACAO` → `PagamentoImplantacao` (related_name: `implantacao`)
- `CONTRATO_PARCELA` / `CONTRATO_ENTRADA` → `PagamentoParcela` (related_name: `parcela`)

---

## Adding a New Payment Type — TDD Checklist

Follow TDD strictly: write each group of tests first, confirm they fail, then implement.

### Step 1 — Tests: Model (`pagamento/tests.py`)

Write tests verifying:
- The new `TipoPagamento` choice value exists
- A `Pagamento` with the new `tipo` can be created and saved
- The OneToOne subtype model can be created and linked to it
- `pagamento.detalhes` returns the new subtype instance (not the base `Pagamento`)

### Step 2 — Model (`pagamento/models.py`)

- Add the new choice to `TipoPagamento`
- Create the new subtype model (e.g. `PagamentoXyz`) with:
  - `pagamento = OneToOneField(Pagamento, on_delete=CASCADE, primary_key=True, related_name="xyz")`
  - `status = CharField(choices=StatusPagamento.choices, default=StatusPagamento.PLANEJADO)`
  - All type-specific fields with appropriate validators
  - `class Meta: verbose_name = "..."`
- Update `Pagamento.detalhes` property to handle the new `tipo`
- Create and run migration: `uv run python manage.py makemigrations && uv run python manage.py migrate`

### Step 3 — Tests: Write Serializer

Write tests verifying:
- POST to the creation endpoint with valid data returns 201
- The `Pagamento` and subtype records are both created in the database
- Required fields return 400 with the correct field name when missing

### Step 4 — Write Serializer (`pagamento/serializers.py`)

- Create `PagamentoXyzSerializer(serializers.Serializer)` with all required fields
- Override `create()` with `@transaction.atomic`: first create `Pagamento(tipo=TipoPagamento.XYZ, processo=...)`, then `PagamentoXyz(pagamento=pagamento, ...)`
- Create a `CreateAPIView` and register a URL in `pagamento/urls.py`

### Step 5 — Tests: Read Serializer

Write tests verifying:
- `GET /api/pagamento` lists the new payment type
- The response includes a `detalhe` field with the subtype's data
- If the subtype has a `data_vencimento`, overdue status (`ATRASADO`) is computed correctly when the date is in the past and status is not `PAGO`

### Step 6 — Read Serializer (`pagamento/read/serializers.py`)

- Create `PagamentoXyzReaderSerializer(serializers.ModelSerializer)` with a `Meta` pointing to the new model
- If the type can be overdue, override `to_representation()` to set `status` to `ATRASADO` when appropriate
- Add a new branch in `PagamentoReaderSerializer.to_representation()` to use the new reader serializer when `tipo == TipoPagamento.XYZ`
- Add `select_related("xyz")` to the queryset in the list view's filter/prefetch logic

### Step 7 — Tests: Service (ONLY if the payment type supports the "pagar" action)

A service is warranted here because `pagar` reads payment event history, validates overpayment across
that history, and updates status — a multi-model stateful transition that cannot live cleanly in a
single serializer `create()`. This is the exception, not the default pattern.

**Skip steps 7 and 8 entirely** if the new payment type is not payable via `/api/pagamento/<id>/pagar`.
Do not create a service file for types that are write-once or read-only.

Write tests verifying:
- POST to `/api/pagamento/<id>/pagar` with `valor_pago` and `data_pagamento` returns 200
- The payment status is updated to `PAGO` or `PARCIALMENTE_PAGO` correctly
- Invalid or overpayment states return 400

### Step 8 — Service (`pagamento/services/`) (ONLY if step 7 applies)

- Add `_pagar_xyz(pagamento, valor_pago, data_pagamento)` in `PagamentoService`
- Wire it into `pagar()` dispatch with a new `elif tipo == TipoPagamento.XYZ:` branch
