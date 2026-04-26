import { useEffect, useMemo, useRef, useState } from 'react'
import { ExternalLink, Film, Loader2, PlayCircle, Sparkles, TriangleAlert } from 'lucide-react'
import {
  ArtifactProgressCard,
  type ArtifactProgressStep,
  type ArtifactProgressStepStatus,
} from '../ArtifactProgressCard'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { useLocale } from '../../../locale'
import { deferEffectWork } from '../../../utils/effects'

interface VideoPreviewPanelProps {
  taskId?: string
  sessionId?: string | null
}

const TASK_ID_REGEX = /^\d{8}_\d{6}$/

function normalizePastedTaskId(raw: string): string | undefined {
  const trimmed = raw.trim()
  if (!trimmed) return undefined
  if (TASK_ID_REGEX.test(trimmed)) return trimmed
  const extracted = trimmed.match(/(\d{8}_\d{6})/)
  return extracted ? extracted[1] : undefined
}

function extractTaskIdFromOutput(runOutput: string): string | undefined {
  if (!runOutput || typeof runOutput !== 'string') return undefined
  const taskIdLabelMatch = runOutput.match(/Task ID:\s*(\d{8}_\d{6})/i)
  if (taskIdLabelMatch) return taskIdLabelMatch[1]
  try {
    const data = JSON.parse(runOutput)
    if (data && typeof data === 'object') {
      for (const key of Object.keys(data)) {
        const node = data[key]
        if (node && typeof node === 'object' && typeof node.task_id === 'string') return node.task_id
        if (node && typeof node === 'object' && node.video_info?.task_id) return node.video_info.task_id
      }
    }
  } catch {
    // Not JSON. Fall back to text extraction.
  }
  const taskIdMatch = runOutput.match(/(\d{8}_\d{6})/)
  return taskIdMatch ? taskIdMatch[1] : undefined
}

const PREVIEW_IFRAME_SANDBOX = 'allow-same-origin allow-scripts'

function getVideoStepStatus(index: number, currentStep: number, failed: boolean): ArtifactProgressStepStatus {
  if (failed && index === currentStep) return 'warning'
  if (index < currentStep) return 'done'
  if (index === currentStep) return 'active'
  return 'pending'
}

function getStepDetail(status: ArtifactProgressStepStatus, t: (key: string) => string) {
  switch (status) {
    case 'done':
      return t('video.stepDone')
    case 'active':
      return t('video.stepActive')
    case 'warning':
      return t('video.stepWarning')
    default:
      return t('video.stepPending')
  }
}

function getLogEntryType(message: string): 'success' | 'warn' | 'error' | 'info' | null {
  const text = message.trim()
  if (text.includes('✅') || text.includes('✓')) return 'success'
  if (text.includes('⚠️') || text.includes('Warning')) return 'warn'
  if (text.includes('❌') || text.includes('Error') || text.includes('Failed')) return 'error'
  if (text.includes('📊') || text.includes('Step') || /^\s*\[?\d+\/\d+\]/.test(text)) return 'info'
  return null
}

function withQueryParam(url: string, key: string, value?: string | null): string {
  if (!value) return url
  try {
    const parsed = new URL(url, typeof window !== 'undefined' ? window.location.origin : 'http://localhost')
    parsed.searchParams.set(key, value)
    return /^https?:\/\//i.test(url) ? parsed.toString() : `${parsed.pathname}${parsed.search}${parsed.hash}`
  } catch {
    const separator = url.includes('?') ? '&' : '?'
    return `${url}${separator}${encodeURIComponent(key)}=${encodeURIComponent(value)}`
  }
}

function getLogRowClass(type: ReturnType<typeof getLogEntryType>) {
  return type ? `panel-log-row panel-log-row--${type}` : 'panel-log-row'
}

export function VideoPreviewPanel({ taskId, sessionId }: VideoPreviewPanelProps) {
  const { t } = useLocale()
  const videoProgressLogsRef = useRef<HTMLDivElement | null>(null)
  const [pastedTaskId, setPastedTaskId] = useState('')
  const [manualTaskId, setManualTaskId] = useState<string | null>(null)

  const sessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )
  const STEP_LABELS = [
    { icon: '📹', label: t('video.step1'), index: 0 },
    { icon: '🎵', label: t('video.step2'), index: 1 },
    { icon: '💾', label: t('video.step3'), index: 2 },
    { icon: '🎬', label: t('video.step4'), index: 3 },
  ]
  const STEP_MESSAGES: Record<number, string> = {
    0: `📹 ${t('video.stepMessage1')}`,
    1: `🎵 ${t('video.stepMessage2')}`,
    2: `💾 ${t('video.stepMessage3')}`,
    3: `🎬 ${t('video.stepMessage4')}`,
  }
  const latestVideoArtifact = useMemo(
    () =>
      [...(sessionState?.artifacts ?? [])]
        .reverse()
        .find((artifact) => artifact.kind === 'video'),
    [sessionState?.artifacts],
  )
  const runOutput = sessionState?.runOutput ?? ''
  const videoProgress = sessionState?.videoProgress ?? { visible: false, step: 0, percent: 0, logs: [] }
  const runStatus = (sessionState?.runStatus as string | null | undefined) ?? null
  const runError = sessionState?.runError ?? null
  const videoPreviewUrl = sessionState?.videoPreviewUrl ?? null
  const [isPreviewReady, setIsPreviewReady] = useState(false)
  const [isCheckingPreview, setIsCheckingPreview] = useState(false)
  const [previewCheckCount, setPreviewCheckCount] = useState(0)
  const previewCheckIntervalRef = useRef<number | null>(null)

  const previewDeclaredReady = Boolean(videoPreviewUrl)

  const pastedNormalized = normalizePastedTaskId(pastedTaskId)
  const artifactTaskId =
    latestVideoArtifact && typeof latestVideoArtifact.task_id === 'string'
      ? latestVideoArtifact.task_id
      : undefined
  const displayTaskId =
    taskId || artifactTaskId || extractTaskIdFromOutput(runOutput) || manualTaskId || undefined

  const constructedPreviewUrl =
    displayTaskId && typeof window !== 'undefined'
      ? `${window.location.origin}/video-previews/deepeye-video-${displayTaskId}/`
      : null

  const effectivePreviewUrl = videoPreviewUrl || constructedPreviewUrl || null
  const effectivePreviewUrlWithSession = useMemo(() => {
    if (!effectivePreviewUrl) return null
    let next = effectivePreviewUrl
    next = withQueryParam(next, 'session_id', sessionId ?? undefined)
    return next
  }, [effectivePreviewUrl, sessionId])

  useEffect(() => {
    if (!effectivePreviewUrlWithSession) {
      return deferEffectWork(() => {
        setIsPreviewReady(false)
        setPreviewCheckCount(0)
      })
    }

    if (previewDeclaredReady) {
      return deferEffectWork(() => {
        setIsPreviewReady(true)
        setPreviewCheckCount(0)
        if (previewCheckIntervalRef.current) {
          window.clearInterval(previewCheckIntervalRef.current)
          previewCheckIntervalRef.current = null
        }
      })
    }

    const resetCleanup = deferEffectWork(() => {
      setIsPreviewReady(false)
      setPreviewCheckCount(0)
    })

    const checkReady = async () => {
      setIsCheckingPreview(true)
      setPreviewCheckCount((count) => count + 1)
      try {
        const response = await fetch(effectivePreviewUrlWithSession, { method: 'HEAD', cache: 'no-store' })
        const fromPreviewRoute = response.headers.get('X-Video-Preview') === '1'
        const contentType = response.headers.get('content-type') ?? ''
        const looksLikePreviewDocument = contentType.includes('text/html')
        if (response.ok && (fromPreviewRoute || looksLikePreviewDocument)) {
          setIsPreviewReady(true)
          if (previewCheckIntervalRef.current) {
            window.clearInterval(previewCheckIntervalRef.current)
            previewCheckIntervalRef.current = null
          }
        }
      } catch {
        // Keep polling while the preview container starts.
      } finally {
        setIsCheckingPreview(false)
      }
    }

    const timeoutId = window.setTimeout(() => {
      checkReady()
      previewCheckIntervalRef.current = window.setInterval(checkReady, 2000)
    }, 3000)

    return () => {
      resetCleanup()
      window.clearTimeout(timeoutId)
      if (previewCheckIntervalRef.current) {
        window.clearInterval(previewCheckIntervalRef.current)
        previewCheckIntervalRef.current = null
      }
    }
  }, [effectivePreviewUrlWithSession, previewDeclaredReady])

  useEffect(() => {
    const prefix = '[VideoPreview]'
    if (effectivePreviewUrlWithSession) {
      console.info(prefix, 'Preview URL (will poll until ready):', {
        source: videoPreviewUrl ? 'event' : 'constructed',
        url: effectivePreviewUrlWithSession,
      })
      return
    }
    if (sessionId != null || (runOutput?.length ?? 0) > 0) {
      console.info(prefix, 'No preview URL (paste Task ID or wait for event):', {
        sessionId: sessionId ?? null,
        taskIdFromProps: taskId ?? null,
        extractedFromRunOutput: extractTaskIdFromOutput(runOutput) ?? null,
        pastedTaskId: pastedNormalized ?? (pastedTaskId.trim() || null),
        runOutputLength: runOutput?.length ?? 0,
      })
    }
  }, [effectivePreviewUrlWithSession, videoPreviewUrl, sessionId, taskId, pastedNormalized, pastedTaskId, runOutput])

  useEffect(() => {
    if (videoProgress.visible && videoProgress.logs.length > 0 && videoProgressLogsRef.current) {
      videoProgressLogsRef.current.scrollTop = videoProgressLogsRef.current.scrollHeight
    }
  }, [videoProgress.visible, videoProgress.logs.length])

  const runInProgress = runStatus === 'running' || runStatus === null
  const runFailed = runStatus === 'failed'
  const generationStepNumber = Math.min(videoProgress.step + 1, STEP_LABELS.length)
  const latestVideoLog = videoProgress.logs.length > 0 ? videoProgress.logs[videoProgress.logs.length - 1]?.message : null
  const videoProgressSteps: ArtifactProgressStep[] = STEP_LABELS.map((step) => {
    const status = getVideoStepStatus(step.index, videoProgress.step, runFailed)
    return {
      id: `${step.index}`,
      label: step.label,
      detail: getStepDetail(status, t),
      icon: runFailed && step.index === videoProgress.step ? '⚠️' : step.icon,
      status,
    }
  })
  const previewWarmupPercent = isPreviewReady ? 100 : Math.min(34 + previewCheckCount * 14, 86)
  const previewWarmupSteps = [
    { id: 'artifact', label: t('video.openPreview'), icon: '🔗', status: 'done' as const, detail: t('common.ready') },
    {
      id: 'boot',
      label: t('video.overlayTitle'),
      icon: '🚀',
      status: isPreviewReady ? 'done' as const : previewCheckCount <= 1 ? 'active' as const : 'done' as const,
      detail: isPreviewReady ? t('common.ready') : previewCheckCount <= 1 ? t('common.starting') : t('common.ready'),
    },
    {
      id: 'probe',
      label: t('video.metricChecks'),
      icon: '🩺',
      status: isPreviewReady ? 'done' as const : previewCheckCount > 1 ? 'active' as const : 'pending' as const,
      detail: isPreviewReady ? t('common.ready') : previewCheckCount > 1 ? t('common.checking') : t('common.queued'),
    },
    {
      id: 'mount',
      label: t('video.livePreview'),
      icon: '🖥️',
      status: isPreviewReady ? 'done' as const : 'pending' as const,
      detail: isPreviewReady ? t('common.ready') : t('common.queued'),
    },
  ]

  if (effectivePreviewUrlWithSession) {
    return (
      <div className="panel-view">
        <div className="panel-toolbar">
          <div className="panel-toolbar-main">
            <div className="panel-toolbar-icon">
              <Film />
            </div>
            <div className="panel-toolbar-copy">
              <div className="panel-toolbar-label">{t('video.label')}</div>
              <div className="panel-toolbar-title">{t('video.livePreview')}</div>
              {(!isPreviewReady || isCheckingPreview) && (
                <div className="panel-toolbar-meta">
                  <span className="panel-toolbar-status">
                    <Loader2 className="animate-spin" />
                    {t('video.waitingPreview')}
                  </span>
                </div>
              )}
            </div>
          </div>

          {isPreviewReady && (
            <div className="panel-toolbar-actions">
              <a
                href={effectivePreviewUrlWithSession}
                target="_blank"
                rel="noopener noreferrer"
                className="panel-toolbar-link"
              >
                <ExternalLink />
                {t('app.open')}
              </a>
            </div>
          )}
        </div>

        {!isPreviewReady ? (
          <div className="artifact-progress-shell">
            <ArtifactProgressCard
              artifact={t('video.label')}
              title={t('video.startingLiveTitle')}
              description={t('video.startingLiveDescription')}
              icon={<Film size={18} />}
              variant="video"
              signature={t('video.signaturePlayback')}
              status={previewCheckCount > 0 ? 'running' : 'waiting'}
              statusLabel={previewCheckCount > 0 ? t('dashboard.connecting') : t('common.starting')}
              percent={previewWarmupPercent}
              currentLabel={
                previewCheckCount > 1
                  ? t('video.waitingPreviewChecks')
                  : t('video.allocatingPreview')
              }
              metrics={[
                ...(displayTaskId ? [{ label: t('video.metricTask'), value: displayTaskId }] : []),
                { label: t('video.metricChecks'), value: previewCheckCount > 0 ? String(previewCheckCount) : t('video.pending') },
              ]}
              steps={previewWarmupSteps}
              tone="#2563eb"
            />
          </div>
        ) : null}

        <div className="panel-frame">
          {isPreviewReady ? (
            <iframe
              key={effectivePreviewUrlWithSession}
              src={effectivePreviewUrlWithSession}
              className="h-full w-full border-none"
              title={t('video.iframeTitle')}
              allow="autoplay"
              sandbox={PREVIEW_IFRAME_SANDBOX}
            />
          ) : null}
          {!isPreviewReady ? (
            <div className="panel-frame-overlay">
              <Loader2 className="h-7 w-7 animate-spin text-[var(--accent)]" />
              <p className="panel-frame-overlay-title">{t('video.overlayTitle')}</p>
              <p className="panel-frame-overlay-subtitle">
                {t('video.overlaySubtitle')}
              </p>
              <p className="panel-helper-text">
                {t('video.overlayHelper')} <code>docker build -f docker/Dockerfile.video-preview -t deepeye-video-preview:latest .</code>
              </p>
            </div>
          ) : null}
        </div>
      </div>
    )
  }

  if (sessionId && videoProgress.visible && (runInProgress || runFailed)) {
    return (
      <div className="panel-view">
        <div className="panel-toolbar">
          <div className="panel-toolbar-main">
            <div className="panel-toolbar-icon">
              {runFailed ? <TriangleAlert /> : <PlayCircle />}
            </div>
            <div className="panel-toolbar-copy">
              <div className="panel-toolbar-label">{t('video.label')}</div>
              <div className="panel-toolbar-title">{t('video.generationStatusTitle')}</div>
              <div className="panel-toolbar-meta">
                <span className={`panel-toolbar-status ${runFailed ? 'panel-toolbar-error' : ''}`}>
                  {runFailed ? t('common.failed') : t('video.percentComplete', { count: videoProgress.percent })}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="panel-surface">
          <div className="panel-stack">
            <ArtifactProgressCard
              artifact={t('video.label')}
              title={runFailed ? t('video.generationFailedTitle') : t('video.renderingTitle')}
              description={
                runFailed
                  ? t('video.generationFailedDescription')
                  : t('video.renderingDescription')
              }
              icon={runFailed ? <TriangleAlert size={18} /> : <PlayCircle size={18} />}
              variant="video"
              signature={t('video.signatureRender')}
              status={runFailed ? 'failed' : videoProgress.percent > 0 || videoProgress.logs.length > 0 ? 'running' : 'waiting'}
              statusLabel={runFailed ? t('common.failed') : videoProgress.percent > 0 || videoProgress.logs.length > 0 ? t('video.rendering') : t('common.queued')}
              percent={videoProgress.percent}
              currentLabel={
                runFailed
                  ? t('video.generationFailedDescription')
                  : latestVideoLog || STEP_MESSAGES[videoProgress.step] || t('video.renderingDescription')
              }
              metrics={[
                { label: t('dashboard.metricStage'), value: `${generationStepNumber}/4` },
                { label: 'Logs', value: String(videoProgress.logs.length) },
                ...(displayTaskId ? [{ label: t('video.metricTask'), value: displayTaskId }] : []),
              ]}
              steps={videoProgressSteps}
              tone="#2563eb"
            />

            {runError ? (
              <div className="panel-state-card panel-state-card--error">
                <div className="panel-state-icon">
                  <TriangleAlert size={16} />
                </div>
                <div className="panel-state-copy">
                  <div className="panel-state-title">{t('video.renderError')}</div>
                  <div className="panel-state-body">{runError}</div>
                </div>
              </div>
            ) : null}

            <div>
              <div className="panel-inline-header">
                <div className="panel-inline-note">{t('video.liveLogs')}</div>
              </div>
              <div ref={videoProgressLogsRef} className="panel-log-console">
                {videoProgress.logs.length === 0 ? (
                  <div className="panel-log-empty">
                    {(videoProgress.step > 0 || videoProgress.percent > 0) && STEP_MESSAGES[videoProgress.step]
                      ? t('video.logFallbackActive', { message: STEP_MESSAGES[videoProgress.step] })
                      : t('video.logFallbackIdle')}
                  </div>
                ) : (
                  videoProgress.logs.slice(-50).map((log) => {
                    const type = getLogEntryType(log.message)
                    return (
                      <div key={log.id} className={getLogRowClass(type)}>
                        <span className="panel-log-time">{log.time}</span>
                        <span className="panel-log-message">{log.message}</span>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="right-panel-empty">
      <div className="right-panel-empty-kicker">{t('video.label')}</div>
      <Film className="right-panel-empty-icon" />
      <h3 className="right-panel-empty-title">{t('video.emptyTitle')}</h3>
      <p className="right-panel-empty-subtitle">
        {t('video.emptySubtitle')}
      </p>

      <div className="panel-form-card">
        <div className="panel-form-row">
          <input
            type="text"
            value={pastedTaskId}
            onChange={(event) => setPastedTaskId(event.target.value)}
            placeholder={t('video.placeholderTaskId')}
            className="panel-input panel-input--mono"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && pastedNormalized) {
                setManualTaskId(pastedNormalized)
              }
            }}
          />
          <button
            type="button"
            onClick={() => pastedNormalized && setManualTaskId(pastedNormalized)}
            disabled={!pastedNormalized}
            className="panel-toolbar-btn panel-toolbar-btn--primary"
          >
            <Sparkles />
            {t('video.openPreview')}
          </button>
        </div>
        <p className="panel-helper-text">
          {t('video.taskIdHelper')} <code>YYYYMMDD_HHMMSS</code>.
        </p>
      </div>
    </div>
  )
}
