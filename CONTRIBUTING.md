# Contributing to DeepEye

DeepEye is currently in active development preview. Contributions are welcome, but internal APIs and module boundaries are still being stabilized.

## Before You Start

- Read the root [README.md](README.md) and [docs/README.md](docs/README.md).
- Check existing issues and pull requests to avoid duplicate work.
- Keep changes focused. Avoid mixing unrelated refactors with feature or bug fixes.
- Treat sandbox, generated-code execution, authentication, and data-source handling as security-sensitive areas.

## Development Setup

Copy the example environment file and adjust local values:

```bash
cp env.example .env
```

Start the local stack:

```bash
docker compose up --build
```

For Python development:

```bash
uv sync --all-groups
uv run pytest packages/backend/app/test packages/core/tests -q
```

For frontend development:

```bash
cd packages/frontend
npm install
npm run lint
npm test -- --maxWorkers=1 --no-file-parallelism
npm run build
```

For the full local CI equivalent:

```bash
make check
```

Install dependencies and then run all checks:

```bash
make check-install
```

Validate Docker Compose configuration:

```bash
make compose-config
```

## Project Boundaries

- `packages/core` contains reusable agent, datasource, sandbox protocol, and workflow engine primitives.
- `packages/backend` owns FastAPI, persistence, Celery, Docker/runtime integrations, concrete workflow nodes, and deployment-facing services.
- `packages/frontend` owns the React workspace.
- `packages/core` must not import `app.*` or backend modules. Runtime services should pass integrations into core through protocols, callbacks, or tool lists.

## Pull Request Checklist

- Add or update tests for behavioral changes.
- Update docs when setup, architecture, API behavior, or security posture changes.
- Run the relevant checks locally before opening a PR.
- Use `make check` for broad changes and mention any skipped checks.
- Keep generated files and local artifacts out of commits.
- Explain user-visible behavior and migration impact in the PR description.

## Commit Style

Use concise, imperative commit messages. Examples:

```text
fix: handle missing workflow artifacts
docs: clarify local setup
refactor: tighten core backend boundary
```

## Security-Sensitive Changes

Do not open public issues or PR comments containing exploitable details. Follow [SECURITY.md](SECURITY.md) for vulnerability reporting.
