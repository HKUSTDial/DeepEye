# Security Model

DeepEye is an active development preview. This document describes the current
security boundary assumptions and the hardening work required before exposing the
system beyond a trusted development environment.

## Trust Boundaries

DeepEye currently has these major trust boundaries:

| Boundary | Current Status | Required Care |
| --- | --- | --- |
| Browser to gateway | Cookie-authenticated app traffic through nginx | Configure CORS, cookies, TLS, and preview auth before shared deployment |
| Gateway to backend API | Internal Docker network | Do not expose backend service ports directly in production-like deployments |
| Backend/worker to runtime-control | Internal API keyed by `DOCKER_CONTROL_API_KEY` | Use a strong key, internal-only network, and least privilege |
| Runtime-control to Docker daemon | High privilege local Docker socket access | Treat as host-level control; isolate from public API surfaces |
| Generated report/dashboard/video code | Model/user-influenced code and templates | Execute only in constrained runtime contexts |
| Uploaded files and datasource credentials | User-provided data and secrets | Sanitize logs, restrict sharing, and encrypt/rotate credentials where applicable |

## Current Safe Use Assumption

The default Docker Compose stack is intended for local development and trusted
evaluation. It should not be considered production hardened.

The stack assumes:

- the host machine and Docker daemon are trusted
- users with access to the app are trusted collaborators
- generated-code workloads run in development containers, not hardened sandboxes
- example credentials have been replaced in `.env`
- no service ports except the gateway are exposed to untrusted networks

## High-Risk Components

### Runtime Control And Docker Socket

`runtime-control` currently owns Docker lifecycle operations and mounts
`/var/run/docker.sock`. This is powerful enough to control containers on the
host. Keep this service private to the Compose network and protect
`DOCKER_CONTROL_API_KEY`.

Hardening direction:

- move Docker control behind a minimal privileged sidecar
- reduce API operations to explicit allowlisted runtime actions
- add per-operation audit logs
- enforce container CPU, memory, filesystem, and network limits
- consider rootless Docker or a separate sandbox host for untrusted workloads

### Generated Code And Artifact Rendering

Report, dashboard, and video flows may process user input, dataset contents, and
LLM output into executable or renderable artifacts.

Hardening direction:

- keep generated-code execution out of the API process
- avoid injecting unsanitized generated HTML/JS into the main application origin
- use isolated origins for previews
- apply CSP headers where practical
- restrict network access for generated-code containers
- enforce timeouts and output size limits

### Secrets And Data Sources

LLM keys, database URLs, MinIO credentials, JWT secrets, and uploaded data must
not appear in logs, frontend state, issue reports, screenshots, or generated
artifacts.

Hardening direction:

- redact known secret fields in logs and events
- avoid returning connection strings to the frontend
- rotate example credentials before shared use
- use separate service accounts for sample and production data

## Deployment Checklist

Before any non-local deployment:

- [ ] Replace all values in `.env` with strong unique secrets.
- [ ] Serve the gateway over TLS.
- [ ] Keep backend, worker, runtime-control, Redis, Postgres, and MinIO on private networks.
- [ ] Set `AUTH_COOKIE_SECURE=true` when using HTTPS.
- [ ] Restrict `BACKEND_CORS_ORIGINS` to exact trusted origins.
- [ ] Use a strong `DOCKER_CONTROL_API_KEY`.
- [ ] Review Docker socket exposure and sandbox resource limits.
- [ ] Confirm preview routes require session ownership.
- [ ] Run `make check` and `make security-scan`.
- [ ] Review dependency and container image scan results.

## Reporting Security Issues

Follow the root [Security Policy](../SECURITY.md). Do not open public issues with
exploit details, tokens, private data, or screenshots containing secrets.
