import { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useChatStore } from '../stores/chat'
import './Sidebar.css'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
}

export default function Sidebar({ collapsed, onToggleCollapse }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  
  // 每个属性单独订阅 - 最简单可靠的方式
  const sessions = useChatStore((state) => state.sessions)
  const sessionId = useChatStore((state) => state.sessionId)
  const isLoadingSessions = useChatStore((state) => state.isLoadingSessions)
  const currentSession = useChatStore((state) => state.currentSession)
  const messages = useChatStore((state) => state.messages)
  const fetchSessions = useChatStore((state) => state.fetchSessions)
  const selectSession = useChatStore((state) => state.selectSession)
  const deleteSession = useChatStore((state) => state.deleteSession)
  const createDraftSession = useChatStore((state) => state.createDraftSession)
  
  const [animatingTitles, setAnimatingTitles] = useState<Map<string, string>>(new Map())
  const previousSessionsRef = useRef<Array<{ id: string; title: string }>>([])

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  // Watch for title changes and animate
  useEffect(() => {
    const currentSessions = sessions.map((s) => ({ id: s.id, title: s.title }))
    const oldSessions = previousSessionsRef.current

    for (const newSession of currentSessions) {
      const oldSession = oldSessions.find((s) => s.id === newSession.id)
      // Detect title change from "New conversation" to user input
      if (oldSession && oldSession.title === 'New conversation' && newSession.title !== 'New conversation') {
        animateTitle(newSession.id, newSession.title)
      }
    }

    previousSessionsRef.current = currentSessions
  }, [sessions])

  const animateTitle = (sessionId: string, fullTitle: string) => {
    setAnimatingTitles((prev) => new Map(prev).set(sessionId, ''))

    let index = 0
    const interval = setInterval(() => {
      if (index < fullTitle.length) {
        setAnimatingTitles((prev) => new Map(prev).set(sessionId, fullTitle.slice(0, index + 1)))
        index++
      } else {
        clearInterval(interval)
        // Remove from animating map after animation completes
        setTimeout(() => {
          setAnimatingTitles((prev) => {
            const newMap = new Map(prev)
            newMap.delete(sessionId)
            return newMap
          })
        }, 100)
      }
    }, 100) // 100ms per character
  }

  const getDisplayTitle = (session: { id: string; title: string }) => {
    // If animating, show animated title
    if (animatingTitles.has(session.id)) {
      return animatingTitles.get(session.id) || ''
    }
    return session.title || 'New conversation'
  }

  const isAnimating = (sessionId: string) => {
    return animatingTitles.has(sessionId)
  }

  const handleNewChat = async () => {
    // If current session is an empty draft, just keep it.
    if (currentSession?.isDraft && messages.length === 0) {
      return
    }
    createDraftSession()
  }

  const handleSelectSession = async (id: string) => {
    await selectSession(id)
  }

  const handleDeleteSession = (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    if (confirm('Delete this conversation?')) {
      deleteSession(id)
    }
  }

  return (
    <div className={`flex flex-col h-full overflow-hidden sidebar ${collapsed ? 'collapsed text-hidden' : 'text-shown'}`}>
      {/* Logo & Collapse Toggle */}
      <div className="sidebar-header border-b border-[var(--sidebar-border)] p-3">
        <div className={`sidebar-header-row ${collapsed ? 'is-collapsed' : ''}`}>
          {!collapsed && (
            <div className="sidebar-brand min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                  DE
                </div>
                <span className="font-semibold text-base truncate sidebar-logo-text">DeepEye</span>
              </div>
            </div>
          )}
          <button
            onClick={onToggleCollapse}
            className={`sidebar-toggle-btn hover:bg-[var(--sidebar-hover)] transition-colors ${collapsed ? '' : 'ml-auto'}`}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg className={`w-5 h-5 transition-transform duration-200 ${collapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3">
        <div className="space-y-1 mb-6">
          <button
            onClick={() => navigate('/')}
            className={`nav-item ${isActive('/') && !isActive('/workflows') && !isActive('/knowledge-bases') ? 'active' : ''}`}
            title="Chat"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span className="sidebar-label">Chat</span>
          </button>
          <button
            onClick={() => navigate('/workflows')}
            className={`nav-item ${isActive('/workflows') ? 'active' : ''}`}
            title="Workflows"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span className="sidebar-label">Workflows</span>
          </button>
          <button
            onClick={() => navigate('/knowledge-bases')}
            className={`nav-item ${isActive('/knowledge-bases') ? 'active' : ''}`}
            title="Knowledge Base"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span className="sidebar-label">Knowledge Base</span>
          </button>
        </div>

        {/* Conversations */}
        <div className="mb-4 sidebar-section">
          <div className="flex items-center justify-between mb-2 px-2">
            <span className="text-xs font-medium text-[var(--sidebar-text-muted)] uppercase">Conversations</span>
            <button
              onClick={handleNewChat}
              className="p-1 rounded hover:bg-[var(--sidebar-hover)] transition-colors"
              title="New chat"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          {/* Session List */}
          <div className="space-y-1">
            {/* Loading skeleton */}
            {isLoadingSessions && (
              <div className="space-y-2 py-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="skeleton h-10 rounded-lg"></div>
                ))}
              </div>
            )}

            {/* Session list */}
            {!isLoadingSessions && sessions.length > 0 && (
              <>
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => handleSelectSession(session.id)}
                    className={`session-item ${session.id === sessionId ? 'active' : ''}`}
                  >
                    <span className="session-title">
                      {getDisplayTitle(session)}
                      {isAnimating(session.id) && <span className="typing-cursor">|</span>}
                    </span>
                    <button
                      onClick={(e) => handleDeleteSession(session.id, e)}
                      className="session-delete-btn"
                      title="Delete"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </>
            )}

            {/* Empty state */}
            {!isLoadingSessions && sessions.length === 0 && (
              <div className="text-center text-[var(--sidebar-text-muted)] text-sm py-8">
                <svg className="w-8 h-8 mx-auto mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                No conversations yet
              </div>
            )}
          </div>
        </div>
      </nav>
    </div>
  )
}

