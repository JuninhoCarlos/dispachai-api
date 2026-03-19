# DespachAI API — Agent Instructions

Django REST Framework API for legal services payment management.

## Stack

Python 3.13 · Django 5.2 · DRF · Knox Auth · PostgreSQL · uv

## Commands

| Purpose | Command |
|---|---|
| Run tests | `uv run python manage.py test` |
| Format | `uv run black .` |
| Lint | `uv run ruff check .` |
| Migrate | `uv run python manage.py migrate` |
| Make migrations | `uv run python manage.py makemigrations` |
| Regenerate schema | `uv run python manage.py spectacular --color --file schema.yml` |

## Project Structure

```
api/            Django settings, wsgi, asgi, urls
pagamento/      Payment management (core business logic)
pessoa/         Person management (lawyers, clients, brokers)
identity/       Authentication and permissions
```

Each app follows this layout:
```
<app>/
├── models.py
├── views.py
├── serializers/
│   ├── __init__.py
│   ├── write.py        POST/PUT serializers
│   └── read.py         GET serializers (only when needed)
├── services/           Only when all 3 service-layer criteria are met
├── migrations/
├── tests/
│   ├── test_models.py
│   ├── test_views.py
│   └── test_serializers.py
└── urls.py
```

## TDD Workflow — Mandatory, Follow in Order

1. **Plan** — clarify requirements and architecture before writing any test. Do not skip.
2. **Write failing tests first** — define expected behavior in tests before any implementation.
3. **Await approval** — present tests to user and wait for explicit approval before implementing.
4. **Implement minimum code** — write just enough to make the failing tests pass. No extra logic.
5. **Run full test suite** — `uv run python manage.py test`. All tests must pass.
6. **Refactor** — clean up duplication or clarity issues. Re-run tests.
7. **Format and lint** — `uv run black .` then `uv run ruff check .`. Fix all ruff errors.
8. **Regenerate schema** — run schema command if any endpoint, serializer field, or URL changed.

## Architecture — Strict Layered Model

```
Request → View → Serializer → Model → Response
```

**View** (`views.py`): HTTP only. Declare `permission_classes`, call `serializer.is_valid(raise_exception=True)`, call `serializer.save()`, return `Response`. No business logic. Use DRF generic views.

**Serializer** (`serializers/write.py`, `serializers/read.py`): Validation and DB writes only. Override `validate_<field>()`, `validate()`, `create()`, `update()`. Wrap multi-model writes in `@transaction.atomic`.

**Model** (`models.py`): Field definitions, `Meta` constraints, simple `@property` helpers only.

**Service layer** (`services/`): Only permitted when ALL THREE are true:
1. Spans multiple models not naturally related through a single serializer `create()`
2. Involves stateful transitions
3. Must be reused from more than one call site

## Authentication Policy

Every write endpoint requires authentication. No exceptions without justification.

| Class | When |
|---|---|
| `IsSuperUser` | Create/update/delete on admin-owned resources |
| `IsAuthenticated` | Read-only endpoints |
| `AllowAny` | Login only — must have inline comment justifying it |

```python
permission_classes = [AllowAny]  # Public login — no auth context available at this point
```

## Style Guide

- PEP-8. Black formatting (88-char line length).
- Double quotes for strings.
- Trailing commas in multi-line collections.
- `snake_case` for variables and functions, `PascalCase` for classes.
- Imports ordered: stdlib → third-party → local.

## Payment Types — Discriminated Union

`Pagamento` is the base record with a `tipo` CharField discriminator. Each subtype has its own model with `OneToOneField(Pagamento, primary_key=True)`.

Current subtypes:
- `IMPLANTACAO` → `PagamentoImplantacao` (related_name: `implantacao`)
- `CONTRATO_PARCELA` / `CONTRATO_ENTRADA` → `PagamentoParcela` (related_name: `parcela`)

To add a new payment type, use the prompt at `.github/prompts/new-payment-type.prompt.md`.

## What the Agent Must Always Do

- Run `uv run black .` and `uv run ruff check .` before finishing any task
- Write tests before implementation code
- Verify both response AND database state in write-endpoint tests
- Use `self.client.force_authenticate(user=...)` in tests — never real Knox tokens
- Regenerate `schema.yml` after any API surface change

## What Requires User Approval

- Written tests — must be presented and explicitly approved before implementation begins
- Service layer introduction — confirm all 3 criteria are met
- `AllowAny` on any write endpoint

## What the Agent Must Never Do

- Never write implementation code before tests exist and the user has approved them
- Never omit `permission_classes` from a view
- Never import from `app.serializers` directly once a `read.py` exists in that app
- Never use `django-polymorphic` or multi-table inheritance with automatic downcasting
- Never commit `.claude/plans/` files to the repository
- Never skip linting — ruff errors must be fixed, not ignored

## Detailed Rules

- Testing conventions: `.github/instructions/testing.instructions.md`
- Architecture details: `.github/instructions/architecture.instructions.md`
- Payment type pattern: `.github/instructions/payments.instructions.md`
