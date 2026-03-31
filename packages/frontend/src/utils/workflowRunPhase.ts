import type {
  WorkflowArtifact,
  WorkflowArtifactPayload,
  WorkflowRun,
} from '../types'
import {
  parseDashboardProgressLine,
  parseVideoProgressLine,
} from './chatProgress'

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

const DEFAULT_ERROR_SUGGESTION = 'Open Workflow to inspect the failed step and retry.'

const NODE_PHASES: Record<string, NodePhaseDescriptor> = {
  'datasource.read': {
    label: 'Reading data',
    suggestion: 'Open Attached data and verify the selected file or table.',
  },
  'sql.execute': {
    label: 'Running SQL',
    suggestion: 'Review the SQL result and datasource schema, then retry the node.',
  },
  'python.code': {
    label: 'Running Python step',
    suggestion: 'Inspect the Python node inputs and rerun the workflow.',
  },
  'report.generate': {
    label: 'Writing report',
    suggestion: 'Retry the report step or inspect the upstream data inputs.',
  },
  'data.generate_dashboard': {
    label: 'Building dashboard',
    suggestion: 'Open Workflow to inspect the dashboard node and retry the preview deployment.',
  },
  'video.generator': {
    label: 'Generating video',
    suggestion: 'Open Workflow to inspect the video node and retry the render.',
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
      label: 'Running workflow node',
      suggestion: DEFAULT_ERROR_SUGGESTION,
    }
  }
  return NODE_PHASES[nodeType] ?? {
    label: `Running ${nodeType}`,
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
    return buildPhase('dashboard-ready', 'Dashboard preview ready', 'done', {
      detail: 'Preview deployed and ready to open.',
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }
  if (artifact.kind === 'video') {
    return buildPhase('video-ready', 'Video preview ready', 'done', {
      detail: 'Preview deployed and ready to open.',
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }
  if (artifact.kind === 'report') {
    const filename =
      typeof artifact.report_filename === 'string'
        ? artifact.report_filename
        : typeof artifact.report_path === 'string'
          ? artifact.report_path.split('/').pop() ?? null
          : null
    return buildPhase('report-ready', 'Report ready', 'done', {
      detail: filename ? `Generated ${filename}` : 'Report generated successfully.',
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }
  return buildPhase(`${artifact.kind}-ready`, 'Artifact ready', 'done', {
    detail: null,
    suggestion: null,
    nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
    source: 'artifact',
  })
}

export function createPlanningPhase(filePath: string | null) {
  return buildPhase('planning', 'Drafting workflow', 'running', {
    detail: filePath ? `Preparing ${filePath}` : 'Preparing nodes and edges for this run.',
  })
}

export function createRunStartPhase(filePath: string | null) {
  return buildPhase('run-start', 'Running workflow', 'running', {
    detail: filePath ? `Executing ${filePath}` : 'Executing the validated workflow graph.',
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
    return buildPhase(`node-${nodeId}-failed`, `${descriptor.label} failed`, 'error', {
      detail: message ?? `Node ${nodeLabel} failed during execution.`,
      suggestion: descriptor.suggestion ?? DEFAULT_ERROR_SUGGESTION,
      nodeId,
      nodeType,
    })
  }

  if (status === 'success' || status === 'completed') {
    return null
  }

  return buildPhase(`node-${nodeId}-running`, descriptor.label, 'running', {
    detail: message ?? `Currently executing node ${nodeLabel}.`,
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
    return buildPhase('report-progress', 'Writing report', 'running', {
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
    return buildPhase('dashboard-refresh', 'Dashboard preview refreshed', 'done', {
      detail: 'Latest dashboard changes are deployed.',
      suggestion: null,
      nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : null,
      source: 'artifact',
    })
  }

  if (phase === 'artifact_failed') {
    const detail = extractMessage(payload) ?? `${artifact.kind} generation failed.`
    const suggestion =
      artifact.kind === 'dashboard'
        ? 'Open Workflow to inspect the dashboard node and retry the preview deployment.'
        : artifact.kind === 'video'
          ? 'Open Workflow to inspect the video node and retry the render.'
          : artifact.kind === 'report'
            ? 'Retry the report step or inspect the upstream data inputs.'
            : DEFAULT_ERROR_SUGGESTION
    return buildPhase(`${artifact.kind}-failed`, `${artifact.kind} failed`, 'error', {
      detail,
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
    return buildPhase('dashboard-progress', 'Building dashboard', dashboardLine.status === 'error' ? 'error' : dashboardLine.status === 'done' ? 'done' : 'running', {
      detail: dashboardLine.detail ?? dashboardLine.label,
      suggestion:
        dashboardLine.status === 'error'
          ? 'Open Workflow to inspect the dashboard node and retry the preview deployment.'
          : null,
      source: 'token',
    })
  }

  const videoLine = parseVideoProgressLine(text)
  if (videoLine) {
    return buildPhase('video-progress', 'Generating video', videoLine.status === 'error' ? 'error' : videoLine.status === 'done' ? 'done' : 'running', {
      detail: videoLine.detail ?? videoLine.label,
      suggestion:
        videoLine.status === 'error'
          ? 'Open Workflow to inspect the video node and retry the render.'
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
    return buildPhase('run-complete', 'Workflow complete', 'done', {
      detail: currentPhase?.status === 'done' ? currentPhase.detail : 'All workflow steps completed successfully.',
      suggestion: null,
    })
  }

  return buildPhase(
    currentPhase?.nodeId ? `node-${currentPhase.nodeId}-failed` : 'run-failed',
    currentPhase?.nodeId ? `${currentPhase.label.replace(/\s+completed$|\s+failed$/i, '')} failed` : 'Workflow failed',
    'error',
    {
      detail: error ?? currentPhase?.detail ?? 'The workflow run stopped before completion.',
      suggestion: currentPhase?.suggestion ?? DEFAULT_ERROR_SUGGESTION,
      nodeId: currentPhase?.nodeId ?? null,
      nodeType: currentPhase?.nodeType ?? null,
    },
  )
}

export function createGenericErrorPhase(message: string, suggestion?: string | null) {
  return buildPhase('workflow-error', 'Workflow failed', 'error', {
    detail: normalizeDetail(message),
    suggestion: suggestion ?? DEFAULT_ERROR_SUGGESTION,
  })
}

export function createConnectionLostPhase() {
  return buildPhase('connection-lost', 'Connection lost', 'error', {
    detail: 'The live event stream disconnected while the run was active.',
    suggestion: 'Reconnect to the session or retry the run once the stream is back.',
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
