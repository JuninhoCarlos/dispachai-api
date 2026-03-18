# DespachAI API

Django REST Framework API for legal services payment management.

**Stack:** Python 3.13 · Django · DRF · Knox Auth · PostgreSQL · uv

**Test command:** `uv run python manage.py test`
**Format command:** `uv run black .`

---

## Style Guide

Follow PEP-8. Use `black` for formatting — always run it before finishing any task.

- Max line length: 88 (black default)
- Use double quotes for strings (black default)
- Use trailing commas in multi-line collections
- Imports ordered: stdlib → third-party → local (isort order)
- Variables and functions in `snake_case`, classes in `PascalCase`

---

## TDD Workflow

For every new feature or bug fix, follow this cycle strictly:

1. **Write failing tests first** — define the expected behavior in tests before writing any implementation code. Run tests and confirm they fail.
2. **Implement minimum code** — write just enough to make the failing tests pass. No extra logic.
3. **Run the full test suite** — `uv run python manage.py test`. All tests must pass.
4. **Refactor** — clean up duplication or clarity issues. Re-run tests to confirm.
5. **Format** — run `uv run black .` before finishing.

Never write implementation code before the test exists.

---

## Architecture

All endpoints follow a strict layered model: **view → serializer → model**.
A service layer is only permitted for complex business logic that spans multiple models (see `architecture.md`).
Authentication is required on every write endpoint by default — `AllowAny` requires an inline comment justifying the exception.
Unit tests are mandatory for every new endpoint.

See `.claude/rules/` for detailed patterns:
- `architecture.md` — Layer responsibilities, authentication policy, and when a service layer is permitted
- `payments.md` — How to add a new payment type (discriminated union pattern)
- `testing.md` — Django test conventions and the mandatory test checklist
