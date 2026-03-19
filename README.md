# DespachAI API

Django REST Framework API for legal services payment management. Handles lawyers, brokers, clients, legal processes, and polymorphic payment types with full transaction history.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Framework | Django 5.2.8 + Django REST Framework |
| Authentication | Knox (token-based, configurable TTL) |
| Database | PostgreSQL |
| Schema | drf-spectacular (OpenAPI 3.0.3) |
| Filtering | django-filter |
| Profiling | django-silk |
| Package manager | uv |
| Containerization | Docker + Docker Compose |

---

## Getting Started

### With Docker (recommended)

```bash
git clone <repo>
cd dispachai-api
docker compose up
```

This starts PostgreSQL and the Django dev server on `http://localhost:8000`.

### Local Development

**Prerequisites:** Python 3.13, uv, PostgreSQL running

```bash
uv sync
cp .env.example .env   # configure DATABASE_URL and SECRET_KEY
uv run python manage.py migrate
uv run python manage.py runserver
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | — |
| `DATABASE_URL` | PostgreSQL DSN (e.g. `postgres://user:pass@host/db`) | — |
| `TOKEN_TTL_HOURS` | Knox token lifetime in hours | `2` |

---

## Project Structure

```
dispachai-api/
├── api/                  # Django project (settings, root urls, wsgi/asgi)
├── identity/             # Authentication: login, register, Knox token management
├── pessoa/               # People: Advogado, Corretor, Cliente
├── pagamento/            # Payments: Processo, Pagamento subtypes, service layer
│   ├── serializers/
│   │   ├── write.py      # Mutation serializers (POST/PUT)
│   │   └── read.py       # Query serializers (GET, polymorphic output)
│   ├── services/
│   │   └── pagamento_service.py  # Multi-model payment business logic
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── filter.py         # Month/year filter for payment listing
├── schema.yml            # OpenAPI 3.0.3 (committed, kept in sync)
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

---

## Architecture

All endpoints follow a strict layered model:

```
Request → View → Serializer → Model → Response
```

- **View:** HTTP only — permission classes, `is_valid()`, `save()`, `Response`
- **Serializer:** Validation and DB writes — `validate_*()`, `create()` with `@transaction.atomic`
- **Model:** Field definitions, constraints, simple properties
- **Service layer:** Only for multi-model stateful transitions reused across call sites (e.g. `PagamentoService.pagar()`)

### Payment Architecture: Discriminated Union

Polymorphic payments use a manual discriminated union (not `django-polymorphic`):

- `Pagamento` — base record with a `tipo` discriminator field
- `PagamentoImplantacao` — `OneToOneField(Pagamento, primary_key=True, related_name="implantacao")`
- `PagamentoParcela` — `OneToOneField(Pagamento, primary_key=True, related_name="parcela")`
- `Pagamento.detalhes` property returns the correct subtype instance

---

## Data Model

```
Processo
  ├── advogado    → Advogado (required)
  ├── corretor    → Corretor (optional)
  ├── cliente     → Cliente (optional)
  └── observacao

Pagamento (base)
  ├── processo    → Processo
  ├── tipo        → TipoPagamento (IMPLANTACAO | CONTRATO_PARCELA | CONTRATO_ENTRADA)
  └── detalhes    → PagamentoImplantacao | PagamentoParcela (via property)

PagamentoImplantacao
  ├── valor_total, porcentagem_escritorio
  ├── data_vencimento, local_pagamento
  └── status      → StatusPagamento

PagamentoParcela
  ├── contrato    → PagamentoContrato
  ├── tipo        → TipoParcela (ENTRADA | PARCELA)
  ├── valor_parcela, numero_parcela, data_vencimento
  └── status      → StatusPagamento

PagamentoEvento  (transaction history)
  ├── pagamento   → Pagamento
  ├── valor_recebido
  └── data_pagamento

StatusPagamento: PLANEJADO | PAGO | PARCIALMENTE_PAGO | ATRASADO
```

---

## API Endpoints

All write endpoints require **IsSuperUser** unless noted.

### Authentication

| Method | Path | Permission | Description |
|---|---|---|---|
| `POST` | `/api/auth/login/` | AllowAny | Login, returns Knox token |
| `POST` | `/api/auth/logout/` | Authenticated | Invalidate current token |
| `POST` | `/api/auth/logoutall/` | Authenticated | Invalidate all tokens |
| `POST` | `/api/auth/register/` | IsSuperUser | Create a new user |

### Pessoas

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/api/pessoas/advogado` | IsAuthenticated | List advogados |
| `POST` | `/api/pessoas/advogado` | IsSuperUser | Create advogado |
| `GET` | `/api/pessoas/corretor` | IsAuthenticated | List corretores |
| `POST` | `/api/pessoas/corretor` | IsSuperUser | Create corretor |
| `GET` | `/api/pessoas/cliente` | IsAuthenticated | List clientes |

### Pagamentos

| Method | Path | Permission | Description |
|---|---|---|---|
| `GET` | `/api/pagamento` | IsAuthenticated | List payments (filter: `?year=&month=`) |
| `POST` | `/api/pagamento/implantacao` | IsSuperUser | Create implantação payment |
| `POST` | `/api/pagamento/contrato` | IsSuperUser | Create contract payment (entrada + parcelas) |
| `POST` | `/api/pagamento/<id>/pagar` | IsSuperUser | Register payment event |
| `GET` | `/api/pagamento/processo` | IsSuperUser | List processos |
| `POST` | `/api/pagamento/processo` | IsSuperUser | Create processo |
| `GET` | `/api/pagamento/processo/<id>` | IsSuperUser | Processo detail |
| `GET` | `/api/pagamento/processo/<id>/pendentes` | IsSuperUser | List pending payments for processo |

### Authentication Header

```
Authorization: Token <knox_token>
```

---

## Development Commands

```bash
# Run tests
uv run python manage.py test

# Format code
uv run black .

# Lint
uv run ruff check .

# Regenerate OpenAPI schema (run after any API change)
uv run python manage.py spectacular --color --file schema.yml

# Create and apply migrations
uv run python manage.py makemigrations
uv run python manage.py migrate
```

---

## Development Workflow (TDD)

1. **Plan** — clarify requirements and architecture before any code
2. **Write failing tests first** — define expected behavior in tests
3. **Await test approval** — present tests to reviewer before implementing
4. **Implement minimum code** — just enough to make tests pass
5. **Run full test suite** — all tests must pass
6. **Refactor** — clean up, re-run tests
7. **Format and lint** — `black .` then `ruff check .`
8. **Regenerate schema** — if any endpoint or serializer field changed

---

## Pagination

All list endpoints use `LimitOffsetPagination` with a default page size of 25.

```
GET /api/pagamento?limit=25&offset=0
```

---

## OpenAPI Schema

The `schema.yml` file is committed to the repository and must stay in sync with the code. Regenerate it after any endpoint, serializer field, or URL change:

```bash
uv run python manage.py spectacular --color --file schema.yml
```
