import type {
  WorkflowArtifact,
  WorkflowArtifactPayload,
  WorkflowDraft,
  WorkflowRun,
} from '../types'
import { getArtifactPreviewUrl, latestWorkflowArtifactByKind } from '../utils/artifactUtils'
import type {
  VideoProgressLogEntry,
  WorkflowDefinition,
  WorkflowViewState,
} from './workflowSessions'

export const asObjectRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null

export const getDraftDefinition = (draft: WorkflowDraft | null): WorkflowDefinition => {
  if (!draft) return null
  return asObjectRecord(draft.definition)
}

export const deriveNodeStatus = (run: WorkflowRun | null) => {
  const result = asObjectRecord(run?.result)
  const outputs = asObjectRecord(result?.outputs)
  if (!outputs) {
    return {}
  }

  return Object.fromEntries(
    Object.entries(outputs)
      .filter(([, value]) => !!asObjectRecord(value))
      .map(([nodeId, value]) => {
        const outputsForNode = asObjectRecord(value) || {}
        const nodeStatus =
          typeof outputsForNode.status === 'string' && outputsForNode.status
            ? outputsForNode.status
            : 'completed'
        return [nodeId, { status: nodeStatus, outputs: outputsForNode }]
      }),
  )
}

export const deriveRunOutput = (run: WorkflowRun | null) => {
  const result = asObjectRecord(run?.result)
  const outputs = asObjectRecord(result?.outputs)
  if (outputs) {
    return JSON.stringify(outputs, null, 2)
  }
  if (result) {
    return JSON.stringify(result, null, 2)
  }
  return run?.error || ''
}

export const deriveVideoPreviewUrl = (artifacts: WorkflowArtifact[]) => {
  const videoArtifact = latestWorkflowArtifactByKind(
    artifacts.filter((artifact) => getArtifactPreviewUrl(artifact.payload)),
    'video',
  )
  return videoArtifact ? getArtifactPreviewUrl(videoArtifact.payload) : null
}

export const deriveArtifactPayloads = (artifacts: WorkflowArtifact[]) =>
  artifacts.map((artifact) => artifact.payload)

export const artifactKey = (artifact: WorkflowArtifactPayload) => {
  const nodeId = typeof artifact.node_id === 'string' ? artifact.node_id : ''
  return `${artifact.kind}:${nodeId}`
}

export const deriveViewState = (
  definition: WorkflowDefinition,
  run: WorkflowRun | null,
): WorkflowViewState => {
  if (definition || run) {
    return 'ready'
  }
  return 'empty'
}

export const createProgressLogEntry = (
  message: string,
  now: Date = new Date(),
): VideoProgressLogEntry => ({
  id: `${now.getTime()}-${Math.random().toString(36).slice(2)}`,
  time: now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }),
  message,
})

export const appendCappedLogEntry = (
  logs: VideoProgressLogEntry[],
  entry: VideoProgressLogEntry,
  limit = 50,
) => [...logs, entry].slice(-limit)

export const clampPercent = (percent: number) =>
  Math.min(100, Math.max(0, percent))

export const deriveDashboardStageState = (stage: number, previousStage: number, previousPercent: number) => {
  const boundedStage = Math.max(previousStage, Math.max(0, Math.min(stage, 5)))
  const percentStops = [12, 28, 46, 64, 82, 94]
  return {
    stage: boundedStage,
    percent: percentStops[boundedStage] ?? previousPercent,
  }
}

export const deriveVideoStepPercent = (step: number) =>
  Math.min(99, Math.round((step / 4) * 100))
