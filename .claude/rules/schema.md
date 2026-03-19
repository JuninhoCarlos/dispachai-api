# Schema Generation

## Command

```
uv run python manage.py spectacular --color --file schema.yml
```

Run this at the end of any task that changes the public API surface. The generated `schema.yml` is committed to the repo and must stay in sync with the code.

---

## When to Regenerate

Regenerate whenever **any** of the following change:

- A URL is added, removed, or its path/name changes (`urls.py`)
- A view is added or removed, or its HTTP methods change
- A serializer used in a view gains or loses fields, changes a field type, or changes validation that affects the schema
- A model field is added, removed, renamed, or its type changes in a way that flows through to a serializer

---

## When to Skip

Skip regeneration when the change does not affect the public API surface:

- Test-only changes (adding or editing files under `tests/`)
- Internal refactors with no public interface change (renaming a private method, extracting a helper, reordering logic)
- Non-API file changes (settings, migrations that only add indexes, dependency updates, documentation)

If in doubt, run it — the command is fast and idempotent.
