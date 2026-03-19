# DespachAI API — Copilot Instructions

Django REST Framework API for legal services payment management.
Stack: Python 3.13 · Django 5.2 · DRF · Knox Auth · PostgreSQL · uv

## Commands

- Tests: `uv run python manage.py test`
- Format: `uv run black .`
- Lint: `uv run ruff check .`
- Schema: `uv run python manage.py spectacular --color --file schema.yml`

## TDD — Always Follow This Order

1. Write failing tests first. Never write implementation before tests exist.
2. Present tests to the user and wait for explicit approval.
3. Implement minimum code to make tests pass.
4. Run full test suite — all must pass.
5. Run `uv run black .` then `uv run ruff check .`. Fix all ruff errors.
6. Regenerate `schema.yml` if any endpoint, serializer field, or URL changed.

## Architecture

Strict layered model: **View → Serializer → Model**.

- **Views**: HTTP only. Declare `permission_classes`, call `serializer.is_valid(raise_exception=True)`, return `Response`. No business logic.
- **Serializers**: Validation and DB writes. Wrap multi-model writes in `@transaction.atomic`.
- **Models**: Field definitions and constraints only.
- **Service layer**: Only when logic spans multiple models, involves stateful transitions, AND is reused from 2+ call sites. Never speculatively.

## Authentication

Every write endpoint requires authentication.
- `IsSuperUser` — create/update/delete
- `IsAuthenticated` — read-only
- `AllowAny` — login only, must have inline comment

Never omit `permission_classes` from a view.

## Serializer Layout

Every app uses a `serializers/` package (never a flat `serializers.py`):
- `write.py` — mutation serializers
- `read.py` — response serializers (only when needed)
- `__init__.py` — re-exports from `write.py` only

## Style

PEP-8. Black (88 chars). Double quotes. Trailing commas. `snake_case`/`PascalCase`.

## Tests — Mandatory for Every Endpoint

Four cases required:
1. Unauthenticated → `401`
2. Authenticated, wrong permission → `403`
3. Happy path → `201`/`200`, verify both response and DB state
4. Validation error → `400`, assert correct field name in `response.data`

Use `self.client.force_authenticate(user=...)`. Never real Knox tokens.
Use `django.test.TestCase` and `rest_framework.test.APIClient`. Never pytest.

## Payment Types

Polymorphic payments use a manual discriminated union. `Pagamento` is the base with a `tipo` CharField. Each subtype has `OneToOneField(Pagamento, primary_key=True)`.
Never use `django-polymorphic` or automatic downcasting.
