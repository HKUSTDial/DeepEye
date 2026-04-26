import type { WorkflowRunPhaseState } from './runPhase'

export type WorkflowRecoveryActionKind =
  | 'open-datasources'
  | 'open-related-file'
  | 'open-files'
  | 'retry-run'
  | 'copy-diagnostics'

export interface WorkflowRecoveryAction {
  kind: WorkflowRecoveryActionKind
  label: string
}

export interface WorkflowRecoveryState {
  title: string
  detail: string
  suggestion: string | null
  diagnostics: string
  actions: WorkflowRecoveryAction[]
}

interface BuildWorkflowRecoveryStateOptions {
  runPhase: WorkflowRunPhaseState | null
  runError: string | null
  error: string | null
  activeFilePath: string | null
  runOutput: string
}

const DATASOURCE_NODE_TYPES = new Set(['datasource.read', 'sql.execute'])
const FILE_REVIEW_NODE_TYPES = new Set([
  'python.code',
  'report.generate',
  'data.generate_dashboard',
  'video.generator',
])

function normalizeText(value: string | null | undefined) {
  if (!value) return null
  const normalized = value.trim()
  return normalized || null
}

function dedupeActions(actions: WorkflowRecoveryAction[]) {
  return actions.filter(
    (action, index, collection) =>
      collection.findIndex((candidate) => candidate.kind === action.kind) === index,
  )
}

function buildDiagnostics(
  runPhase: WorkflowRunPhaseState | null,
  detail: string,
  runError: string | null,
  error: string | null,
  activeFilePath: string | null,
  runOutput: string,
) {
  return [
    'Workflow recovery snapshot',
    runPhase?.label ? `Phase: ${runPhase.label}` : null,
    runPhase?.nodeId ? `Node: ${runPhase.nodeId}` : null,
    runPhase?.nodeType ? `Node type: ${runPhase.nodeType}` : null,
    activeFilePath ? `Related file: ${activeFilePath}` : null,
    `Detail: ${detail}`,
    runError ? `Run error: ${runError}` : null,
    error && error !== runError ? `Error: ${error}` : null,
    normalizeText(runOutput) ? `Run output:\n${runOutput}` : null,
  ]
    .filter((value): value is string => Boolean(value))
    .join('\n')
}

function shouldSuggestDataReview(nodeType: string | null, detail: string) {
  if (nodeType && DATASOURCE_NODE_TYPES.has(nodeType)) {
    return true
  }
  const detailText = detail.toLowerCase()
  return ['datasource', 'schema', 'table', 'connection', 'sql'].some((fragment) =>
    detailText.includes(fragment),
  )
}

export function buildWorkflowRecoveryState({
  runPhase,
  runError,
  error,
  activeFilePath,
  runOutput,
}: BuildWorkflowRecoveryStateOptions): WorkflowRecoveryState | null {
  const hasFailure =
    runPhase?.status === 'error' ||
    Boolean(normalizeText(runError)) ||
    Boolean(normalizeText(error))
  if (!hasFailure) {
    return null
  }

  const detail =
    normalizeText(runError) ??
    normalizeText(error) ??
    normalizeText(runPhase?.detail) ??
    'The latest workflow run stopped before completion.'
  const suggestion =
    normalizeText(runPhase?.suggestion) ?? 'Review the failing step, then retry the workflow.'
  const nodeType = runPhase?.nodeType ?? null
  const actions: WorkflowRecoveryAction[] = []

  if (shouldSuggestDataReview(nodeType, detail)) {
    actions.push({ kind: 'open-datasources', label: 'Review attached data' })
  }

  if (activeFilePath) {
    actions.push({ kind: 'open-related-file', label: 'Open related file' })
  } else if (nodeType && FILE_REVIEW_NODE_TYPES.has(nodeType)) {
    actions.push({ kind: 'open-files', label: 'Open files' })
  }

  actions.push({ kind: 'retry-run', label: 'Retry workflow' })
  actions.push({ kind: 'copy-diagnostics', label: 'Copy diagnostics' })

  return {
    title: normalizeText(runPhase?.label) ?? 'Workflow needs attention',
    detail,
    suggestion,
    diagnostics: buildDiagnostics(runPhase, detail, runError, error, activeFilePath, runOutput),
    actions: dedupeActions(actions),
  }
}
