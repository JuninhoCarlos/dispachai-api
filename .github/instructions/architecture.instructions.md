---
applyTo: "**/*.py"
---

# Architecture Guidelines

## Layered Architecture

Strict three-layer model — each layer has exactly one job:

```
Request → View → Serializer → Model → Response
```

### View (`views.py`)

Handles HTTP only:
- Declare `permission_classes`
- Call `serializer.is_valid(raise_exception=True)`
- Call `serializer.save()` or a service method
- Return `Response`

Views must not contain business logic, DB queries outside of `get_queryset()`, or validation rules.
Use DRF generic views (`CreateAPIView`, `ListAPIView`, `GenericAPIView`) whenever they fit.
Keep views under ~40 lines.

### Serializer (`serializers/write.py`, `serializers/read.py`)

Handles validation and data transformation only:
- Override `validate_<field>()` for field-level rules
- Override `validate()` for cross-field rules
- Override `create()` or `update()` for DB writes; wrap multi-model writes in `@transaction.atomic`

Keep serializer `create()` methods under ~30 lines.

### Model (`models.py`)

Handles data and data integrity only:
- Field definitions with validators
- `class Meta` constraints
- Simple `@property` helpers

Models must not import serializers or contain business-flow logic.

## Authentication Policy

Every write endpoint requires authentication. No exceptions without justification.

| Permission class | When to use |
|---|---|
| `IsSuperUser` | Create/update/delete on admin-owned resources |
| `IsAuthenticated` | Read-only endpoints any authenticated user may access |
| `AllowAny` | Login endpoint only — must have inline justification comment |

```python
permission_classes = [AllowAny]  # Public login — no auth context available at this point
```

Never omit `permission_classes` from a view.

## When a Service Layer Is Permitted

Default path: **view → serializer → model**. No service layer.

A service (in `<app>/services/`) is only permitted when **all three** are true:

1. The operation spans **multiple models** not naturally related through a single serializer `create()`
2. The logic involves **stateful transitions**
3. The same logic must be **reused from more than one call site**

Do not create a service file speculatively.

## Serializer File Layout

Every app uses a `serializers/` package — never a flat `serializers.py` module:

```
app/
├── serializers/
│   ├── __init__.py   # re-exports from write.py only
│   ├── write.py      # mutation serializers
│   └── read.py       # query serializers — only add when needed
```

Import style:
```python
# views.py
from .serializers.read import FooReaderSerializer
from .serializers.write import FooSerializer
```

Never import from `app.serializers` directly once a `read.py` exists in that app.
