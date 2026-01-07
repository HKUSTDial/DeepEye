import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from '../stores/chat'
import './Sidebar.css'

export default function Sidebar() {
  const navigate = useNavigate()
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
    <div className="flex flex-col h-full overflow-hidden">
      {/* Top Actions */}
      <div className="p-2">
        <button
          onClick={() => navigate('/workflows')}
          className="btn w-full flex items-center gap-3 px-3 py-3 rounded-xl border border-[var(--sidebar-border)] hover:bg-[var(--sidebar-hover)] text-sm mb-2"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M7.5 6.75h9m-9 4.5h9m-9 4.5h9M3 5.25a1.5 1.5 0 011.5-1.5h15A1.5 1.5 0 0121 5.25v13.5a1.5 1.5 0 01-1.5 1.5h-15A1.5 1.5 0 013 18.75V5.25z"
            />
          </svg>
          Workflows
        </button>
        <button
          onClick={() => navigate('/knowledge-bases')}
          className="btn w-full flex items-center gap-3 px-3 py-3 rounded-xl border border-[var(--sidebar-border)] hover:bg-[var(--sidebar-hover)] text-sm mb-2"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4.5 19.5V6.75A2.25 2.25 0 016.75 4.5h10.5A2.25 2.25 0 0119.5 6.75V19.5l-3.75-2.25L12 19.5l-3.75-2.25L4.5 19.5z"
            />
          </svg>
          Knowledge Base
        </button>
        <button
          onClick={handleNewChat}
          className="btn w-full flex items-center gap-3 px-3 py-3 rounded-xl border border-[var(--sidebar-border)] hover:bg-[var(--sidebar-hover)] text-sm"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New chat
        </button>
      </div>

      {/* Session List */}
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {/* Loading skeleton */}
        {isLoadingSessions && (
          <div className="space-y-2 py-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-10 rounded-lg"></div>
            ))}
          </div>
        )}

        {/* Session list */}
        {!isLoadingSessions && (
          <ul className="space-y-1">
            {sessions.map((session) => (
              <li key={session.id}>
                <div
                  onClick={() => handleSelectSession(session.id)}
                  className={`group flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer text-sm session-item ${
                    sessionId === session.id
                      ? 'bg-[var(--sidebar-active)]'
                      : 'hover:bg-[var(--sidebar-hover)]'
                  }`}
                >
                  {/* Chat Icon */}
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="w-4 h-4 flex-shrink-0 text-[var(--sidebar-text-muted)]"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                  {/* Title */}
                  <span className="flex-1 truncate">
                    {getDisplayTitle(session)}
                    {isAnimating(session.id) && <span className="typing-cursor">|</span>}
                  </span>
                  {/* Delete */}
                  <button
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    className="btn opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/20 text-[var(--sidebar-text-muted)] hover:text-red-400"
                    title="Delete"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="w-3.5 h-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </li>
            ))}

            {sessions.length === 0 && (
              <li className="text-center text-[var(--sidebar-text-muted)] text-sm py-8">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-8 h-8 mx-auto mb-2 opacity-40"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="1"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
                No conversations yet
              </li>
            )}
          </ul>
        )}
      </nav>
    </div>
  )
}

