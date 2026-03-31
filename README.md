# DeepEye

DeepEye is a workflow-native data agent system for multi-step analysis over uploaded files and live databases.

The current monorepo contains:

- `packages/backend`: FastAPI API, Celery workers, workflow orchestration, sandbox management
- `packages/core`: shared agent and workflow primitives
- `packages/frontend`: React workspace UI for chat, workflow, report, dashboard, and video preview panels
- `docker/`: runtime images and local development stack
- `docs/`: architecture notes, RFCs, and subsystem design documents

## Quick Start

1. Copy the environment template and fill in the required secrets:

   ```bash
   cp env.example .env
   ```

2. Start the local stack:

   ```bash
   docker compose up --build
   ```

3. Open the app:

   ```text
   http://localhost:8080
   ```

## Quality Checks

- Default tests:

  ```bash
  uv run pytest packages/backend/app/test packages/core/tests -q
  ```

- Docker-backed integration tests are opt-in:

  ```bash
  DEEPEYE_RUN_DOCKER_TESTS=1 uv run pytest packages/backend/app/test/test_sandbox.py packages/backend/app/test/test_sandbox_manager.py -q
  ```

## Open Source Hardening Status

Active remediation work is tracked in [docs/open_source_remediation_checklist.md](/home/liboyan/project/DeepEye/docs/open_source_remediation_checklist.md).

Before internet-facing deployment, review the execution model carefully:

- report/dashboard/video flows still rely on generated code paths
- backend services still orchestrate Docker-backed runtimes
- architecture is being converged onto `session -> turn -> draft -> run -> artifact`
