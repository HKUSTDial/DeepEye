# Maintainability Refactor Plan

Status: Draft

This plan tracks large-file and boundary refactors that should happen after the
current public preview quality gates are stable.

## Principles

- Keep behavior-preserving refactors separate from feature changes.
- Add characterization tests before moving complex execution logic.
- Prefer small modules with explicit inputs over shared mutable state.
- Keep `packages/core` free of `app.*` backend imports.

## Initial Targets

| Area | Current Risk | Target Shape |
| --- | --- | --- |
| `packages/backend/app/tools/workflow_tools.py` | Mixed planning, execution, serialization, and UI-oriented state helpers | Split planner, executor, event mapper, and artifact mapper |
| `packages/backend/app/node/video/config/generator.py` | Large prompt/config/render orchestration surface | Split scene planning, theme normalization, animation planning, and render config validation |
| `packages/backend/app/node/dashboard/nl2dashboard/engineering/dashboard_engineer.py` | Dashboard generation, validation, file layout, and build behavior in one class | Split config validation, template assembly, asset copying, and build orchestration |
| Chat/workflow tracking services | State transitions assembled in several places | Single transition service for turn/run/artifact state changes |

## Workflow

1. Add tests around current behavior.
2. Extract pure helpers first.
3. Move IO and runtime calls behind small interfaces.
4. Update docs and diagrams when a boundary changes.
5. Run `make check` before merging.

## First Concrete Slice

Artifact protocol normalization is the preferred first slice because it reduces
special cases across backend and frontend without requiring a full node rewrite.
See [Artifact Protocol RFC](artifact_protocol.md).
