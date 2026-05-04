import type { WorkflowArtifact, WorkflowArtifactPayload } from '../types'

type ArtifactKind = WorkflowArtifactPayload['kind']

const URL_PREVIEW_TYPES = new Set(['iframe', 'url', 'video'])

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function artifactPayload(artifact: WorkflowArtifactPayload) {
  return asRecord(artifact.payload)
}

export function getArtifactString(
  artifact: WorkflowArtifactPayload | null | undefined,
  key: string,
) {
  if (!artifact) return null
  const direct = artifact[key]
  if (typeof direct === 'string' && direct.trim()) return direct

  const payloadValue = artifactPayload(artifact)?.[key]
  if (typeof payloadValue === 'string' && payloadValue.trim()) return payloadValue

  return null
}

export function getArtifactKind(artifact: WorkflowArtifactPayload | null | undefined) {
  return typeof artifact?.kind === 'string' && artifact.kind.trim() ? artifact.kind : null
}

export function getArtifactNodeId(artifact: WorkflowArtifactPayload | null | undefined) {
  return getArtifactString(artifact, 'node_id')
}

export function getArtifactTaskId(artifact: WorkflowArtifactPayload | null | undefined) {
  return getArtifactString(artifact, 'task_id')
}

export function getArtifactError(artifact: WorkflowArtifactPayload | null | undefined) {
  return getArtifactString(artifact, 'error')
}

export function getArtifactStatus(artifact: WorkflowArtifactPayload | null | undefined) {
  if (!artifact) return 'pending'
  if (getArtifactError(artifact)) return 'failed'
  return artifact.status ?? 'ready'
}

export function getArtifactPreviewUrl(artifact: WorkflowArtifactPayload | null | undefined) {
  if (!artifact) return null

  const preview = asRecord(artifact.preview)
  const previewType = typeof preview?.type === 'string' ? preview.type : null
  const previewUrl = preview?.url
  if (
    typeof previewUrl === 'string' &&
    previewUrl.trim() &&
    (!previewType || URL_PREVIEW_TYPES.has(previewType))
  ) {
    return previewUrl
  }

  if (artifact.kind === 'dashboard') {
    return getArtifactString(artifact, 'dashboard_url')
  }
  if (artifact.kind === 'video') {
    return getArtifactString(artifact, 'video_url')
  }

  return null
}

export function getArtifactHtml(artifact: WorkflowArtifactPayload | null | undefined) {
  if (!artifact) return null
  const preview = asRecord(artifact.preview)
  const contentKey = typeof preview?.content_key === 'string' ? preview.content_key : null
  if (contentKey) {
    const content = getArtifactString(artifact, contentKey)
    if (content) return content
  }
  return getArtifactString(artifact, 'report_html')
}

export function getArtifactFileName(
  artifact: WorkflowArtifactPayload | null | undefined,
  role?: string,
) {
  if (!artifact) return null
  if (artifact.kind === 'report') {
    const reportFilename = getArtifactString(artifact, 'report_filename')
    if (reportFilename) return reportFilename
  }

  const files = Array.isArray(artifact.files) ? artifact.files : []
  const matchingFile = role
    ? files.find((file) => file.role === role)
    : files[0]
  if (typeof matchingFile?.name === 'string' && matchingFile.name.trim()) {
    return matchingFile.name
  }

  const path =
    getArtifactString(artifact, 'report_path') ||
    getArtifactString(artifact, 'file_path') ||
    getArtifactString(artifact, 'path')
  return path?.split('/').pop() || null
}

export function getArtifactSteps(artifact: WorkflowArtifactPayload | null | undefined) {
  if (!artifact) return []
  const direct = artifact.steps
  const payloadSteps = artifactPayload(artifact)?.steps
  const steps = Array.isArray(direct) ? direct : Array.isArray(payloadSteps) ? payloadSteps : []
  return steps.filter((item): item is string => typeof item === 'string')
}

export function latestArtifactByKind<T extends WorkflowArtifactPayload>(
  artifacts: T[] | null | undefined,
  kind: ArtifactKind,
) {
  return [...(artifacts ?? [])].reverse().find((artifact) => artifact.kind === kind) ?? null
}

export function latestWorkflowArtifactByKind(
  artifacts: WorkflowArtifact[] | null | undefined,
  kind: ArtifactKind,
) {
  return [...(artifacts ?? [])].reverse().find((artifact) => artifact.kind === kind) ?? null
}
