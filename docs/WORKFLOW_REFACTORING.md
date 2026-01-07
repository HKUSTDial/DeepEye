# Workflow Refactor Plan

This document defines the unified architecture for workflow streaming, session switching, and rendering.
It replaces ad-hoc patches with a single state machine and a single event protocol.

## Goals
- Single source of truth per session.
- No view flashes during session switching.
- Streaming uses draft state; rendering uses validated state.
- Back-end emits one workflow event type with consistent fields.

## Frontend Architecture
### Session-Scoped State
Each session owns an independent workflow state:
- `files`: list of workflow JSON files under `/workspace/workflow`
- `activeFilePath`
- `draftGraph`: incrementally built from streaming events
- `validatedGraph`: validated graph used for rendering
- `runState`: running/success/failed
- `viewState`: `idle | switching | ready | empty | error`

### State Machine
```
idle -> switching -> ready
idle -> switching -> empty
ready -> switching -> ready
ready -> switching -> empty
any -> error
```

Transition rules:
- `switching` keeps last `validatedGraph` on screen.
- `ready` only updates after validation succeeds.
- `empty` clears `validatedGraph` but does not flash during switch.

### Rendering Rules
- Render `validatedGraph` only.
- `draftGraph` is never rendered directly.
- Promote `draftGraph` to `validatedGraph` only if validation passes.

## Backend Event Protocol
All workflow streaming events should follow this shape:
```
{
  "type": "workflow_event",
  "session_id": "<uuid>",
  "file_path": "/workspace/workflow/<name>.json",
  "phase": "create_file|node|edge|run_start|run_end|error",
  "payload": { ... }
}
```

Notes:
- `session_id` must be explicit in the payload.
- `file_path` must be present for all phases.
- `payload` is the node/edge/run info.

## Frontend Event Handling
- Single reducer handles all `workflow_event` messages.
- `phase=node|edge` updates `draftGraph`.
- After each update, validate; if valid, promote to `validatedGraph`.
- `phase=run_start|run_end` updates `runState`.
- `phase=error` sets `viewState=error`.

## Migration Strategy
1) Implement session-scoped store + reducer.
2) Wire `useChat` to the reducer; remove per-event branching.
3) Update `WorkflowLivePanel` to render from `validatedGraph` only.
4) Update backend to emit `workflow_event` with `session_id + file_path`.
5) Remove legacy event branches and old stores.

## Validation Rules (Summary)
- Every edge must reference existing nodes.
- All node `type` must exist in node registry.
- Ports must exist in node definitions.

