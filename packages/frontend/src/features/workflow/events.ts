import type { AgentEvent } from '../../api'
import type { WorkflowArtifactPayload, WorkflowRun } from '../../types'

type WorkflowEventLike = Pick<AgentEvent, 'type' | 'data'> | { type?: string; data?: Record<string, unknown> }

export interface ParsedWorkflowEvent {
  data: Record<string, unknown>
  metadata: Record<string, unknown>
  payload: Record<string, unknown>
  phase: string
  filePath: string | null
  runId: string | null
  draftId: string | null
  turnId: string | null
  artifact: WorkflowArtifactPayload | null
  artifactKind: string | null
}

function isParsedWorkflowEvent(
  event: ParsedWorkflowEvent | Record<string, unknown> | undefined,
): event is ParsedWorkflowEvent {
  return !!event && typeof event === 'object' && 'data' in event && 'phase' in event && 'payload' in event
}

export function parseWorkflowEvent(event: WorkflowEventLike): ParsedWorkflowEvent | null {
  if (event.type !== 'workflow_event') {
    return null
  }

  const data = typeof event.data === 'object' && event.data ? event.data as Record<string, unknown> : {}
  const metadata = typeof data.metadata === 'object' && data.metadata ? data.metadata as Record<string, unknown> : {}
  const payload = typeof data.payload === 'object' && data.payload ? data.payload as Record<string, unknown> : {}
  const artifact =
    typeof payload.artifact === 'object' && payload.artifact
      ? payload.artifact as WorkflowArtifactPayload
      : null

  return {
    data,
    metadata,
    payload,
    phase: typeof data.phase === 'string' ? data.phase : '',
    filePath:
      typeof metadata.file_path === 'string'
        ? metadata.file_path
        : typeof data.file_path === 'string'
          ? data.file_path
          : null,
    runId: typeof data.run_id === 'string' ? data.run_id : null,
    draftId: typeof data.draft_id === 'string' ? data.draft_id : null,
    turnId: typeof data.turn_id === 'string' ? data.turn_id : null,
    artifact,
    artifactKind: typeof artifact?.kind === 'string' ? artifact.kind : null,
  }
}

export function buildWorkflowRunFromEvent(
  sessionId: string,
  event: ParsedWorkflowEvent | Record<string, unknown> | undefined,
  status: string,
  options?: {
    error?: string | null
    source?: string
  },
): WorkflowRun {
  const data: Record<string, unknown> = isParsedWorkflowEvent(event) ? event.data : (event ?? {})
  const metadata: Record<string, unknown> = isParsedWorkflowEvent(event)
    ? event.metadata
    : (typeof data.metadata === 'object' && data.metadata ? data.metadata as Record<string, unknown> : {})
  const filePath =
    typeof metadata.file_path === 'string'
      ? metadata.file_path
      : typeof data.file_path === 'string'
        ? data.file_path
        : null

  return {
    id: typeof data.run_id === 'string' ? data.run_id : `workflow-event:${sessionId}`,
    workflow_id: null,
    session_id: sessionId,
    turn_id: typeof data.turn_id === 'string' ? data.turn_id : null,
    draft_id: typeof data.draft_id === 'string' ? data.draft_id : null,
    source: options?.source ?? 'chat_workflow',
    file_path: filePath,
    status,
    error: options?.error || undefined,
    created_at: new Date().toISOString(),
    finished_at: status === 'running' ? null : new Date().toISOString(),
  }
}

export function matchesTrackedWorkflowEvent(
  currentRun: WorkflowRun | null | undefined,
  currentDraftId: string | null | undefined,
  event: ParsedWorkflowEvent,
): boolean {
  if (currentRun?.id) {
    if (event.runId) {
      return currentRun.id === event.runId
    }
    const trackedDraftId = currentRun.draft_id ?? currentDraftId ?? null
    if (event.draftId && trackedDraftId) {
      return trackedDraftId === event.draftId
    }
    return false
  }

  const trackedDraftId = currentRun?.draft_id ?? currentDraftId ?? null
  if (trackedDraftId) {
    if (event.draftId) {
      return trackedDraftId === event.draftId
    }
    return false
  }

  return true
}

export function getWorkflowArtifacts(payload: Record<string, unknown>): WorkflowArtifactPayload[] {
  if (!Array.isArray(payload.artifacts)) {
    return []
  }
  return payload.artifacts.filter(
    (item): item is WorkflowArtifactPayload => typeof item === 'object' && item !== null,
  )
}

export function getWorkflowOutputs(payload: Record<string, unknown>): Record<string, unknown> | null {
  return typeof payload.outputs === 'object' && payload.outputs
    ? payload.outputs as Record<string, unknown>
    : null
}
