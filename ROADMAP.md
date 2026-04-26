# Roadmap

DeepEye is currently focused on stabilizing the public development preview.

## Current Focus

- Improve setup, documentation, and contributor onboarding.
- Strengthen sandbox, generated-code execution, and runtime-control boundaries.
- Consolidate the workflow model around `session -> turn -> draft -> run -> artifact`.
- Keep backend/core/frontend checks reliable in CI.
- Continue reducing legacy paths and duplicated state handling.
- Make artifact rendering depend on a stable typed artifact protocol.
- Add repeatable local quality gates and security scans.

## Near-Term Goals

- Document API groups and auth/session concepts.
- Provide a small reproducible demo dataset and workflow walkthrough.
- Improve production hardening guidance for deployments beyond local development.
- Add more focused tests around workflow node execution and artifact persistence.
- Improve dependency and container image update automation.
- Introduce the artifact protocol normalization layer described in `docs/rfcs/artifact_protocol.md`.
- Start behavior-preserving splits of the largest backend node implementation files.

## Later Goals

- Define release/versioning policy.
- Publish architecture diagrams and threat model notes.
- Split reusable workflow node implementations if they outgrow the backend runtime layer.
- Add benchmark or evaluation examples for common analytical workflows.

## Not Yet Stable

- Public API contracts
- Workflow node schema compatibility
- Generated dashboard/video internals
- Production deployment guidance
- Release cadence
