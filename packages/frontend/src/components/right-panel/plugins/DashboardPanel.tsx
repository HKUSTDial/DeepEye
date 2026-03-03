import { useMemo, useState, useEffect, useRef } from 'react'
import { LayoutDashboard, ExternalLink, RefreshCw, Loader2 } from 'lucide-react'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { useTheme } from '../../../hooks/useTheme'
import { config } from '../../../config'

export function DashboardPanel({ 
  sessionId 
}: { 
  sessionId: string | null 
}) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
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
    
    const urls: { nodeId: string, url: string }[] = []
    Object.entries(sessionState.nodeStatus).forEach(([nodeId, statusInfo]) => {
      const info = statusInfo as { outputs?: Record<string, unknown> }
      const outputs = info.outputs
      if (outputs?.dashboard_url && typeof outputs.dashboard_url === 'string') {
        urls.push({
          nodeId,
          url: outputs.dashboard_url
        })
      }
    })
    return urls
  }, [sessionState?.nodeStatus])

  const latestDashboard = dashboardUrls[dashboardUrls.length - 1]

  const fullDashboardUrl = useMemo(() => {
    if (!latestDashboard?.url) return ''
    if (latestDashboard.url.startsWith('http')) return latestDashboard.url
    
    // Construct full URL from API base
    const base = config.api.baseUrl.replace('/api/v1', '')
    return `${base}${latestDashboard.url.startsWith('/') ? '' : '/'}${latestDashboard.url}`
  }, [latestDashboard?.url])

  // Check if dashboard is ready (avoid 502)
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
      } catch (e) {
        // Ignore errors
      } finally {
        setIsChecking(false)
      }
    }

    setIsReady(false)
    checkReady()

    // Start polling if not ready
    if (!isReady) {
      checkIntervalRef.current = window.setInterval(checkReady, 2000)
    }

    return () => {
      if (checkIntervalRef.current) {
        window.clearInterval(checkIntervalRef.current)
        checkIntervalRef.current = null
      }
    }
  }, [fullDashboardUrl, refreshKey])

  // Handle scaling based on container width
  // Assume dashboard target width is 1280px
  useEffect(() => {
    if (!containerRef.current) return

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect
        const targetWidth = 1280
        const newScale = Math.min(width / targetWidth, 1) // Only scale down
        setScale(newScale)
      }
    })

    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  if (!sessionId) {
    return (
      <div className={`flex h-full w-full items-center justify-center p-8 text-center ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
        <p>No active session</p>
      </div>
    )
  }

  if (!latestDashboard) {
    return (
      <div className={`h-full w-full flex flex-col items-center justify-center p-8 text-center ${
        isDark ? 'bg-slate-950' : 'bg-slate-50'
      }`}>
        <div className={`mb-6 rounded-2xl p-4 ring-1 ${
          isDark ? 'bg-slate-900/50 ring-slate-800' : 'bg-white ring-slate-200'
        }`}>
          <LayoutDashboard className={`h-8 w-8 ${isDark ? 'text-indigo-400' : 'text-indigo-600'}`} />
        </div>
        <h3 className={`mb-2 text-lg font-medium ${isDark ? 'text-slate-200' : 'text-slate-900'}`}>
          No Dashboard Generated
        </h3>
        <p className={`max-w-xs text-sm leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
          Ask DeepEye to "generate a dashboard" for your data, and it will appear here.
        </p>
      </div>
    )
  }

  return (
    <div className={`h-full w-full flex flex-col ${isDark ? 'bg-slate-950' : 'bg-white'}`}>
      <div className={`flex items-center justify-between border-b px-3 py-2 text-xs ${
        isDark ? 'border-slate-800 bg-slate-900/60' : 'border-slate-200 bg-slate-50'
      }`}>
        <div className={`flex items-center gap-2 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
          <LayoutDashboard className="h-3.5 w-3.5" />
          <span className="font-semibold">Dashboard Preview</span>
          {(!isReady || isChecking) && (
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <Loader2 className="h-3 w-3 animate-spin" />
              Waiting for service...
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setIsReady(false)
              setLocalRefreshKey(prev => prev + 1)
            }}
            className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors ${
              isDark 
                ? 'border-slate-700 text-slate-200 hover:bg-slate-800' 
                : 'border-slate-300 text-slate-700 hover:bg-slate-100'
            }`}
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </button>
          <a
            href={fullDashboardUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors ${
              isDark 
                ? 'border-slate-700 text-slate-200 hover:bg-slate-800' 
                : 'border-slate-300 text-slate-700 hover:bg-slate-100'
            }`}
          >
            <ExternalLink className="h-3 w-3" />
            Open
          </a>
        </div>
      </div>
      <div 
        ref={containerRef}
        className="flex-1 min-h-0 bg-white relative overflow-hidden"
      >
        {!isReady ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-slate-50/50 backdrop-blur-[2px] z-10">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
            <p className="text-sm text-slate-500">Starting dashboard service...</p>
            <p className="text-xs text-slate-400 max-w-[200px] text-center">
              This might take up to 30 seconds to install dependencies and start the server.
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
            className="w-full h-full border-none"
            title="Dashboard Preview"
          />
        </div>
      </div>
    </div>
  )
}
