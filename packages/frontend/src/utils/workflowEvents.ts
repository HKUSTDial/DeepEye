import type { AgentEvent } from '../api'
import type { WorkflowArtifactPayload, WorkflowRun } from '../types'

type WorkflowEventLike = Pick<AgentEvent, 'type' | 'data'> | { type?: string; data?: Record<string, unknown> }

export interface ParsedWorkflowEvent {
  data: Record<string, unknown>
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
  const payload = typeof data.payload === 'object' && data.payload ? data.payload as Record<string, unknown> : {}
  const artifact =
    typeof payload.artifact === 'object' && payload.artifact
      ? payload.artifact as WorkflowArtifactPayload
      : null

  return {
    data,
    payload,
    phase: typeof data.phase === 'string' ? data.phase : '',
    filePath: typeof data.file_path === 'string' ? data.file_path : null,
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

  return {
    id: typeof data.run_id === 'string' ? data.run_id : `workflow-event:${sessionId}`,
    workflow_id: null,
    session_id: sessionId,
    turn_id: typeof data.turn_id === 'string' ? data.turn_id : null,
    draft_id: typeof data.draft_id === 'string' ? data.draft_id : null,
    source: options?.source ?? 'chat_workflow',
    file_path: typeof data.file_path === 'string' ? data.file_path : null,
    status,
    error: options?.error || undefined,
    created_at: new Date().toISOString(),
    finished_at: status === 'running' ? null : new Date().toISOString(),
  }
}

export function matchesTrackedWorkflowEvent(
  currentRun: WorkflowRun | null | undefined,
  currentDraftId: string | null | undefined,
  activeFilePath: string | null | undefined,
  event: ParsedWorkflowEvent,
): boolean {
  if (currentRun?.id && event.runId && currentRun.id !== event.runId) {
    return false
  }

  if (!currentRun?.id && currentRun?.draft_id && event.draftId && currentRun.draft_id !== event.draftId) {
    return false
  }

  if (!currentRun?.id && !currentRun?.draft_id && currentDraftId && event.draftId && currentDraftId !== event.draftId) {
    return false
  }

  if (!currentRun?.id && !currentRun?.draft_id && event.filePath && activeFilePath && activeFilePath !== event.filePath) {
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
