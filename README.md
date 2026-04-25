# DeepEye

> **Project Status: Active Development Preview**
>
> DeepEye is being shared publicly while the codebase, documentation, tests, deployment workflow, and security hardening are still being actively improved. The repository is useful for local evaluation, collaboration, and understanding the architecture, but APIs, internal contracts, and setup details may continue to change as the project is refined.

DeepEye is a workflow-native data agent system for multi-step analysis over uploaded files and live databases. It combines a chat workspace, workflow orchestration, sandboxed execution, and artifact rendering for analytical outputs such as reports, dashboards, and data videos.

## What DeepEye Does

- Turns data analysis requests into visible workflow drafts and execution runs.
- Works with uploaded files and database-backed data sources.
- Produces structured artifacts such as reports, dashboards, tables, files, and video previews.
- Provides a React workspace for chat, workflow inspection, output preview, and session state.
- Runs backend services, workers, storage, and runtime control through a local Docker Compose stack.

## Current Focus

The project is currently being stabilized around a unified workflow model:

```text
session -> turn -> draft -> run -> artifact
```

Ongoing work includes:

- improving documentation and onboarding paths
- tightening generated-code and sandbox execution boundaries
- converging report, dashboard, and video flows onto shared workflow/artifact contracts
- expanding automated tests and integration coverage
- cleaning up legacy or duplicated internal paths

Progress is tracked in [docs/open_source_remediation_checklist.md](docs/open_source_remediation_checklist.md).

## Repository Layout

| Path | Purpose |
| --- | --- |
| [packages/backend](packages/backend) | FastAPI API, Celery workers, workflow orchestration, persistence, sandbox/runtime integration |
| [packages/core](packages/core) | Shared agent, datasource, workflow, graph, and sandbox primitives |
| [packages/frontend](packages/frontend) | React + TypeScript workspace UI for chat, workflow, reports, dashboards, and video preview panels |
| [docker](docker) | Dockerfiles, nginx config, scripts, and local runtime assets |
| [docs](docs) | Architecture notes, RFCs, UI notes, and remediation tracking |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A supported LLM provider key and model
- `uv` for Python development and tests
- Node.js/npm only if running the frontend outside Docker

### 1. Configure Environment

Copy the example environment file:

```bash
cp env.example .env
```

Then update the values in `.env`. At minimum, review:

- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- `RETAIL_OPS_DB_USER`, `RETAIL_OPS_DB_PASSWORD`, `RETAIL_OPS_DB_NAME`
- `HOST_GATEWAY_PORT` if port `8080` is already in use

For shared development machines, set a unique `COMPOSE_PROJECT_NAME` and `HOST_GATEWAY_PORT` to avoid container, volume, and port conflicts.

### 2. Start the Local Stack

```bash
docker compose up --build
```

The Compose stack starts Postgres, Redis, MinIO, the backend API, Celery worker, runtime-control service, frontend, and nginx gateway. Database migrations are applied automatically before backend services start.

### 3. Open DeepEye

By default, the app is available at:

```text
http://localhost:8080
```

If you changed `HOST_GATEWAY_PORT`, use that port instead.

### 4. Stop the Stack

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to remove local volumes and stored development data.

## Development

### Backend and Core

Run the default backend/core test set:

```bash
uv run pytest packages/backend/app/test packages/core/tests -q
```

Run Docker-backed sandbox integration tests explicitly:

```bash
DEEPEYE_RUN_DOCKER_TESTS=1 uv run pytest \
  packages/backend/app/test/test_sandbox.py \
  packages/backend/app/test/test_sandbox_manager.py -q
```

Apply migrations manually when working outside the Compose flow:

```bash
uv run alembic -c packages/backend/alembic.ini upgrade head
```

### Frontend

The recommended path is to run the frontend through Docker Compose with the rest of the stack. For frontend-only development:

```bash
cd packages/frontend
npm install
npm run dev
```

Build the frontend:

```bash
npm run build
```

## Security and Deployment Notes

DeepEye orchestrates LLM-assisted workflows and Docker-backed execution runtimes. Treat the current stack as a local development environment unless you have reviewed and hardened the deployment for your own threat model.

Before exposing DeepEye beyond a trusted local environment:

- replace all example secrets and development credentials
- review authentication, cookie, CORS, and gateway settings
- review Docker socket access and runtime-control boundaries
- review generated-code execution paths for reports, dashboards, and video generation
- set resource limits and cleanup policies appropriate for your infrastructure

## Documentation

- [Backend README](packages/backend/README.md)
- [Frontend README](packages/frontend/README.md)
- [Core README](packages/core/README.md)
- [Workflow-native agent refactor RFC](docs/rfcs/workflow_native_agent_refactor.md)
- [Open-source remediation checklist](docs/open_source_remediation_checklist.md)

## Project Maturity

DeepEye is moving quickly. Some modules are production-shaped, while others are still being consolidated or documented. If you are evaluating the project, please expect active iteration and prefer the documented Docker Compose workflow as the most reliable way to run it locally.
