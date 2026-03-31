# DeepEye Backend

FastAPI and Celery backend for the DeepEye data agent system.

## Responsibilities

- authentication and session management
- datasource, session, and workspace-state APIs
- chat orchestration and workflow planning
- workflow draft/run/artifact persistence
- sandbox-backed execution for report, dashboard, and video nodes

## Recommended Development Flow

Run the backend as part of the monorepo Docker stack:

```bash
docker compose up --build
```

The API is then available behind the gateway at `http://localhost:8080/api/...`.

If you need to apply schema migrations manually outside Docker:

```bash
uv run alembic -c packages/backend/alembic.ini upgrade head
```

## Tests

Default backend and core tests:

```bash
uv run pytest packages/backend/app/test packages/core/tests -q
```

Docker-backed sandbox integration tests are opt-in:

```bash
DEEPEYE_RUN_DOCKER_TESTS=1 uv run pytest \
  packages/backend/app/test/test_sandbox.py \
  packages/backend/app/test/test_sandbox_manager.py -q
```

## Notes

- Runtime schema changes now go through Alembic migrations. Docker Compose runs `alembic upgrade head` before the API and worker start.
- Open-source hardening work is tracked in `docs/open_source_remediation_checklist.md`.
