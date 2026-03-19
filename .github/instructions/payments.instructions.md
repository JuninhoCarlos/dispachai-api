---
applyTo: "pagamento/**"
---

# Payment Architecture

## Pattern: Manual Discriminated Union

Polymorphic payments use a manual discriminated union. Never use `django-polymorphic` or
multi-table inheritance with automatic downcasting.

- `Pagamento` is the base record with a `tipo` CharField (discriminator)
- Each payment subtype has its own model with `OneToOneField(Pagamento, primary_key=True)`
- The `detalhes` property on `Pagamento` returns the correct subtype based on `tipo`
- Joins to subtype tables only happen when explicitly requested via `select_related`

Current subtypes:
- `IMPLANTACAO` → `PagamentoImplantacao` (related_name: `implantacao`)
- `CONTRATO_PARCELA` / `CONTRATO_ENTRADA` → `PagamentoParcela` (related_name: `parcela`)

## Adding a New Payment Type — TDD Checklist

Follow TDD strictly: write each group of tests first, confirm they fail, then implement.

### Step 1 — Tests: Model

Verify:
- The new `TipoPagamento` choice value exists
- A `Pagamento` with the new `tipo` can be created and saved
- The OneToOne subtype model can be created and linked
- `pagamento.detalhes` returns the new subtype instance

### Step 2 — Model (`pagamento/models.py`)

- Add the new choice to `TipoPagamento`
- Create subtype model with `OneToOneField(Pagamento, primary_key=True)`, `status` field, all type-specific fields
- Update `Pagamento.detalhes` property
- Run `uv run python manage.py makemigrations && uv run python manage.py migrate`

### Step 3 — Tests: Write Serializer

Verify:
- POST with valid data returns 201
- Both `Pagamento` and subtype records are created in the DB
- Required fields return 400 with correct field name when missing

### Step 4 — Write Serializer (`pagamento/serializers/write.py`)

- Create `PagamentoXyzSerializer` with `@transaction.atomic` in `create()`
- First create `Pagamento(tipo=TipoPagamento.XYZ, ...)`, then create the subtype
- Add `CreateAPIView` and register URL in `pagamento/urls.py`

### Step 5 — Tests: Read Serializer

Verify:
- `GET /api/pagamento` lists the new type
- Response includes a `detalhe` field with subtype data
- Overdue status (`ATRASADO`) is computed correctly if the type has a `data_vencimento`

### Step 6 — Read Serializer (`pagamento/serializers/read.py`)

- Create `PagamentoXyzReaderSerializer` pointing to the new model
- If overdue-capable, override `to_representation()` to set `ATRASADO` when appropriate
- Add a new branch in `PagamentoReaderSerializer.to_representation()` for the new type
- Add `select_related("xyz")` to the list view queryset

### Step 7 — Tests: Service (only if the type supports `/api/pagamento/<id>/pagar`)

Skip steps 7 and 8 entirely if the new type is not payable. Do not create a service for write-once or read-only types.

Verify:
- POST to `/api/pagamento/<id>/pagar` with `valor_pago` and `data_pagamento` returns 200
- Status is updated to `PAGO` or `PARCIALMENTE_PAGO` correctly
- Invalid or overpayment states return 400

### Step 8 — Service (only if step 7 applies)

- Add `_pagar_xyz(pagamento, valor_pago, data_pagamento)` in `PagamentoService`
- Wire into `pagar()` dispatch with a new `elif tipo == TipoPagamento.XYZ:` branch
