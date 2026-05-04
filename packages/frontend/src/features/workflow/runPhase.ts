import type {
  WorkflowArtifact,
  WorkflowArtifactPayload,
  WorkflowRun,
} from '../../types'
import {
  parseDashboardProgressLine,
  parseVideoProgressLine,
} from '../../utils/chatProgress'
import { translateApp } from '../../locale'
import { getArtifactFileName } from '../../utils/artifactUtils'

export type WorkflowRunPhaseStatus = 'running' | 'done' | 'error'
export type WorkflowRunPhaseSource = 'workflow' | 'artifact' | 'token' | 'system'

export interface WorkflowRunPhaseState {
  key: string
  label: string
  detail: string | null
  status: WorkflowRunPhaseStatus
  suggestion: string | null
  nodeId: string | null
  nodeType: string | null
  source: WorkflowRunPhaseSource
  updatedAt: number
}

type WorkflowArtifactPhase = 'artifact_progress' | 'artifact_ready' | 'artifact_refresh' | 'artifact_failed'

type NodePhaseDescriptor = {
  label: string
  suggestion: string | null
}

const DEFAULT_ERROR_SUGGESTION = translateApp('workflow.suggestionDefault')

const NODE_PHASES: Record<string, NodePhaseDescriptor> = {
  'datasource.read': {
    label: translateApp('workflow.phaseReadingData'),
    suggestion: translateApp('workflow.suggestionData'),
  },
  'sql.execute': {
    label: translateApp('workflow.phaseRunningSql'),
    suggestion: translateApp('workflow.suggestionSql'),
  },
  'python.code': {
    label: translateApp('workflow.phaseRunningPython'),
    suggestion: translateApp('workflow.suggestionPython'),
  },
  'report.generate': {
    label: translateApp('workflow.phaseWritingReport'),
    suggestion: translateApp('workflow.suggestionReport'),
  },
  'data.generate_dashboard': {
    label: translateApp('workflow.phaseBuildingDashboard'),
    suggestion: translateApp('workflow.suggestionDashboard'),
  },
  'video.generator': {
    label: translateApp('workflow.phaseGeneratingVideo'),
    suggestion: translateApp('workflow.suggestionVideo'),
  },
}

function buildPhase(
  key: string,
  label: string,
  status: WorkflowRunPhaseStatus,
  options?: {
    detail?: string | null
    suggestion?: string | null
    nodeId?: string | null
    nodeType?: string | null
    source?: WorkflowRunPhaseSource
  },
): WorkflowRunPhaseState {
  return {
    key,
    label,
    detail: options?.detail ?? null,
    status,
    suggestion: options?.suggestion ?? null,
    nodeId: options?.nodeId ?? null,
    nodeType: options?.nodeType ?? null,
    source: options?.source ?? 'workflow',
    updatedAt: Date.now(),
  }
}

function describeNodeType(nodeType: string | null) {
  if (!nodeType) {
    return {
      label: translateApp('workflow.phaseRunningNode'),
      suggestion: DEFAULT_ERROR_SUGGESTION,
    }
  }
  return NODE_PHASES[nodeType] ?? {
    label: translateApp('workflow.phaseNodeType', { nodeType }),
    suggestion: DEFAULT_ERROR_SUGGESTION,
  }
}

function normalizeDetail(detail: string | null | undefined) {
  if (!detail) return null
  const value = detail.trim()
  return value ? value : null
}

function extractMessage(payload: Record<string, unknown>) {
  const raw = payload.error ?? payload.message
  return typeof raw === 'string' ? normalizeDetail(raw) : null
}

function latestArtifact(artifacts: WorkflowArtifact[]) {
  if (artifacts.length === 0) return null
  return [...artifacts].sort((left, right) => {
    const leftTime = Date.parse(left.created_at || '')
    const rightTime = Date.parse(right.created_at || '')
    return rightTime - leftTime
  })[0] ?? null
}

function buildArtifactDonePhase(artifact: WorkflowArtifactPayload) {
  if (artifact.kind === 'dashboard') {
    return buildPhase('dashboard-ready', translateApp('workflow.phaseDashboardReady'), 'done', {
      detail: translateApp('workflow.phasePreviewReadyDetail'),
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }
  if (artifact.kind === 'video') {
    return buildPhase('video-ready', translateApp('workflow.phaseVideoReady'), 'done', {
      detail: translateApp('workflow.phasePreviewReadyDetail'),
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }
  if (artifact.kind === 'report') {
    const filename = getArtifactFileName(artifact, 'report')
    return buildPhase('report-ready', translateApp('workflow.phaseReportReady'), 'done', {
      detail: filename ? translateApp('workflow.phaseReportGenerated', { filename }) : translateApp('workflow.phaseReportSuccess'),
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }
  return buildPhase(`${artifact.kind}-ready`, translateApp('workflow.phaseArtifactReady'), 'done', {
    detail: null,
    suggestion: null,
    nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
    source: 'artifact',
  })
}

export function createPlanningPhase(filePath: string | null) {
  return buildPhase('planning', translateApp('workflow.phaseDrafting'), 'running', {
    detail: filePath ? translateApp('workflow.phasePreparingFile', { filePath }) : translateApp('workflow.phasePreparingRun'),
  })
}

export function createRunStartPhase(filePath: string | null) {
  return buildPhase('run-start', translateApp('workflow.phaseRunStart'), 'running', {
    detail: filePath ? translateApp('workflow.phaseExecutingFile', { filePath }) : translateApp('workflow.phaseExecutingGraph'),
  })
}

export function createNodePhase(
  nodeId: string,
  nodeType: string | null,
  status: string,
  payload?: Record<string, unknown>,
) {
  const descriptor = describeNodeType(nodeType)
  const message = extractMessage(payload ?? {})
  const nodeLabel = nodeType ? `${nodeId} (${nodeType})` : nodeId

  if (status === 'failed' || status === 'error') {
    return buildPhase(`node-${nodeId}-failed`, translateApp('workflow.phaseNodeFailed', { label: descriptor.label }), 'error', {
      detail: message ?? translateApp('workflow.phaseNodeFailedDetail', { nodeLabel }),
      suggestion: descriptor.suggestion ?? DEFAULT_ERROR_SUGGESTION,
      nodeId,
      nodeType,
    })
  }

  if (status === 'success' || status === 'completed') {
    return null
  }

  return buildPhase(`node-${nodeId}-running`, descriptor.label, 'running', {
    detail: message ?? translateApp('workflow.phaseNodeRunningDetail', { nodeLabel }),
    suggestion: null,
    nodeId,
    nodeType,
  })
}

export function createArtifactPhase(
  phase: WorkflowArtifactPhase,
  payload: Record<string, unknown>,
) {
  const artifact =
    typeof payload.artifact === 'object' && payload.artifact
      ? payload.artifact as WorkflowArtifactPayload
      : null

  if (!artifact) {
    return null
  }

  if (phase === 'artifact_progress' && artifact.kind === 'report') {
    const message = typeof payload.message === 'string' ? normalizeDetail(payload.message) : null
    return buildPhase('report-progress', translateApp('workflow.phaseWritingReport'), 'running', {
      detail: message,
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }

  if (phase === 'artifact_ready') {
    return buildArtifactDonePhase(artifact)
  }

  if (phase === 'artifact_refresh' && artifact.kind === 'dashboard') {
    return buildPhase('dashboard-refresh', translateApp('workflow.phaseDashboardRefreshed'), 'done', {
      detail: translateApp('workflow.phaseDashboardChanges'),
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }

  if (phase === 'artifact_failed') {
    const detail = extractMessage(payload) ?? `${artifact.kind} generation failed.`
    const suggestion =
      artifact.kind === 'dashboard'
        ? translateApp('workflow.suggestionDashboard')
        : artifact.kind === 'video'
          ? translateApp('workflow.suggestionVideo')
          : artifact.kind === 'report'
            ? translateApp('workflow.suggestionReport')
            : DEFAULT_ERROR_SUGGESTION
    return buildPhase(`${artifact.kind}-failed`, translateApp('workflow.phaseArtifactFailed', { kind: artifact.kind }), 'error', {
      detail: detail || translateApp('workflow.phaseArtifactFailedDetail', { kind: artifact.kind }),
      suggestion,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }

  return null
}

export function createTokenPhase(text: string) {
  const dashboardLine = parseDashboardProgressLine(text)
  if (dashboardLine) {
    return buildPhase('dashboard-progress', translateApp('workflow.phaseBuildingDashboard'), dashboardLine.status === 'error' ? 'error' : dashboardLine.status === 'done' ? 'done' : 'running', {
      detail: dashboardLine.detail ?? dashboardLine.label,
      suggestion:
        dashboardLine.status === 'error'
          ? translateApp('workflow.suggestionDashboard')
          : null,
      source: 'token',
    })
  }

  const videoLine = parseVideoProgressLine(text)
  if (videoLine) {
    return buildPhase('video-progress', translateApp('workflow.phaseGeneratingVideo'), videoLine.status === 'error' ? 'error' : videoLine.status === 'done' ? 'done' : 'running', {
      detail: videoLine.detail ?? videoLine.label,
      suggestion:
        videoLine.status === 'error'
          ? translateApp('workflow.suggestionVideo')
          : null,
      source: 'token',
    })
  }

  return null
}

export function createRunCompletionPhase(
  status: string,
  error: string | null,
  currentPhase: WorkflowRunPhaseState | null,
) {
  if (status === 'success' || status === 'completed') {
    return buildPhase('run-complete', translateApp('workflow.phaseRunComplete'), 'done', {
      detail: currentPhase?.status === 'done' ? currentPhase.detail : translateApp('workflow.phaseRunCompleteDetail'),
      suggestion: null,
    })
  }

  return buildPhase(
    currentPhase?.nodeId ? `node-${currentPhase.nodeId}-failed` : 'run-failed',
    currentPhase?.nodeId ? translateApp('workflow.phaseNodeFailed', { label: currentPhase.label.replace(/\s+completed$|\s+failed$/i, '') }) : translateApp('workflow.phaseRunFailed'),
    'error',
    {
      detail: error ?? currentPhase?.detail ?? translateApp('workflow.phaseRunStopped'),
      suggestion: currentPhase?.suggestion ?? DEFAULT_ERROR_SUGGESTION,
      nodeId: currentPhase?.nodeId ?? null,
      nodeType: currentPhase?.nodeType ?? null,
    },
  )
}

export function createGenericErrorPhase(message: string, suggestion?: string | null) {
  return buildPhase('workflow-error', translateApp('workflow.phaseRunFailed'), 'error', {
    detail: normalizeDetail(message),
    suggestion: suggestion ?? DEFAULT_ERROR_SUGGESTION,
  })
}

export function createConnectionLostPhase() {
  return buildPhase('connection-lost', translateApp('workflow.phaseConnectionLost'), 'error', {
    detail: translateApp('workflow.phaseConnectionLostDetail'),
    suggestion: translateApp('workflow.phaseConnectionLostSuggestion'),
    source: 'system',
  })
}

export function deriveRunPhaseFromSnapshot(
  run: WorkflowRun | null,
  artifacts: WorkflowArtifact[],
) {
  if (!run) {
    return null
  }

  if (run.status === 'running') {
    return createRunStartPhase(run.file_path ?? null)
  }

  if (run.status === 'failed' || run.status === 'error') {
    return createRunCompletionPhase(run.status, run.error ?? null, null)
  }

  const artifact = latestArtifact(artifacts)?.payload ?? null
  if (artifact) {
    return buildArtifactDonePhase(artifact)
  }

  return createRunCompletionPhase(run.status, run.error ?? null, null)
}
