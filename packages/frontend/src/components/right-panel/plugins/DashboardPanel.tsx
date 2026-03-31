import { useMemo, useState, useEffect, useRef } from 'react'
import { LayoutDashboard, ExternalLink, RefreshCw, Loader2 } from 'lucide-react'
import { ArtifactProgressCard } from '../ArtifactProgressCard'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { config } from '../../../config'
import { DASHBOARD_PROGRESS_STAGES } from '../../../utils/dashboardProgress'

function extractDashboardNodeIds(definition: unknown): string[] {
  if (!definition || typeof definition !== 'object') return []
  const record = definition as Record<string, unknown>
  const root = record.root && typeof record.root === 'object'
    ? (record.root as Record<string, unknown>)
    : record
  const nodes = root.nodes && typeof root.nodes === 'object'
    ? (root.nodes as Record<string, { id?: string; type?: string }>)
    : {}
  return Object.values(nodes)
    .filter((node) => node?.type === 'data.generate_dashboard' && typeof node.id === 'string')
    .map((node) => node.id as string)
}

const PREVIEW_IFRAME_SANDBOX = 'allow-same-origin allow-scripts'

export function DashboardPanel({
  sessionId,
}: {
  sessionId: string | null
}) {
  const [localRefreshKey, setLocalRefreshKey] = useState(0)
  const [previewState, setPreviewState] = useState({
    activeToken: '',
    readyToken: '',
    healthCheckCount: 0,
  })
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const checkIntervalRef = useRef<number | null>(null)

  const sessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )
  const dashboardProgress = sessionState?.dashboardProgress ?? {
    visible: false,
    stage: 0,
    percent: 0,
    logs: [],
  }
  const dashboardNodeIds = useMemo(
    () => extractDashboardNodeIds(sessionState?.definition),
    [sessionState?.definition],
  )

  const dashboardRefreshKey = sessionState?.dashboardRefreshKey || 0
  const refreshKey = useMemo(() => localRefreshKey + dashboardRefreshKey, [localRefreshKey, dashboardRefreshKey])

  const dashboardUrls = useMemo(() => {
    if (!sessionState?.artifacts) return []

    const urls: { nodeId: string; url: string }[] = []
    sessionState.artifacts.forEach((artifact) => {
      if (artifact.kind === 'dashboard' && typeof artifact.dashboard_url === 'string') {
        urls.push({
          nodeId: typeof artifact.node_id === 'string' ? artifact.node_id : 'dashboard',
          url: artifact.dashboard_url,
        })
      }
    })
    return urls
  }, [sessionState])

  const latestDashboard = dashboardUrls[dashboardUrls.length - 1]
  const isDashboardGenerating =
    !latestDashboard &&
    (
      dashboardProgress.visible ||
      dashboardNodeIds.some((nodeId) => sessionState?.nodeStatus?.[nodeId]?.status === 'running') ||
      (sessionState?.runStatus === 'running' && dashboardNodeIds.length > 0)
    )
  const generationStageIndex = Math.min(
    Math.max(dashboardProgress.stage ?? 0, 0),
    DASHBOARD_PROGRESS_STAGES.length - 1,
  )
  const generationCurrentLabel =
    dashboardProgress.logs[dashboardProgress.logs.length - 1]?.message ||
    DASHBOARD_PROGRESS_STAGES[generationStageIndex] ||
    'Preparing dashboard generation'
  const generationPercent = Math.max(
    dashboardProgress.percent || 0,
    isDashboardGenerating ? 14 : 0,
  )
  const generationSteps = DASHBOARD_PROGRESS_STAGES.map((label, index) => {
    const status =
      index < generationStageIndex
        ? 'done'
        : index === generationStageIndex
          ? 'active'
          : 'pending'
    return {
      id: label,
      label,
      detail: status === 'done' ? 'Completed' : status === 'active' ? 'Running' : 'Queued',
      icon: status === 'done' ? '✓' : ['🧭', '📊', '🧮', '🔗', '🧩', '🚀'][index] || '•',
      status,
    } as const
  })

  const fullDashboardUrl = useMemo(() => {
    if (!latestDashboard?.url) return ''
    if (latestDashboard.url.startsWith('http')) return latestDashboard.url

    const base = config.api.baseUrl.replace('/api/v1', '')
    return `${base}${latestDashboard.url.startsWith('/') ? '' : '/'}${latestDashboard.url}`
  }, [latestDashboard?.url])
  const previewToken = fullDashboardUrl ? `${fullDashboardUrl}::${refreshKey}` : ''
  const isReady = !!previewToken && previewState.readyToken === previewToken
  const healthCheckCount = previewState.activeToken === previewToken ? previewState.healthCheckCount : 0

  useEffect(() => {
    if (!previewToken || !fullDashboardUrl) {
      return
    }
    let cancelled = false
    let firstCheckTimer: number | null = null

    const checkReady = async () => {
      setPreviewState((prev) => ({
        activeToken: previewToken,
        readyToken: prev.readyToken === previewToken ? prev.readyToken : '',
        healthCheckCount: prev.activeToken === previewToken ? prev.healthCheckCount + 1 : 1,
      }))
      try {
        const res = await fetch(fullDashboardUrl, { method: 'HEAD', cache: 'no-store' })
        if (!cancelled && res.ok) {
          setPreviewState((prev) => ({
            activeToken: previewToken,
            readyToken: previewToken,
            healthCheckCount: prev.activeToken === previewToken ? prev.healthCheckCount : 1,
          }))
          if (checkIntervalRef.current) {
            window.clearInterval(checkIntervalRef.current)
            checkIntervalRef.current = null
          }
        }
      } catch {
        // Ignore errors while the preview service is still booting.
      }
    }

    firstCheckTimer = window.setTimeout(() => {
      void checkReady()
    }, 0)
    checkIntervalRef.current = window.setInterval(() => {
      void checkReady()
    }, 2000)

    return () => {
      cancelled = true
      if (firstCheckTimer) {
        window.clearTimeout(firstCheckTimer)
      }
      if (checkIntervalRef.current) {
        window.clearInterval(checkIntervalRef.current)
        checkIntervalRef.current = null
      }
    }
  }, [previewToken, fullDashboardUrl])

  useEffect(() => {
    if (!containerRef.current) return

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        const targetWidth = 1280
        const nextScale = Math.min(width / targetWidth, 1)
        setScale(nextScale)
      }
    })

    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  const dashboardWarmupPercent = isReady ? 100 : Math.min(28 + healthCheckCount * 16, 84)
  const dashboardWarmupSteps = [
    { id: 'artifact', label: 'Resolve dashboard artifact', icon: '🧩', status: 'done' as const, detail: 'Ready' },
    {
      id: 'boot',
      label: 'Warm preview service',
      icon: '🚀',
      status: isReady ? 'done' as const : healthCheckCount <= 1 ? 'active' as const : 'done' as const,
      detail: isReady ? 'Ready' : healthCheckCount <= 1 ? 'Starting' : 'Warmed',
    },
    {
      id: 'probe',
      label: 'Run health checks',
      icon: '🩺',
      status: isReady ? 'done' as const : healthCheckCount > 1 ? 'active' as const : 'pending' as const,
      detail: isReady ? 'Healthy' : healthCheckCount > 1 ? 'Checking' : 'Queued',
    },
    {
      id: 'mount',
      label: 'Mount interactive frame',
      icon: '📊',
      status: isReady ? 'done' as const : 'pending' as const,
      detail: isReady ? 'Visible' : 'Queued',
    },
  ]
  const isDashboardWarming = !!latestDashboard && !isReady
  const showDashboardProgress = isDashboardGenerating || isDashboardWarming
  const toolbarTitle = latestDashboard
    ? 'Live preview'
    : isDashboardGenerating
      ? 'Building preview'
      : 'No dashboard yet'
  const toolbarStatusLabel = isDashboardGenerating
    ? 'Generating...'
    : isDashboardWarming
      ? 'Waiting for service...'
      : null

  if (!sessionId) {
    return (
      <div className="right-panel-empty">
        <div className="right-panel-empty-kicker">Dashboard</div>
        <LayoutDashboard className="right-panel-empty-icon" />
        <h3 className="right-panel-empty-title">No active session</h3>
        <p className="right-panel-empty-subtitle">
          Start a conversation or run a workflow to open a live dashboard here.
        </p>
      </div>
    )
  }

  if (!latestDashboard && !isDashboardGenerating) {
    return (
      <div className="right-panel-empty">
        <div className="right-panel-empty-kicker">Dashboard</div>
        <LayoutDashboard className="right-panel-empty-icon" />
        <h3 className="right-panel-empty-title">No dashboard yet</h3>
        <p className="right-panel-empty-subtitle">
          Ask DeepEye to generate a dashboard for your attached data and the live preview will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className="panel-view">
      <div className="panel-toolbar">
        <div className="panel-toolbar-main">
          <div className="panel-toolbar-icon">
            <LayoutDashboard />
          </div>
          <div className="panel-toolbar-copy">
            <div className="panel-toolbar-label">Dashboard</div>
            <div className="panel-toolbar-title">{toolbarTitle}</div>
            {toolbarStatusLabel && (
              <div className="panel-toolbar-meta">
                <span className="panel-toolbar-status">
                  <Loader2 className="animate-spin" />
                  {toolbarStatusLabel}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="panel-toolbar-actions">
          {latestDashboard ? (
            <button
              type="button"
              onClick={() => {
                setLocalRefreshKey((prev) => prev + 1)
              }}
              className="panel-toolbar-btn"
            >
              <RefreshCw />
              Refresh
            </button>
          ) : null}
          {isReady ? (
            <a
              href={fullDashboardUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="panel-toolbar-link"
            >
              <ExternalLink />
              Open
            </a>
          ) : null}
        </div>
      </div>

      {showDashboardProgress ? (
        <div className="artifact-progress-shell">
          {isDashboardGenerating ? (
            <ArtifactProgressCard
              artifact="Dashboard"
              title="Generating dashboard"
              description="DeepEye is still designing the dashboard structure and packaging the preview app."
              icon={<LayoutDashboard size={18} />}
              variant="dashboard"
              signature="Visual analysis pipeline"
              status="running"
              statusLabel="Running"
              percent={generationPercent}
              currentLabel={generationCurrentLabel}
              metrics={[
                { label: 'Stage', value: `${Math.min(generationStageIndex + 1, generationSteps.length)}/${generationSteps.length}` },
                { label: 'Node', value: dashboardNodeIds[dashboardNodeIds.length - 1] || 'generate_dashboard' },
              ]}
              steps={generationSteps}
              tone="#0f766e"
            />
          ) : (
            <ArtifactProgressCard
              artifact="Dashboard"
              title="Starting live dashboard"
              description="The dashboard artifact is ready. DeepEye is warming the preview service before the interactive frame mounts."
              icon={<LayoutDashboard size={18} />}
              variant="dashboard"
              signature="Interactive preview"
              status={healthCheckCount > 0 ? 'running' : 'waiting'}
              statusLabel={healthCheckCount > 0 ? 'Connecting' : 'Starting'}
              percent={dashboardWarmupPercent}
              currentLabel={
                healthCheckCount > 1
                  ? 'Polling the preview endpoint until the dashboard responds.'
                  : 'Provisioning the dashboard container and loading the shell.'
              }
              metrics={[
                { label: 'Node', value: latestDashboard?.nodeId || 'generate_dashboard' },
                { label: 'Checks', value: healthCheckCount > 0 ? String(healthCheckCount) : 'Pending' },
              ]}
              steps={dashboardWarmupSteps}
              tone="#0f766e"
            />
          )}
        </div>
      ) : null}

      <div className={`panel-surface${latestDashboard ? ' panel-surface--dashboard' : ''}`}>
        {latestDashboard ? (
          <div ref={containerRef} className="panel-frame">
            {!isReady ? (
              <div className="panel-frame-overlay">
                <Loader2 className="h-7 w-7 animate-spin text-[var(--accent)]" />
                <p className="panel-frame-overlay-title">Starting dashboard service</p>
                <p className="panel-frame-overlay-subtitle">
                  This can take a short while while the preview environment starts.
                </p>
              </div>
            ) : null}

            {isReady ? (
              <div
                className="absolute top-0 left-0"
                style={{
                  width: '1280px',
                  height: `${100 / scale}%`,
                  transform: `scale(${scale})`,
                  transformOrigin: 'top left',
                }}
              >
                <iframe
                  key={`${fullDashboardUrl}-${refreshKey}`}
                  src={fullDashboardUrl}
                  className="h-full w-full border-none"
                  title="Dashboard Preview"
                  sandbox={PREVIEW_IFRAME_SANDBOX}
                />
              </div>
            ) : null}
          </div>
        ) : (
          <div className="panel-state-card">
            <div className="panel-state-icon">
              <Loader2 size={16} className="animate-spin" />
            </div>
            <div className="panel-state-copy">
              <div className="panel-state-title">Dashboard is in progress</div>
              <div className="panel-state-body">
                The workflow is still composing the dashboard artifact. This pane will switch to the live preview automatically.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
