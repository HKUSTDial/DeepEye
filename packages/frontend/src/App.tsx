import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from './stores/chat'
import { useAuthStore } from './stores/auth'
import { useRightPanelStore } from './stores/rightPanel'
import Sidebar from './components/Sidebar'
import ChatBox from './components/ChatBox'
import { RightPanelLayout } from './components/right-panel/RightPanelLayout'
import './App.css'

function App() {
  const navigate = useNavigate()
  const [dataSourceIds, setDataSourceIds] = useState<string[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth < 1440 : false,
  )
  const [chatCollapsed, setChatCollapsed] = useState(false)

  const MIN_CHAT_RATIO = 22
  const MAX_CHAT_RATIO = 38

  const [isDraggingChat, setIsDraggingChat] = useState(false)
  const hasNormalizedLayoutRef = useRef(false)
  const mainAreaRef = useRef<HTMLDivElement>(null)

  const sessionId = useChatStore((state) => state.sessionId)
  const currentSession = useChatStore((state) => state.currentSession)
  const messages = useChatStore((state) => state.messages)
  const createDraftSession = useChatStore((state) => state.createDraftSession)
  const currentUser = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const rightPanelRatio = useRightPanelStore((state) => state.panelRatio)
  const setRightPanelRatio = useRightPanelStore((state) => state.setPanelRatio)

  const chatTitle = useMemo(() => {
    const title = currentSession?.title?.trim()
    if (!title || title === 'New conversation') return 'Ask DeepEye'
    return title
  }, [currentSession?.title])
  const workspaceNote = useMemo(() => {
    if (chatTitle !== 'Ask DeepEye') {
      return `Thread: ${chatTitle}`
    }
    return 'Reports, dashboards, files, and previews'
  }, [chatTitle])

  const toggleSidebarCollapse = () => {
    setSidebarCollapsed((current) => !current)
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

  const startChatDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDraggingChat(true)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const onChatDrag = useCallback((e: MouseEvent) => {
    if (!isDraggingChat || !mainAreaRef.current) return

    const mainRect = mainAreaRef.current.getBoundingClientRect()
    const mainWidth = mainRect.width
    const relativeX = e.clientX - mainRect.left
    const nextRatio = ((mainWidth - relativeX) / mainWidth) * 100

    setRightPanelRatio(Math.max(MIN_CHAT_RATIO, Math.min(MAX_CHAT_RATIO, nextRatio)))
  }, [isDraggingChat, setRightPanelRatio])

  const stopChatDrag = useCallback(() => {
    setIsDraggingChat(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }, [])

  useEffect(() => {
    if (!isDraggingChat) return

    document.addEventListener('mousemove', onChatDrag)
    document.addEventListener('mouseup', stopChatDrag)
    return () => {
      document.removeEventListener('mousemove', onChatDrag)
      document.removeEventListener('mouseup', stopChatDrag)
    }
  }, [isDraggingChat, onChatDrag, stopChatDrag])

  useEffect(() => {
    if (hasNormalizedLayoutRef.current || typeof window === 'undefined') return
    hasNormalizedLayoutRef.current = true

    if (rightPanelRatio < MIN_CHAT_RATIO || rightPanelRatio > 42) {
      setRightPanelRatio(window.innerWidth < 1320 ? 30 : 28)
    }
  }, [rightPanelRatio, setRightPanelRatio])

  const workspaceStyle = useMemo(
    () => ({
      flex: chatCollapsed ? '1 1 auto' : `1 1 ${100 - rightPanelRatio}%`,
    }),
    [chatCollapsed, rightPanelRatio],
  )

  const chatStyle = useMemo(
    () => ({
      flex: chatCollapsed ? '0 0 56px' : `0 0 ${rightPanelRatio}%`,
    }),
    [chatCollapsed, rightPanelRatio],
  )

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation drawer"
        />
      )}

      <aside
        className={`sidebar-drawer ${sidebarOpen ? 'is-open' : ''} ${sidebarCollapsed ? 'is-collapsed' : 'is-expanded'}`}
        style={{ width: sidebarCollapsed ? '96px' : '304px' }}
      >
        <div className="app-sidebar-panel">
          <div className="app-sidebar-body">
            <Sidebar
              collapsed={sidebarCollapsed}
              onToggleCollapse={toggleSidebarCollapse}
              currentUser={currentUser}
              onLogout={handleLogout}
            />
          </div>
        </div>
      </aside>

      <main className="workspace-shell">
        <section className="workspace-stage">
          <div ref={mainAreaRef} className={`workspace-split ${chatCollapsed ? 'chat-collapsed' : ''}`}>
            <section className="workspace-main" style={workspaceStyle}>
              <div className="workspace-main-card">
                <div className="workspace-main-toolbar">
                  <div className="workspace-main-toolbar-copy">
                    <button
                      type="button"
                      className="workspace-shell-btn"
                      onClick={() => setSidebarOpen(true)}
                      aria-label="Open navigation"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                      </svg>
                      <span>Menu</span>
                    </button>
                    <div className="workspace-main-toolbar-copytext">
                      <span className="workspace-main-toolbar-heading">Workspace</span>
                      <span className="workspace-main-toolbar-note" title={workspaceNote}>{workspaceNote}</span>
                    </div>
                  </div>
                  <div className="workspace-main-toolbar-actions">
                    <button
                      type="button"
                      className="workspace-toolbar-btn"
                      onClick={() => setChatCollapsed((current) => !current)}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        {chatCollapsed ? (
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.9} d="M3 7h18M3 12h18M3 17h18" />
                        ) : (
                          <>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.9} d="M4 7h16M4 12h10M4 17h16" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.9} d="M18 10v4" />
                          </>
                        )}
                      </svg>
                      {chatCollapsed ? 'Show assistant' : 'Hide assistant'}
                    </button>
                    <button
                      type="button"
                      className="workspace-toolbar-btn workspace-toolbar-btn-primary"
                      onClick={handleNewChat}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v14M5 12h14" />
                      </svg>
                      New chat
                    </button>
                  </div>
                </div>
                <div className="workspace-main-body">
                  <RightPanelLayout sessionId={sessionId} dataSourceIds={dataSourceIds} />
                </div>
              </div>
            </section>

            {!chatCollapsed && (
              <div
                className={`chat-rail-splitter ${isDraggingChat ? 'is-active' : ''}`}
                onMouseDown={startChatDrag}
              />
            )}

            <aside className={`chat-rail ${chatCollapsed ? 'is-collapsed' : 'is-open'}`} style={chatStyle}>
              {chatCollapsed ? (
                <button
                  type="button"
                  className="chat-rail-collapsed-bar"
                  onClick={() => setChatCollapsed(false)}
                  aria-label="Open assistant"
                >
                  <span className="chat-rail-collapsed-icon" aria-hidden="true">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.9} d="M8 10h8M8 14h5" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.9} d="M12 3c4.971 0 9 3.806 9 8.5S16.971 20 12 20a9.57 9.57 0 01-3.756-.741L4 20l1.05-3.063C3.768 15.43 3 13.544 3 11.5 3 6.806 7.029 3 12 3Z" />
                    </svg>
                  </span>
                  <span className="chat-rail-collapsed-title">Open</span>
                </button>
              ) : (
                <div className="chat-rail-card">
                  <div className="chat-rail-header">
                    <div className="chat-rail-header-copy">
                      <span className="chat-rail-kicker">Assistant</span>
                      <span className="chat-rail-title" title={chatTitle}>{chatTitle}</span>
                    </div>
                    <div className="chat-rail-actions">
                      <button
                        type="button"
                        className="chat-rail-action-btn"
                        onClick={() => setChatCollapsed(true)}
                      >
                        Hide
                      </button>
                    </div>
                  </div>
                  <div className="chat-rail-body">
                    <ChatBox
                      dataSourceIds={dataSourceIds}
                      onDataSourceIdsChange={setDataSourceIds}
                      compact
                    />
                  </div>
                </div>
              )}
            </aside>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
