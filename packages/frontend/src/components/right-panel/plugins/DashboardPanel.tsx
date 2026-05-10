import { useMemo, useState, useEffect, useRef } from 'react'
import { LayoutDashboard, ExternalLink, RefreshCw, Loader2 } from 'lucide-react'
import { ArtifactProgressCard } from '../ArtifactProgressCard'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { config } from '../../../config'
import { useLocale } from '../../../locale'
import { getArtifactNodeId, getArtifactPreviewUrl } from '../../../utils/artifactUtils'
import { createDashboardGeneration } from '../../../utils/artifactGeneration'

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
  const { t } = useLocale()
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
      if (artifact.kind === 'dashboard') {
        const url = getArtifactPreviewUrl(artifact)
        if (!url) return
        urls.push({
          nodeId: getArtifactNodeId(artifact) ?? 'dashboard',
          url,
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

  const isDashboardWarming = !!latestDashboard && !isReady
  const dashboardGeneration = createDashboardGeneration({
    t,
    isGenerating: isDashboardGenerating,
    isWarming: isDashboardWarming,
    isReady,
    stage: dashboardProgress.stage ?? 0,
    percent: dashboardProgress.percent || 0,
    logs: dashboardProgress.logs,
    nodeId: isDashboardGenerating
      ? dashboardNodeIds[dashboardNodeIds.length - 1]
      : latestDashboard?.nodeId,
    healthCheckCount,
  })
  const showDashboardProgress = !!dashboardGeneration
  const toolbarTitle = latestDashboard
    ? t('dashboard.livePreview')
    : isDashboardGenerating
      ? t('dashboard.buildingPreview')
      : t('dashboard.emptyTitle')
  const toolbarStatusLabel = isDashboardGenerating
    ? t('dashboard.generatingStatus')
    : isDashboardWarming
      ? t('dashboard.waitingServiceStatus')
      : null

  if (!sessionId) {
    return (
      <div className="right-panel-empty">
        <div className="right-panel-empty-kicker">{t('panel.dashboard.title')}</div>
        <LayoutDashboard className="right-panel-empty-icon" />
        <h3 className="right-panel-empty-title">{t('dashboard.emptyTitleNoSession')}</h3>
        <p className="right-panel-empty-subtitle">
          {t('dashboard.emptySubtitleNoSession')}
        </p>
      </div>
    )
  }

  if (!latestDashboard && !isDashboardGenerating) {
    return (
      <div className="right-panel-empty">
        <div className="right-panel-empty-kicker">{t('panel.dashboard.title')}</div>
        <LayoutDashboard className="right-panel-empty-icon" />
        <h3 className="right-panel-empty-title">{t('dashboard.emptyTitle')}</h3>
        <p className="right-panel-empty-subtitle">
          {t('dashboard.emptySubtitle')}
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
            <div className="panel-toolbar-label">{t('panel.dashboard.title')}</div>
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
              {t('common.refresh')}
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
              {t('app.open')}
            </a>
          ) : null}
        </div>
      </div>

      {showDashboardProgress ? (
        <div className="artifact-progress-shell">
          {dashboardGeneration ? <ArtifactProgressCard icon={<LayoutDashboard size={18} />} {...dashboardGeneration.card} /> : null}
        </div>
      ) : null}

      <div className={`panel-surface${latestDashboard ? ' panel-surface--dashboard' : ''}`}>
        {latestDashboard ? (
          <div ref={containerRef} className="panel-frame">
            {!isReady ? (
              <div className="panel-frame-overlay">
                <Loader2 className="h-7 w-7 animate-spin text-[var(--accent)]" />
                <p className="panel-frame-overlay-title">{t('dashboard.overlayTitle')}</p>
                <p className="panel-frame-overlay-subtitle">
                  {t('dashboard.overlaySubtitle')}
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
                  title={t('dashboard.iframeTitle')}
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
              <div className="panel-state-title">{t('dashboard.inProgressTitle')}</div>
              <div className="panel-state-body">
                {t('dashboard.inProgressBody')}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
