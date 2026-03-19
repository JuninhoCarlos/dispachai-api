# DespachAI API

Django REST Framework API for legal services payment management.

**Stack:** Python 3.13 · Django · DRF · Knox Auth · PostgreSQL · uv

**Test command:** `uv run python manage.py test`
**Format command:** `uv run black .`
**Lint command:** `uv run ruff check .`

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

0. **Plan** — before writing any test, invoke the planning step (see `.claude/rules/planning.md`). Clarify requirements, resolve architectural decisions, and produce a design artifact in a Claude plan file. Only proceed to step 1 after the user has approved the design.
1. **Write failing tests first** — define the expected behavior in tests before writing any implementation code. Run tests and confirm they fail.
2. **Await test approval** — present the written tests to the user and wait for explicit approval before writing any implementation code.
3. **Implement minimum code** — write just enough to make the failing tests pass. No extra logic.
4. **Run the full test suite** — `uv run python manage.py test`. All tests must pass.
5. **Refactor** — clean up duplication or clarity issues. Re-run tests to confirm.
6. **Format and lint** — run `uv run black .` then `uv run ruff check .` before finishing. Fix any ruff errors before marking the task done. See `linting.md`.

Never write implementation code before the test exists and the user has approved the tests.

---

## Architecture

All endpoints follow a strict layered model: **view → serializer → model**.
A service layer is only permitted for complex business logic that spans multiple models (see `architecture.md`).
Authentication is required on every write endpoint by default — `AllowAny` requires an inline comment justifying the exception.
Unit tests are mandatory for every new endpoint.

See `.claude/rules/` for detailed patterns:
- `planning.md` — Mandatory planning step before any TDD cycle (requirements, architecture decisions, design output)
- `architecture.md` — Layer responsibilities, authentication policy, and when a service layer is permitted
- `payments.md` — How to add a new payment type (discriminated union pattern)
- `testing.md` — Django test conventions and the mandatory test checklist (includes approval gate)
- `linting.md` — Required format and lint steps before finishing any task
