import { useMemo, useState, useEffect, useRef } from 'react'
import { LayoutDashboard, ExternalLink, RefreshCw, Loader2 } from 'lucide-react'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { config } from '../../../config'

export function DashboardPanel({
  sessionId,
}: {
  sessionId: string | null
}) {
  const [localRefreshKey, setLocalRefreshKey] = useState(0)
  const [isReady, setIsReady] = useState(false)
  const [isChecking, setIsChecking] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const checkIntervalRef = useRef<number | null>(null)

  const sessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )

  const dashboardRefreshKey = sessionState?.dashboardRefreshKey || 0
  const refreshKey = useMemo(() => localRefreshKey + dashboardRefreshKey, [localRefreshKey, dashboardRefreshKey])

  const dashboardUrls = useMemo(() => {
    if (!sessionState?.nodeStatus) return []

    const urls: { nodeId: string; url: string }[] = []
    Object.entries(sessionState.nodeStatus).forEach(([nodeId, statusInfo]) => {
      const info = statusInfo as { outputs?: Record<string, unknown> }
      const outputs = info.outputs
      if (outputs?.dashboard_url && typeof outputs.dashboard_url === 'string') {
        urls.push({
          nodeId,
          url: outputs.dashboard_url,
        })
      }
    })
    return urls
  }, [sessionState?.nodeStatus])

  const latestDashboard = dashboardUrls[dashboardUrls.length - 1]

  const fullDashboardUrl = useMemo(() => {
    if (!latestDashboard?.url) return ''
    if (latestDashboard.url.startsWith('http')) return latestDashboard.url

    const base = config.api.baseUrl.replace('/api/v1', '')
    return `${base}${latestDashboard.url.startsWith('/') ? '' : '/'}${latestDashboard.url}`
  }, [latestDashboard?.url])

  useEffect(() => {
    if (!fullDashboardUrl) {
      setIsReady(false)
      return
    }

    const checkReady = async () => {
      setIsChecking(true)
      try {
        const res = await fetch(fullDashboardUrl, { method: 'HEAD' })
        if (res.ok) {
          setIsReady(true)
          if (checkIntervalRef.current) {
            window.clearInterval(checkIntervalRef.current)
            checkIntervalRef.current = null
          }
        }
      } catch {
        // Ignore errors while the preview service is still booting.
      } finally {
        setIsChecking(false)
      }
    }

    setIsReady(false)
    checkReady()
    checkIntervalRef.current = window.setInterval(checkReady, 2000)

    return () => {
      if (checkIntervalRef.current) {
        window.clearInterval(checkIntervalRef.current)
        checkIntervalRef.current = null
      }
    }
  }, [fullDashboardUrl, refreshKey])

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

  if (!latestDashboard) {
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
            <div className="panel-toolbar-title">Live preview</div>
            {(!isReady || isChecking) && (
              <div className="panel-toolbar-meta">
                <span className="panel-toolbar-status">
                  <Loader2 className="animate-spin" />
                  Waiting for service...
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="panel-toolbar-actions">
          <button
            type="button"
            onClick={() => {
              setIsReady(false)
              setLocalRefreshKey((prev) => prev + 1)
            }}
            className="panel-toolbar-btn"
          >
            <RefreshCw />
            Refresh
          </button>
          <a
            href={fullDashboardUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="panel-toolbar-link"
          >
            <ExternalLink />
            Open
          </a>
        </div>
      </div>

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
          />
        </div>
      </div>
    </div>
  )
}
