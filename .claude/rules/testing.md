# Testing Conventions

## Framework

Use `django.test.TestCase` for all tests. Use `rest_framework.test.APIClient` for API tests.
Do not use pytest — the project uses Django's built-in test runner.

Run tests: `uv run python manage.py test`

## Test Structure

```python
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.urls import reverse


class FeatureTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("url_name")
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.user = User.objects.create_user(
            username="user", email="user@example.com", password="userpass"
        )
```

## Tests Are Mandatory

Every new endpoint requires tests before the implementation exists (TDD). No endpoint may be merged
without covering the four cases below. This is not optional.

After writing the tests and confirming they fail, **stop and present the tests to the user for explicit
approval** before writing any implementation code. Only proceed once the user confirms the test cases
are correct.

## What to Test for Every Endpoint

For every endpoint, cover these four cases:

1. **Unauthenticated** → `401 UNAUTHORIZED`
2. **Authenticated, wrong permission** → `403 FORBIDDEN`
3. **Happy path** → `201 CREATED` (POST) or `200 OK` (GET), check both response and DB state
4. **Validation errors** → `400 BAD_REQUEST`, assert the correct field name appears in `response.data`

For `AllowAny` endpoints (e.g., login), replace cases 1 and 2 with:
- **Valid credentials** → expected success status + token/data in response
- **Invalid credentials** → `400 BAD_REQUEST` with the correct error field

## Naming Convention

`test_<action>_<condition>`:
- `test_create_pagamento_requires_authentication`
- `test_create_pagamento_requires_superuser`
- `test_create_pagamento_with_valid_data`
- `test_create_pagamento_missing_valor_total`

## Authentication

Always use `self.client.force_authenticate(user=...)` — never use real Knox tokens in tests.

## Assertions

```python
# Status codes
self.assertEqual(response.status_code, status.HTTP_201_CREATED)

# Database state
self.assertEqual(Model.objects.count(), 1)
obj = Model.objects.first()
self.assertEqual(obj.field, expected_value)

# Validation errors — check field name is present
self.assertIn("field_name", response.data)
```

Always verify the database state for write operations — don't rely only on the response.

## Test Coverage for DB Writes

For every write endpoint, verify both the response and the database state:

```python
# After POST that creates two records atomically
self.assertEqual(ParentModel.objects.count(), 1)
self.assertEqual(ChildModel.objects.count(), 1)

parent = ParentModel.objects.first()
child = ChildModel.objects.get(parent=parent)
self.assertEqual(child.some_field, expected_value)
```

For service-layer operations that update status, verify the subtype model directly — not just the response:

```python
implantacao.refresh_from_db()
self.assertEqual(implantacao.status, StatusPagamento.PAGO)
```
