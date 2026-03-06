import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from './stores/chat'
import { useAuthStore } from './stores/auth'
import { useRightPanelStore } from './stores/rightPanel'
import Sidebar from './components/Sidebar'
import DataSourceManager from './components/DataSourceManager'
import ChatBox from './components/ChatBox'
import { RightPanelLayout } from './components/right-panel/RightPanelLayout'
import './App.css'

function App() {
  const navigate = useNavigate()
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
  const currentSession = useChatStore((state) => state.currentSession)
  const messages = useChatStore((state) => state.messages)
  const createDraftSession = useChatStore((state) => state.createDraftSession)
  const currentUser = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const rightPanelCollapsed = useRightPanelStore((state) => state.collapsed)
  const setRightPanelCollapsed = useRightPanelStore((state) => state.setCollapsed)
  const rightPanelRatio = useRightPanelStore((state) => state.panelRatio)
  const setRightPanelRatio = useRightPanelStore((state) => state.setPanelRatio)
  const rightPanelPanes = useRightPanelStore((state) => state.panes)
  const openRightPanelTab = useRightPanelStore((state) => state.openTab)
  const chatTitle = useMemo(() => {
    const title = currentSession?.title?.trim()
    if (!title || title === 'New conversation') return 'DeepEye Assistant'
    return title
  }, [currentSession?.title])
  const selectedDataSourceCount = selectedDataSourceIds.length

  const handleDataSourceToggle = (id: string) => {
    setSelectedDataSourceIds((prev) => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  const toggleRightPanel = () => {
    if (rightPanelCollapsed) {
      setRightPanelCollapsed(false)
      if (rightPanelPanes.length === 0) {
        openRightPanelTab('files')
      }
      return
    }
    setRightPanelCollapsed(true)
  }

  const handleNewChat = () => {
    if (currentSession?.isDraft && messages.length === 0) {
      return
    }
    createDraftSession()
  }

  const handleLogout = () => {
    logout()
    navigate('/auth')
  }

  // Panel resize handlers
  const startPanelDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDraggingPanel(true)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const onPanelDrag = useCallback((e: MouseEvent) => {
    if (!isDraggingPanel || !mainAreaRef.current) return
    const mainRect = mainAreaRef.current.getBoundingClientRect()
    const mainWidth = mainRect.width
    const relativeX = e.clientX - mainRect.left
    const newRatio = ((mainWidth - relativeX) / mainWidth) * 100
    setRightPanelRatio(Math.max(MIN_PANEL_RATIO, Math.min(MAX_PANEL_RATIO, newRatio)))
  }, [isDraggingPanel, setRightPanelRatio])

  const stopPanelDrag = useCallback(() => {
    setIsDraggingPanel(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }, [])

  useEffect(() => {
    if (isDraggingPanel) {
      document.addEventListener('mousemove', onPanelDrag)
      document.addEventListener('mouseup', stopPanelDrag)
      return () => {
        document.removeEventListener('mousemove', onPanelDrag)
        document.removeEventListener('mouseup', stopPanelDrag)
      }
    }
  }, [isDraggingPanel, onPanelDrag, stopPanelDrag])

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
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
            <Sidebar
              collapsed={sidebarCollapsed}
              onToggleCollapse={toggleSidebar}
              currentUser={currentUser}
              onLogout={handleLogout}
            />
          </div>
          <div className="flex-shrink-0">
            <DataSourceManager
              selectedIds={selectedDataSourceIds}
              onToggle={handleDataSourceToggle}
              collapsed={sidebarCollapsed}
            />
          </div>
        </div>
      </aside>

      {/* Main Area */}
      <main ref={mainAreaRef} className="flex-1 flex min-w-0 relative" style={{ background: 'var(--main-bg)' }}>
        {/* Chat Area */}
        <div className="chat-area-shell flex flex-col min-w-0 relative" style={chatAreaStyle}>
          <div className="chat-topbar">
            <div className="chat-topbar-meta">
              <span className="chat-topbar-kicker">Chat</span>
              <span className="chat-topbar-title" title={chatTitle}>
                {chatTitle}
              </span>
            </div>
            <div className="chat-topbar-actions">
              <button
                type="button"
                className="chat-topbar-new-btn"
                onClick={handleNewChat}
                title="Start a new conversation"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>New chat</span>
              </button>
              <span className="chat-status-pill">
                {selectedDataSourceCount > 0 ? `${selectedDataSourceCount} data source(s) attached` : 'No data source selected'}
              </span>
              {sessionId && (
                <button
                  onClick={toggleRightPanel}
                  className={`chat-panel-toggle ${rightPanelCollapsed ? '' : 'active'}`}
                  title={rightPanelCollapsed ? 'Open workspace panel' : 'Hide workspace panel'}
                  aria-label={rightPanelCollapsed ? 'Open workspace panel' : 'Hide workspace panel'}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                    />
                  </svg>
                  <span className="chat-panel-toggle-status"></span>
                </button>
              )}
            </div>
          </div>

          <div className="chat-main-shell">
            {/* ChatBox is now always shown */}
            <ChatBox dataSourceIds={selectedDataSourceIds} />
          </div>
        </div>

        {!rightPanelCollapsed && (
          <button
            type="button"
            className="right-panel-mobile-backdrop"
            onClick={toggleRightPanel}
            aria-label="Close workspace panel"
          />
        )}

        {/* Right Panel */}
        <aside
          className={`right-panel flex relative ${rightPanelCollapsed ? 'is-collapsed' : 'is-open'} ${isDragging ? 'no-transition' : ''}`}
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
              onRequestClose={() => setRightPanelCollapsed(true)}
            />
          </div>
        </aside>
      </main>
    </div>
  )
}

export default App
