# Dependency Management

## Goal

DeepEye uses a single Python dependency workspace at repository root to avoid drift between local development, CI, and Docker.

## Source Of Truth

- Root workspace config: `pyproject.toml`
- Root lockfile: `uv.lock`
- Package manifests:
  - `packages/core/pyproject.toml`
  - `packages/backend/pyproject.toml`

`packages/backend/uv.lock` is intentionally removed. Do not add per-package lockfiles for workspace members.

## Common Commands

Run from repository root:

```bash
uv sync --all-packages --group dev
uv run pytest packages/core/tests packages/backend/app/test
uv run --package deepeye-backend uvicorn app.main:app --reload
uv run --package deepeye-backend celery -A app.core.celery_app worker --loglevel=info
```

## Updating Dependencies

1. Edit dependency declarations in package `pyproject.toml` files.
2. Regenerate lockfile at root:

```bash
uv lock
```

3. Sync environment:

```bash
uv sync --all-packages --group dev
```

## Docker

`docker/Dockerfile.backend` installs dependencies from the root workspace lock with:

```bash
uv sync --frozen --no-dev --package deepeye-backend --project /app
```

This keeps container dependency resolution aligned with local root `uv.lock`.
