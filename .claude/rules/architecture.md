# Architecture Guidelines

## Layered Architecture

This project uses a strict three-layer model. Each layer has exactly one job.

```
Request → View → Serializer → Model → Response
```

### View (`views.py`)

Handles HTTP concerns only:
- Declare `permission_classes`
- Parse and validate query parameters (simple filtering only — see below)
- Build the queryset via `get_queryset()` with `select_related` / `prefetch_related`
- Call `serializer.is_valid(raise_exception=True)`
- Call `serializer.save()` or a service method (see below)
- Return `Response`

**Views must never contain business logic.** This means no commission calculations,
no status derivations, no multi-step computations, and no domain rules of any kind.
If a `get()` method needs to do more than parse params → build queryset → call service
→ serialize → return, the extra logic belongs in a service.

**Simple filtering is allowed directly in the view.** Simple means: translating a query
param into a queryset `.filter()` call, a date range, or a single `select_related` hint.
Complex filtering (custom aggregation, multi-step query construction, annotation logic)
must be extracted to a service or a dedicated queryset helper.

Use DRF generic views (`CreateAPIView`, `ListAPIView`, `GenericAPIView`) whenever they fit.
Keep views under ~40 lines. If a view is growing, it is absorbing logic that belongs
in a serializer or a service.

**OpenAPI schema annotation (`@extend_schema`) is mandatory** when drf-spectacular cannot
infer the serializer from `serializer_class` alone. Two cases trigger this requirement:

1. **`serializer_class` is absent** — the view manually instantiates serializers inside
   the method body instead of relying on `get_serializer()`.
2. **Multiple serializers per class** — the view overrides `get_serializer_class()` to
   return different serializers depending on the HTTP method.

In both cases, annotate each affected method explicitly:

```python
from drf_spectacular.utils import extend_schema

class MyView(GenericAPIView):
    # No serializer_class — every method must be annotated

    @extend_schema(responses=MyReaderSerializer)
    def get(self, request): ...

    @extend_schema(request=MyWriteSerializer, responses=MyReaderSerializer)
    def post(self, request): ...
```

**Prefer a single unified serializer over polymorphic dispatch.** Before reaching for
`PolymorphicProxySerializer`, check whether a single serializer on the base model can
resolve subtype fields via `SerializerMethodField`. Only use `PolymorphicProxySerializer`
when response shapes are genuinely incompatible (e.g. different required fields with no
shared base model). When it is truly necessary, annotate with the discriminator field:

```python
from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer

@extend_schema(
    responses=PolymorphicProxySerializer(
        component_name="MyUnion",
        serializers=[FooSerializer, BarSerializer],
        resource_type_field_name="tipo",
    )
)
def get(self, request): ...
```

Never rely on drf-spectacular's fallback inference when `serializer_class` is absent or
dispatched dynamically — the generated schema will be wrong or empty.

### Serializer (`serializers/write.py`, `serializers/read.py`)

**Prefer a single serializer per endpoint response.** When a read endpoint could return
multiple subtypes (e.g. implantação and parcela payments in the same list), design the
serializer to accept the common base model (`Pagamento`) and resolve subtype fields
internally via `SerializerMethodField` or `to_representation()`. Only fall back to
`PolymorphicProxySerializer` when the response shapes are genuinely incompatible and a
unified model is not reachable without significant contortion. Annotate every
`SerializerMethodField` with `@extend_schema_field` so drf-spectacular can infer the
correct OpenAPI type.

Handles validation and data transformation only:
- Declare fields with appropriate validators
- Override `validate_<field>()` for field-level rules
- Override `validate()` for cross-field rules
- Override `create()` or `update()` for DB writes; wrap multi-model writes in `@transaction.atomic`

Write (mutation) serializers and read (query) serializers are kept separate. See **Serializer File Layout** below.
Serializers must not access `request` or contain presentation logic unrelated to the model.
Keep serializer `create()` methods under ~30 lines. Extract a private method within the same class if longer.

### Model (`models.py`)

Handles data and data integrity only:
- Field definitions with validators
- `class Meta` constraints
- Simple `@property` helpers (e.g., the `detalhes` discriminator)

Models must not import serializers or contain business-flow logic.

---

## Authentication Policy

**Default rule: every write endpoint requires authentication. No exceptions without justification.**

| Permission class | When to use |
|---|---|
| `IsSuperUser` | Create/update/delete on admin-owned resources (processes, payments, users) |
| `IsAuthenticated` | Read-only endpoints that any authenticated user may access |
| `AllowAny` | Login endpoint only — must be justified with an inline comment |

Never omit `permission_classes` from a view. DRF's global default is a safety net, not a permission strategy.

If a new view uses `AllowAny` on a write method, add an inline comment explaining why:

```python
permission_classes = [AllowAny]  # Public login — no auth context available at this point
```

---

## When a Service Layer Is Required

The default path is **view → serializer → model**. No service layer.

A service (in `<app>/services/`) is **required** whenever the logic meets **any** of the
following criteria:

### Criterion A — Stateful multi-model mutation
The operation spans multiple models, involves stateful transitions (e.g. computing status
across event history), and is called from more than one entry point.

**Example:** `PagamentoService.pagar()` reads payment event history, validates overpayment,
updates subtype status, and creates a new `PagamentoEvento` — a multi-model stateful
transaction called from multiple entry points.

### Criterion B — Business computation that must stay out of the view
The operation requires domain logic (formulas, rules, multi-step derivations) that is too
complex for a view but does not belong in a serializer because it is not about validation
or response shaping. Even a single-call-site, read-only operation qualifies if the logic
is non-trivial.

**Example:** `relatorio_service.build_relatorio()` computes commission distribution across
Implantação and Contrato payments — applying type-specific formulas (see `commission.md`),
grouping by advogado and corretor, and aggregating totals. This is pure domain computation
that must never live as helper functions inside `views.py`.

---

**Decision guide:**

| Scenario | Where does the logic go? |
|---|---|
| Simple field validation | Serializer `validate_<field>()` |
| Cross-field validation | Serializer `validate()` |
| Single-model DB write | Serializer `create()` / `update()` |
| Multi-model atomic write (single call site, no state machine) | Serializer `create()` with `@transaction.atomic` |
| Stateful multi-model mutation, reused across entry points | Service (Criterion A) |
| Non-trivial domain computation (formulas, aggregation, rules) | Service (Criterion B) |
| Simple queryset filtering from a query param | View `get_queryset()` |

Do not create a service file speculatively. Apply the decision guide; if the scenario
does not match Criterion A or B, default to the serializer.

---

## Filtering

Always reach for `django_filters` before writing manual query-param parsing in a view.
`django_filters.FilterSet` provides free input validation, type coercion, and graceful
degradation on bad input — manual parsing with `date.fromisoformat()` or `int()` will
raise unhandled exceptions on invalid user input.

**Pattern:**
1. Define a `FilterSet` in `<app>/filter.py` with typed filter fields
   (`DateFilter`, `NumberFilter`, `CharFilter`, etc.).
2. For non-trivial defaults (e.g. current-month fallback), override the `qs` property
   and add effective-value properties for values the view needs to pass to a service.
3. Wire into the view:
   - `ListAPIView`: set `filter_backends = [DjangoFilterBackend]` and `filterset_class = MyFilter`.
   - `GenericAPIView` with a custom `get()`: instantiate `MyFilter(request.GET, queryset=base_qs)` and use `f.qs` as the filtered queryset.

Only write manual query-param parsing when `django_filters` genuinely cannot express
the filtering logic. Document the reason inline.

---

## Serializer File Layout

Every app uses a `serializers/` package — never a flat `serializers.py` module.

```
app/
├── serializers/
│   ├── __init__.py   # re-exports public symbols when no read layer exists yet
│   ├── write.py      # mutation (POST/PUT) serializers
│   └── read.py       # query (GET) serializers — only add when the app has read-specific logic
```

**Rules:**

- `write.py` — all serializers used by write endpoints (creation, updates, input validation).
- `read.py` — all serializers used by read endpoints (response shaping, computed fields, polymorphic output). Create this file only when the app genuinely needs read-specific serializers.
- `__init__.py` — re-exports from `write.py` only, so callers that haven't adopted the explicit import path yet continue to work:
  ```python
  from .write import FooSerializer  # noqa: F401
  ```
  Once a `read.py` exists, callers **must** import from `serializers.read` or `serializers.write` explicitly. Remove the `__init__.py` re-export at that point to prevent ambiguity.

**Import style in views and tests:**

```python
# views.py
from .serializers.read import FooReaderSerializer
from .serializers.write import FooSerializer

# tests/
from myapp.serializers.write import FooSerializer
from myapp.serializers.read import FooReaderSerializer
```

Never import from `app.serializers` directly once a `read.py` exists in that app.
