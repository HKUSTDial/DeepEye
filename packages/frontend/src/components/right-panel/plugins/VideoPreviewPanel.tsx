import { useEffect, useMemo, useRef, useState } from 'react'
import { ExternalLink, Film, Loader2, PlayCircle, Sparkles, TriangleAlert } from 'lucide-react'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { config } from '../../../config'

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

const STEP_LABELS = [
  { icon: '📹', label: 'Generate config', index: 0 },
  { icon: '🎵', label: 'Audio & timeline', index: 1 },
  { icon: '💾', label: 'Save config', index: 2 },
  { icon: '🎬', label: 'Render components', index: 3 },
]

const STEP_MESSAGES: Record<number, string> = {
  0: '📹 Step 1/4: Generating video configuration...',
  1: '🎵 Step 2/4: Generating audio and aligning timeline...',
  2: '💾 Step 3/4: Saving configuration file...',
  3: '🎬 Step 4/4: Rendering video components...',
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

function getVideoStepClass(index: number, currentStep: number, failed: boolean) {
  if (failed && index === currentStep) return 'panel-step-pill panel-step-pill--warning'
  if (index < currentStep) return 'panel-step-pill panel-step-pill--done'
  if (index === currentStep) return 'panel-step-pill panel-step-pill--active'
  return 'panel-step-pill'
}

function getLogRowClass(type: ReturnType<typeof getLogEntryType>) {
  return type ? `panel-log-row panel-log-row--${type}` : 'panel-log-row'
}

export function VideoPreviewPanel({ taskId, sessionId }: VideoPreviewPanelProps) {
  const videoProgressLogsRef = useRef<HTMLDivElement | null>(null)
  const [pastedTaskId, setPastedTaskId] = useState('')
  const [manualTaskId, setManualTaskId] = useState<string | null>(null)

  const sessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )
  const runOutput = sessionState?.runOutput ?? ''
  const videoProgress = sessionState?.videoProgress ?? { visible: false, step: 0, percent: 0, logs: [] }
  const runStatus = (sessionState?.runStatus as string | null | undefined) ?? null
  const runError = sessionState?.runError ?? null
  const videoPreviewUrl = sessionState?.videoPreviewUrl ?? null
  const [isPreviewReady, setIsPreviewReady] = useState(false)
  const [isCheckingPreview, setIsCheckingPreview] = useState(false)
  const previewCheckIntervalRef = useRef<number | null>(null)

  const videoUrlsFromNode = useMemo(() => {
    if (!sessionState?.nodeStatus) return []
    const urls: { nodeId: string; url: string }[] = []
    Object.entries(sessionState.nodeStatus).forEach(([nodeId, statusInfo]) => {
      const info = statusInfo as { outputs?: Record<string, unknown> }
      const value = info.outputs?.video_url
      if (typeof value === 'string' && value) {
        urls.push({ nodeId, url: value })
      }
    })
    return urls
  }, [sessionState?.nodeStatus])

  const latestVideoUrlFromNode = videoUrlsFromNode[videoUrlsFromNode.length - 1]?.url
  const fullPreviewUrlFromNode = useMemo(() => {
    if (!latestVideoUrlFromNode) return ''
    if (latestVideoUrlFromNode.startsWith('http')) return latestVideoUrlFromNode
    const base = config.api.baseUrl.replace('/api/v1', '')
    return `${base}${latestVideoUrlFromNode.startsWith('/') ? '' : '/'}${latestVideoUrlFromNode}`
  }, [latestVideoUrlFromNode])

  const pastedNormalized = normalizePastedTaskId(pastedTaskId)
  const displayTaskId = taskId || extractTaskIdFromOutput(runOutput) || manualTaskId || undefined

  const constructedPreviewUrl =
    displayTaskId && typeof window !== 'undefined'
      ? `${window.location.origin}/video-previews/deepeye-video-${displayTaskId}/`
      : null

  const effectivePreviewUrl = videoPreviewUrl || fullPreviewUrlFromNode || constructedPreviewUrl || null
  const effectivePreviewUrlWithSession = useMemo(() => {
    if (!effectivePreviewUrl) return null
    let next = effectivePreviewUrl
    next = withQueryParam(next, 'session_id', sessionId ?? undefined)
    return next
  }, [effectivePreviewUrl, sessionId])

  useEffect(() => {
    if (!effectivePreviewUrlWithSession) {
      setIsPreviewReady(false)
      return
    }
    setIsPreviewReady(false)

    const checkReady = async () => {
      setIsCheckingPreview(true)
      try {
        const response = await fetch(effectivePreviewUrlWithSession, { method: 'GET', cache: 'no-store' })
        const fromPreviewRoute = response.headers.get('X-Video-Preview') === '1'
        if (response.ok && fromPreviewRoute) {
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
      window.clearTimeout(timeoutId)
      if (previewCheckIntervalRef.current) {
        window.clearInterval(previewCheckIntervalRef.current)
        previewCheckIntervalRef.current = null
      }
    }
  }, [effectivePreviewUrlWithSession])

  useEffect(() => {
    const prefix = '[VideoPreview]'
    if (effectivePreviewUrlWithSession) {
      console.info(prefix, 'Preview URL (will poll until ready):', {
        source: videoPreviewUrl ? 'event' : fullPreviewUrlFromNode ? 'node output' : 'constructed',
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
  }, [effectivePreviewUrlWithSession, videoPreviewUrl, fullPreviewUrlFromNode, sessionId, taskId, pastedNormalized, pastedTaskId, runOutput])

  useEffect(() => {
    if (videoProgress.visible && videoProgress.logs.length > 0 && videoProgressLogsRef.current) {
      videoProgressLogsRef.current.scrollTop = videoProgressLogsRef.current.scrollHeight
    }
  }, [videoProgress.visible, videoProgress.logs.length])

  const runInProgress = runStatus === 'running' || runStatus === null
  const runFailed = runStatus === 'failed'

  if (effectivePreviewUrlWithSession) {
    return (
      <div className="panel-view">
        <div className="panel-toolbar">
          <div className="panel-toolbar-main">
            <div className="panel-toolbar-icon">
              <Film />
            </div>
            <div className="panel-toolbar-copy">
              <div className="panel-toolbar-label">Video</div>
              <div className="panel-toolbar-title">Live preview</div>
              {(!isPreviewReady || isCheckingPreview) && (
                <div className="panel-toolbar-meta">
                  <span className="panel-toolbar-status">
                    <Loader2 className="animate-spin" />
                    Waiting for preview...
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
                Open
              </a>
            </div>
          )}
        </div>

        <div className="panel-frame">
          {!isPreviewReady ? (
            <div className="panel-frame-overlay">
              <Loader2 className="h-7 w-7 animate-spin text-[var(--accent)]" />
              <p className="panel-frame-overlay-title">Starting preview container</p>
              <p className="panel-frame-overlay-subtitle">
                This usually takes 15 to 30 seconds. The panel will switch to the rendered video as soon as the service responds.
              </p>
              <p className="panel-helper-text">
                If it stays blank for more than a minute, build the preview image first: <code>docker build -f docker/Dockerfile.video-preview -t deepeye-video-preview:latest .</code>
              </p>
            </div>
          ) : (
            <iframe
              src={effectivePreviewUrlWithSession}
              className="h-full w-full border-none"
              title="Video Preview"
              allow="autoplay"
            />
          )}
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
              <div className="panel-toolbar-label">Video</div>
              <div className="panel-toolbar-title">Generation status</div>
              <div className="panel-toolbar-meta">
                <span className={`panel-toolbar-status ${runFailed ? 'panel-toolbar-error' : ''}`}>
                  {runFailed ? 'Failed' : `${videoProgress.percent}% complete`}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="panel-surface">
          <div className="panel-stack">
            <div className="panel-progress-card">
              <div className="panel-progress-header">
                <div className="panel-progress-copy">
                  <div className="panel-toolbar-label">Video</div>
                  <div className="panel-progress-title">
                    {runFailed ? 'Video generation failed' : 'Rendering data video'}
                  </div>
                  <div className="panel-progress-description">
                    {runFailed
                      ? 'The workflow stopped before the preview could open. Inspect the latest logs below.'
                      : 'DeepEye is generating the video config, timeline, and render artifacts.'}
                  </div>
                </div>
                <div className="panel-progress-percent tabular-nums">
                  {runFailed ? 'Failed' : `${videoProgress.percent}%`}
                </div>
              </div>

              {!runFailed && (
                <div className="panel-progress-bar">
                  <div className="panel-progress-fill" style={{ width: `${videoProgress.percent}%` }} />
                </div>
              )}

              <div className="panel-step-rail">
                {STEP_LABELS.map((step) => (
                  <div key={step.index} className={getVideoStepClass(step.index, videoProgress.step, runFailed)}>
                    <span className="panel-step-pill-icon">{step.icon}</span>
                    <span className="panel-step-pill-label">{step.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {runError ? (
              <div className="panel-state-card panel-state-card--error">
                <div className="panel-state-icon">
                  <TriangleAlert size={16} />
                </div>
                <div className="panel-state-copy">
                  <div className="panel-state-title">Render error</div>
                  <div className="panel-state-body">{runError}</div>
                </div>
              </div>
            ) : null}

            <div>
              <div className="panel-inline-header">
                <div className="panel-inline-note">Live render logs</div>
              </div>
              <div ref={videoProgressLogsRef} className="panel-log-console">
                {videoProgress.logs.length === 0 ? (
                  <div className="panel-log-empty">
                    {(videoProgress.step > 0 || videoProgress.percent > 0) && STEP_MESSAGES[videoProgress.step]
                      ? `${STEP_MESSAGES[videoProgress.step]} Live log lines will appear here when the backend emits progress.`
                      : 'Progress logs will appear here while the render is running.'}
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
      <div className="right-panel-empty-kicker">Video</div>
      <Film className="right-panel-empty-icon" />
      <h3 className="right-panel-empty-title">No video preview yet</h3>
      <p className="right-panel-empty-subtitle">
        DeepEye will open the rendered video here automatically. If you already have a task ID, you can open the preview manually.
      </p>

      <div className="panel-form-card">
        <div className="panel-form-row">
          <input
            type="text"
            value={pastedTaskId}
            onChange={(event) => setPastedTaskId(event.target.value)}
            placeholder="e.g. 20260306_121530"
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
            Open preview
          </button>
        </div>
        <p className="panel-helper-text">
          Paste the task ID from chat or workflow output. Supported format: <code>YYYYMMDD_HHMMSS</code>.
        </p>
      </div>
    </div>
  )
}
