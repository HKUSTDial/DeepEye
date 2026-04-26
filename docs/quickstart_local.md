# Local Quickstart

This guide is the shortest path for a new contributor to run DeepEye locally and
validate that the development environment works.

## Prerequisites

- Docker and Docker Compose
- `uv`
- Node.js 20 and npm, only when running frontend checks outside Docker
- An LLM API key and model name

## 1. Configure Environment

```bash
cp env.example .env
```

Edit `.env` and set at least:

- `COMPOSE_PROJECT_NAME`
- `HOST_GATEWAY_PORT`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `DOCKER_CONTROL_API_KEY`

Use unique values on shared machines to avoid container, volume, and port
conflicts.

## 2. Validate Configuration

```bash
make compose-config
```

This checks that Docker Compose can parse the stack and environment.

## 3. Start DeepEye

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

If you changed `HOST_GATEWAY_PORT`, use that port instead.

## 4. Confirm Services

In another terminal:

```bash
docker compose ps
```

The important services are:

- `gateway`
- `frontend`
- `backend-api`
- `backend-worker`
- `runtime-control`
- `postgres`
- `redis`
- `minio`

For a deeper smoke test after the stack is running:

```bash
make compose-smoke
```

## 5. Try A Minimal Workflow

Use the UI to create a session, attach a small CSV, and ask for a simple report
or summary. For reference data and scenario notes, see:

- [Retail ops workflow sample](test/retail_ops_workflow_sample.md)
- [Knowledge base demo checklist](test/knowledge_base_demo_checklist.md)

## 6. Run Local Quality Checks

Fast backend/core check:

```bash
make check-python
```

Full local CI equivalent:

```bash
make check
```

Install dependencies before checking:

```bash
make check-install
```

## Troubleshooting

### Port Already In Use

Set a different `HOST_GATEWAY_PORT` in `.env`, then restart the stack.

### Docker Permission Errors

Confirm your user can run:

```bash
docker ps
```

If not, fix local Docker permissions before running DeepEye.

### Startup Warmup Fails

Check `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and provider network access.
For local debugging only, you can temporarily set:

```text
STARTUP_WARMUP_STRICT=false
```

### Reset Local Data

This removes local containers and volumes for the current Compose project:

```bash
docker compose down -v
```

Only use this when you intend to delete local development data.
