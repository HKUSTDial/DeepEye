import type { LocaleTranslate } from '../locale'
import {
  deriveReportProgressState,
  REPORT_PROGRESS_STAGE_ICONS,
  REPORT_PROGRESS_STAGE_KEYS,
  REPORT_PROGRESS_TOTAL_STEPS,
} from './reportProgress'
import { DASHBOARD_PROGRESS_STAGE_KEYS } from './dashboardProgress'
import {
  VIDEO_PROGRESS_STAGE_ICONS,
  VIDEO_PROGRESS_STAGE_KEYS,
  VIDEO_PROGRESS_STAGE_MESSAGE_KEYS,
} from './videoProgress'

export type ArtifactGenerationKind = 'report' | 'dashboard' | 'video'
export type ArtifactGenerationLifecycle = 'queued' | 'running' | 'warming' | 'ready' | 'failed'
export type ArtifactGenerationCardStatus = 'running' | 'waiting' | 'ready' | 'failed'
export type ArtifactGenerationStepStatus = 'done' | 'active' | 'warning' | 'pending'

export interface ArtifactGenerationMetric {
  label: string
  value: string
}

export interface ArtifactGenerationStep {
  id?: string
  label: string
  detail?: string
  icon?: string
  status: ArtifactGenerationStepStatus
}

export interface ArtifactGenerationCard {
  artifact: string
  title: string
  description: string
  variant: ArtifactGenerationKind
  signature?: string
  status: ArtifactGenerationCardStatus
  statusLabel: string
  percent: number
  currentLabel?: string
  metrics?: ArtifactGenerationMetric[]
  steps: ArtifactGenerationStep[]
  tone: string
}

export interface ArtifactGeneration {
  kind: ArtifactGenerationKind
  lifecycle: ArtifactGenerationLifecycle
  card: ArtifactGenerationCard
}

export interface ProgressLogEntryLike {
  message: string
}

const DASHBOARD_PROGRESS_STAGE_ICONS = ['🧭', '📊', '🧮', '🔗', '🧩', '🚀'] as const

function clampPercent(value: number) {
  if (Number.isNaN(value)) return 0
  return Math.min(100, Math.max(0, Math.round(value)))
}

function clampIndex(value: number, length: number) {
  return Math.min(Math.max(Math.trunc(value), 0), Math.max(length - 1, 0))
}

function genericStepDetail(status: ArtifactGenerationStepStatus, t: LocaleTranslate) {
  if (status === 'done') return t('common.completed')
  if (status === 'active') return t('common.running')
  if (status === 'warning') return t('common.needsAttention')
  return t('common.queued')
}

function reportStepDetail(status: ArtifactGenerationStepStatus, t: LocaleTranslate) {
  if (status === 'done') return t('report.stageDone')
  if (status === 'active') return t('report.stageActive')
  if (status === 'warning') return t('report.stageWarning')
  return t('report.stagePending')
}

function videoStepDetail(status: ArtifactGenerationStepStatus, t: LocaleTranslate) {
  if (status === 'done') return t('video.stepDone')
  if (status === 'active') return t('video.stepActive')
  if (status === 'warning') return t('video.stepWarning')
  return t('video.stepPending')
}

export function createReportGeneration({
  t,
  steps,
  isGenerating,
  isDone,
  error,
  percent,
}: {
  t: LocaleTranslate
  steps: string[]
  isGenerating: boolean
  isDone: boolean
  error?: string | null
  percent: number
}): ArtifactGeneration | null {
  if (!isDone && !isGenerating && steps.length === 0 && !error) return null

  const { stageStatuses, maxStage, progressedCount } = deriveReportProgressState(
    steps,
    isDone,
    REPORT_PROGRESS_TOTAL_STEPS,
  )
  const reportSteps = REPORT_PROGRESS_STAGE_KEYS.map((key, index) => ({
    id: key,
    label: t(key),
    detail: reportStepDetail(stageStatuses[index], t),
    icon: stageStatuses[index] === 'done' ? '✓' : REPORT_PROGRESS_STAGE_ICONS[index],
    status: stageStatuses[index],
  }))
  const isWaiting = isGenerating && steps.length === 0 && !error
  const lifecycle: ArtifactGenerationLifecycle = error
    ? 'failed'
    : isDone
      ? 'ready'
      : isWaiting
        ? 'queued'
        : 'running'
  const status: ArtifactGenerationCardStatus = error
    ? 'failed'
    : isDone
      ? 'ready'
      : isWaiting
        ? 'waiting'
        : 'running'
  const currentLabel =
    error ||
    (maxStage >= 0 && maxStage < reportSteps.length
      ? reportSteps[maxStage].label
      : isDone
        ? t('report.readyToReview')
        : t('report.preparingPipeline'))

  return {
    kind: 'report',
    lifecycle,
    card: {
      artifact: t('panel.report.title'),
      title: isDone ? t('report.readyToReview') : error ? t('report.failedTitle') : t('report.generatingTitle'),
      description: error ? error : t('report.generatingDescription'),
      variant: 'report',
      signature: t('report.signature'),
      status,
      statusLabel: error ? t('common.failed') : isDone ? t('common.ready') : isWaiting ? t('common.queued') : t('common.running'),
      percent: isDone ? 100 : clampPercent(percent),
      currentLabel,
      metrics: [
        { label: t('report.phasesMetric'), value: `${progressedCount}/${REPORT_PROGRESS_TOTAL_STEPS}` },
        { label: 'Output', value: t('report.outputMetric') },
      ],
      steps: reportSteps,
      tone: '#c2410c',
    },
  }
}

export function createDashboardGeneration({
  t,
  isGenerating,
  isWarming,
  isReady,
  stage,
  percent,
  logs,
  nodeId,
  healthCheckCount,
}: {
  t: LocaleTranslate
  isGenerating: boolean
  isWarming: boolean
  isReady: boolean
  stage: number
  percent: number
  logs: ProgressLogEntryLike[]
  nodeId?: string | null
  healthCheckCount: number
}): ArtifactGeneration | null {
  if (!isGenerating && !isWarming) return null

  if (isGenerating) {
    const stageIndex = clampIndex(stage, DASHBOARD_PROGRESS_STAGE_KEYS.length)
    const stageKey = DASHBOARD_PROGRESS_STAGE_KEYS[stageIndex] ?? DASHBOARD_PROGRESS_STAGE_KEYS[0]
    const steps = DASHBOARD_PROGRESS_STAGE_KEYS.map((key, index) => {
      const status: ArtifactGenerationStepStatus =
        index < stageIndex ? 'done' : index === stageIndex ? 'active' : 'pending'
      return {
        id: key,
        label: t(key),
        detail: genericStepDetail(status, t),
        icon: status === 'done' ? '✓' : DASHBOARD_PROGRESS_STAGE_ICONS[index],
        status,
      }
    })
    const currentLabel = logs[logs.length - 1]?.message || t(stageKey) || t('dashboard.preparingGeneration')

    return {
      kind: 'dashboard',
      lifecycle: 'running',
      card: {
        artifact: t('panel.dashboard.title'),
        title: t('dashboard.generatingTitle'),
        description: t('dashboard.generatingDescription'),
        variant: 'dashboard',
        signature: t('dashboard.generatingSignature'),
        status: 'running',
        statusLabel: t('common.running'),
        percent: clampPercent(Math.max(percent || 0, 14)),
        currentLabel,
        metrics: [
          { label: t('dashboard.metricStage'), value: `${Math.min(stageIndex + 1, steps.length)}/${steps.length}` },
          { label: t('dashboard.metricNode'), value: nodeId || t('dashboard.nodeFallback') },
        ],
        steps,
        tone: '#0f766e',
      },
    }
  }

  const steps: ArtifactGenerationStep[] = [
    {
      id: 'artifact',
      label: t('artifact.stepResolveArtifact'),
      icon: '🧩',
      status: 'done',
      detail: t('common.ready'),
    },
    {
      id: 'boot',
      label: t('artifact.stepWarmPreviewService'),
      icon: '🚀',
      status: isReady ? 'done' : healthCheckCount <= 1 ? 'active' : 'done',
      detail: isReady ? t('common.ready') : healthCheckCount <= 1 ? t('common.starting') : t('artifact.detailWarmed'),
    },
    {
      id: 'probe',
      label: t('artifact.stepRunHealthChecks'),
      icon: '🩺',
      status: isReady ? 'done' : healthCheckCount > 1 ? 'active' : 'pending',
      detail: isReady ? t('artifact.detailHealthy') : healthCheckCount > 1 ? t('common.checking') : t('common.queued'),
    },
    {
      id: 'mount',
      label: t('artifact.stepMountPreview'),
      icon: '📊',
      status: isReady ? 'done' : 'pending',
      detail: isReady ? t('artifact.detailVisible') : t('common.queued'),
    },
  ]

  return {
    kind: 'dashboard',
    lifecycle: isReady ? 'ready' : 'warming',
    card: {
      artifact: t('panel.dashboard.title'),
      title: t('dashboard.startingLiveTitle'),
      description: t('dashboard.startingLiveDescription'),
      variant: 'dashboard',
      signature: t('dashboard.startingLiveSignature'),
      status: healthCheckCount > 0 ? 'running' : 'waiting',
      statusLabel: healthCheckCount > 0 ? t('dashboard.connecting') : t('common.starting'),
      percent: isReady ? 100 : Math.min(28 + healthCheckCount * 16, 84),
      currentLabel: healthCheckCount > 1 ? t('dashboard.pollingPreview') : t('dashboard.allocatingPreview'),
      metrics: [
        { label: t('dashboard.metricNode'), value: nodeId || t('dashboard.nodeFallback') },
        { label: t('dashboard.metricChecks'), value: healthCheckCount > 0 ? String(healthCheckCount) : t('dashboard.pendingChecks') },
      ],
      steps,
      tone: '#0f766e',
    },
  }
}

export function createVideoGeneration({
  t,
  isRendering,
  isPreviewWarming,
  isPreviewReady,
  runFailed,
  step,
  percent,
  logs,
  taskId,
  previewCheckCount,
}: {
  t: LocaleTranslate
  isRendering: boolean
  isPreviewWarming: boolean
  isPreviewReady: boolean
  runFailed: boolean
  step: number
  percent: number
  logs: ProgressLogEntryLike[]
  taskId?: string | null
  previewCheckCount: number
}): ArtifactGeneration | null {
  if (isRendering || runFailed) {
    const stageIndex = clampIndex(step, VIDEO_PROGRESS_STAGE_KEYS.length)
    const steps = VIDEO_PROGRESS_STAGE_KEYS.map((key, index) => {
      const status: ArtifactGenerationStepStatus =
        runFailed && index === stageIndex
          ? 'warning'
          : index < stageIndex
            ? 'done'
            : index === stageIndex
              ? 'active'
              : 'pending'
      return {
        id: key,
        label: t(key),
        detail: videoStepDetail(status, t),
        icon: runFailed && index === stageIndex ? '⚠️' : VIDEO_PROGRESS_STAGE_ICONS[index],
        status,
      }
    })
    const latestLog = logs.length > 0 ? logs[logs.length - 1]?.message : null
    const stepMessageKey = VIDEO_PROGRESS_STAGE_MESSAGE_KEYS[stageIndex] ?? 'video.renderingDescription'
    const stepIcon = VIDEO_PROGRESS_STAGE_ICONS[stageIndex] ?? '🎬'

    return {
      kind: 'video',
      lifecycle: runFailed ? 'failed' : percent > 0 || logs.length > 0 ? 'running' : 'queued',
      card: {
        artifact: t('video.label'),
        title: runFailed ? t('video.generationFailedTitle') : t('video.renderingTitle'),
        description: runFailed ? t('video.generationFailedDescription') : t('video.renderingDescription'),
        variant: 'video',
        signature: t('video.signatureRender'),
        status: runFailed ? 'failed' : percent > 0 || logs.length > 0 ? 'running' : 'waiting',
        statusLabel: runFailed ? t('common.failed') : percent > 0 || logs.length > 0 ? t('video.rendering') : t('common.queued'),
        percent: clampPercent(percent),
        currentLabel: runFailed
          ? t('video.generationFailedDescription')
          : latestLog || `${stepIcon} ${t(stepMessageKey)}`,
        metrics: [
          { label: t('dashboard.metricStage'), value: `${Math.min(stageIndex + 1, steps.length)}/${steps.length}` },
          { label: 'Logs', value: String(logs.length) },
          ...(taskId ? [{ label: t('video.metricTask'), value: taskId }] : []),
        ],
        steps,
        tone: '#2563eb',
      },
    }
  }

  if (!isPreviewWarming) return null

  const steps: ArtifactGenerationStep[] = [
    { id: 'artifact', label: t('video.openPreview'), icon: '🔗', status: 'done', detail: t('common.ready') },
    {
      id: 'boot',
      label: t('video.overlayTitle'),
      icon: '🚀',
      status: isPreviewReady ? 'done' : previewCheckCount <= 1 ? 'active' : 'done',
      detail: isPreviewReady ? t('common.ready') : previewCheckCount <= 1 ? t('common.starting') : t('common.ready'),
    },
    {
      id: 'probe',
      label: t('artifact.stepRunHealthChecks'),
      icon: '🩺',
      status: isPreviewReady ? 'done' : previewCheckCount > 1 ? 'active' : 'pending',
      detail: isPreviewReady ? t('artifact.detailHealthy') : previewCheckCount > 1 ? t('common.checking') : t('common.queued'),
    },
    {
      id: 'mount',
      label: t('artifact.stepMountPreview'),
      icon: '🎞️',
      status: isPreviewReady ? 'done' : 'pending',
      detail: isPreviewReady ? t('artifact.detailVisible') : t('common.queued'),
    },
  ]

  return {
    kind: 'video',
    lifecycle: isPreviewReady ? 'ready' : 'warming',
    card: {
      artifact: t('video.label'),
      title: t('video.startingLiveTitle'),
      description: t('video.startingLiveDescription'),
      variant: 'video',
      signature: t('video.signaturePlayback'),
      status: previewCheckCount > 0 ? 'running' : 'waiting',
      statusLabel: previewCheckCount > 0 ? t('dashboard.connecting') : t('common.starting'),
      percent: isPreviewReady ? 100 : Math.min(34 + previewCheckCount * 14, 86),
      currentLabel: previewCheckCount > 1 ? t('video.waitingPreviewChecks') : t('video.allocatingPreview'),
      metrics: [
        ...(taskId ? [{ label: t('video.metricTask'), value: taskId }] : []),
        { label: t('video.metricChecks'), value: previewCheckCount > 0 ? String(previewCheckCount) : t('video.pending') },
      ],
      steps,
      tone: '#2563eb',
    },
  }
}
