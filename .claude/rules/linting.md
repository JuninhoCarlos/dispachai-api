# Linting

## CI/CD Pipeline

The lint workflow (`.github/workflows/lint.yml`) runs two checks on every PR:

1. `uv run black --check .` — formatting
2. `uv run ruff check .` — linting

Both must pass. Passing black alone is not sufficient.

## Required Steps After Every Task

Always run both commands in order before marking a task done:

```
uv run black .
uv run ruff check .
```

Fix any ruff errors before finishing. Do not skip or defer linting.
