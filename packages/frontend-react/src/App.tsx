import { useState, useRef, useEffect, useMemo } from 'react'
import { useChatStore } from './stores/chat'
import { useRightPanelStore } from './stores/rightPanel'
import Sidebar from './components/Sidebar'
import DataSourceManager from './components/DataSourceManager'
import ChatBox from './components/ChatBox'
import { RightPanelLayout } from './components/right-panel/RightPanelLayout'
import './App.css'

function App() {
  const [selectedDataSourceIds, setSelectedDataSourceIds] = useState<string[]>([])
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  // Resizable panel ratios (percentage based)
  const MIN_PANEL_RATIO = 25
  const MAX_PANEL_RATIO = 60

  // Drag state
  const [isDraggingPanel, setIsDraggingPanel] = useState(false)
  const mainAreaRef = useRef<HTMLDivElement>(null)

  // 每个属性单独订阅 - 最简单可靠的方式
  const sessionId = useChatStore((state) => state.sessionId)
  const rightPanelCollapsed = useRightPanelStore((state) => state.collapsed)
  const setRightPanelCollapsed = useRightPanelStore((state) => state.setCollapsed)
  const rightPanelRatio = useRightPanelStore((state) => state.panelRatio)
  const setRightPanelRatio = useRightPanelStore((state) => state.setPanelRatio)

  const handleDataSourceToggle = (id: string) => {
    setSelectedDataSourceIds((prev) => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  const toggleRightPanel = () => {
    setRightPanelCollapsed(!rightPanelCollapsed)
  }

  // Panel resize handlers
  const startPanelDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDraggingPanel(true)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const onPanelDrag = (e: MouseEvent) => {
    if (!isDraggingPanel || !mainAreaRef.current) return
    const mainRect = mainAreaRef.current.getBoundingClientRect()
    const mainWidth = mainRect.width
    const relativeX = e.clientX - mainRect.left
    const newRatio = ((mainWidth - relativeX) / mainWidth) * 100
    setRightPanelRatio(Math.max(MIN_PANEL_RATIO, Math.min(MAX_PANEL_RATIO, newRatio)))
  }

  const stopPanelDrag = () => {
    setIsDraggingPanel(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  useEffect(() => {
    if (isDraggingPanel) {
      document.addEventListener('mousemove', onPanelDrag)
      document.addEventListener('mouseup', stopPanelDrag)
      return () => {
        document.removeEventListener('mousemove', onPanelDrag)
        document.removeEventListener('mouseup', stopPanelDrag)
      }
    }
  }, [isDraggingPanel])

  const isDragging = isDraggingPanel

  const rightPanelStyle = useMemo(
    () => ({
      flex: rightPanelCollapsed ? '0 0 0' : `0 0 ${rightPanelRatio}%`,
    }),
    [rightPanelCollapsed, rightPanelRatio],
  )

  const chatAreaStyle = useMemo(() => ({
    flex: rightPanelCollapsed ? '1 1 100%' : `1 1 ${100 - rightPanelRatio}%`,
  }), [rightPanelCollapsed, rightPanelRatio])

  return (
    <div className="app-shell flex h-screen w-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`sidebar flex flex-col h-full flex-shrink-0 transition-all duration-300 ${
          sidebarCollapsed ? 'w-20' : 'w-64'
        }`}
        style={{ background: 'var(--sidebar-bg)' }}
      >
        <div className="flex-1 overflow-visible flex flex-col">
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggleCollapse={toggleSidebar}
          />
          <DataSourceManager
            selectedIds={selectedDataSourceIds}
            onToggle={handleDataSourceToggle}
            collapsed={sidebarCollapsed}
          />
        </div>
      </aside>

      {/* Main Area */}
      <main ref={mainAreaRef} className="flex-1 flex min-w-0 relative" style={{ background: 'var(--main-bg)' }}>
        {/* Chat Area */}
        <div className="flex flex-col min-w-0 relative" style={chatAreaStyle}>
          {/* Top Control Bar */}
          <div className="absolute top-3 right-3 z-50 flex items-center justify-end pointer-events-none">
            {/* Toggle Files Panel Button */}
            {sessionId && (
              <button
                onClick={toggleRightPanel}
                className="btn p-2 rounded-xl hover:bg-white/10 pointer-events-auto"
                title={rightPanelCollapsed ? 'Show panel' : 'Hide panel'}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-5 h-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  />
                </svg>
              </button>
            )}
          </div>

          {/* ChatBox is now always shown */}
          <ChatBox dataSourceIds={selectedDataSourceIds} />
        </div>

        {/* Right Panel */}
        <aside
          className={`right-panel flex relative ${isDragging ? 'no-transition' : ''}`}
          style={rightPanelStyle}
        >
          {!rightPanelCollapsed && (
            <div
              className={`resize-handle-panel ${isDraggingPanel ? 'resize-active' : ''}`}
              onMouseDown={startPanelDrag}
            ></div>
          )}
          <div
            className={`right-panel-content flex h-full flex-1 overflow-hidden ${
              rightPanelCollapsed ? 'opacity-0 pointer-events-none' : ''
            }`}
          >
            <RightPanelLayout 
              sessionId={sessionId} 
              dataSourceIds={selectedDataSourceIds} 
            />
          </div>
        </aside>
      </main>
    </div>
  )
}

export default App
