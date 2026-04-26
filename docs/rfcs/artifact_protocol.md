# Artifact Protocol RFC

Status: Draft

## Problem

DeepEye produces reports, dashboards, files, tables, and video previews. Some
frontend and backend paths still infer artifact behavior from fields such as
`dashboard_url`, `file_path`, or ad hoc output shapes. This makes UI behavior
harder to reason about and causes each node type to grow special cases.

## Goals

- Make artifact rendering depend on a stable typed contract.
- Keep workflow node outputs flexible while normalizing persisted artifacts.
- Let the frontend render artifacts by `artifact.kind` and `artifact.status`.
- Make artifact persistence, preview, download, and failure states testable.

## Non-Goals

- Freeze every node output schema immediately.
- Remove existing compatibility fields in one change.
- Define a public API stability guarantee before the preview matures.

## Proposed Shape

```json
{
  "id": "artifact-id",
  "session_id": "session-id",
  "turn_id": "turn-id",
  "run_id": "run-id",
  "node_id": "dashboard",
  "kind": "dashboard",
  "status": "ready",
  "title": "Revenue Dashboard",
  "summary": "Optional short user-facing summary",
  "payload": {
    "dashboard_url": "/dashboards/example/",
    "output_path": "/workspace/.workflow_scripts/dashboard"
  },
  "preview": {
    "type": "url",
    "url": "/dashboards/example/"
  },
  "files": [
    {
      "name": "dashboard_config.json",
      "path": "/workspace/.workflow_scripts/dashboard/dashboard_config.json",
      "mime_type": "application/json",
      "download_url": null
    }
  ],
  "created_at": "2026-04-26T00:00:00Z",
  "updated_at": "2026-04-26T00:00:00Z"
}
```

## Required Fields

| Field | Meaning |
| --- | --- |
| `id` | Stable artifact identifier |
| `session_id` | Owning session |
| `turn_id` | User turn that produced the artifact |
| `run_id` | Workflow run that produced the artifact |
| `node_id` | Producing workflow node |
| `kind` | Renderer selector: `report`, `dashboard`, `table`, `file`, `video`, `dataset`, `unknown` |
| `status` | `pending`, `running`, `ready`, `failed`, `expired` |
| `payload` | Kind-specific data, not used as the primary renderer selector |

## Preview Contract

`preview.type` should describe how the frontend opens the artifact:

- `html`: render sanitized/persisted HTML content
- `url`: open an authenticated preview URL
- `file`: open or download a stored file
- `table`: render structured rows/columns
- `none`: artifact is recorded but has no preview

## Migration Plan

1. Add a backend normalization helper that maps node outputs to this artifact
   shape.
2. Update tests for report, dashboard, video, file, and dataset artifacts.
3. Update frontend panels to select renderers by `artifact.kind` and
   `preview.type`.
4. Keep legacy payload fields for one compatibility window.
5. Remove frontend heuristics that infer artifact type from `dashboard_url`,
   `file_path`, or similar fields.

## Acceptance Criteria

- New artifact renderers need only a `kind` and `preview.type` registration.
- Existing report/dashboard/video flows persist valid normalized artifacts.
- Frontend behavior is covered by focused tests for each artifact kind.
- Failure artifacts include `status=failed` and a safe, user-facing error
  summary without secret-bearing details.
