# Security Policy

DeepEye orchestrates LLM-assisted workflows, uploaded data, database connections, generated artifacts, and Docker-backed execution runtimes. Treat the current repository as an active development preview unless you have reviewed and hardened it for your own deployment environment.

For a component-level trust boundary overview, see [docs/security_model.md](docs/security_model.md).

## Supported Versions

Security fixes are currently targeted at the default branch.

| Version | Supported |
| --- | --- |
| `master` / default branch | Yes |
| Tagged releases | Not yet established |

## Reporting a Vulnerability

Please do not disclose exploitable details in public issues, pull requests, or discussions.

Preferred reporting path:

1. Use GitHub private vulnerability reporting or GitHub Security Advisories for this repository if enabled.
2. If private reporting is unavailable, open a minimal public issue asking for a secure contact path without including exploit details.

Include the affected component, impact, reproduction conditions, and any suggested mitigation when using a private channel.

## High-Risk Areas

Please review these areas carefully before exposing DeepEye outside a trusted local environment:

- Docker socket and runtime-control access
- sandbox lifecycle, filesystem mounts, and cleanup
- generated report, dashboard, and video code paths
- LLM tool execution and prompt-to-action boundaries
- uploaded files and database connection strings
- authentication, refresh tokens, cookies, CORS, and gateway configuration
- MinIO, Postgres, Redis, and local volume persistence

## Deployment Guidance

Before production-like use:

- replace all example secrets and development credentials
- use least-privilege service accounts and network boundaries
- isolate Docker/runtime control from public API surfaces
- set CPU, memory, storage, and execution time limits
- restrict outbound network access for generated-code workloads where possible
- enable audit logging and container cleanup policies
- review dependency and container image vulnerability scans

Recommended local checks:

```bash
make check
make security-scan
```
