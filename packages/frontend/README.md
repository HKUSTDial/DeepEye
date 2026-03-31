# DeepEye Frontend

React + TypeScript workspace UI for DeepEye.

## Responsibilities

- chat workspace and session navigation
- datasource attachment and workspace state management
- workflow editor and live workflow panel
- report, dashboard, and video preview panels

## Local Development

Recommended path: run the full monorepo via Docker Compose from the repository root.

If you need to run the frontend alone:

```bash
cd packages/frontend
npm install
npm run dev
```

Environment variables used by the app:

- `VITE_API_URL`
- `VITE_AUTH_URL`
- `VITE_API_TIMEOUT`

## Build

```bash
npm run build
```

## Notes

- The live workspace state is driven by session-scoped workflow draft/run/artifact snapshots.
- Open-source hardening and architecture convergence are tracked in `docs/open_source_remediation_checklist.md`.
