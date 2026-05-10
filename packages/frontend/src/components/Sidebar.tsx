import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  selectCurrentMessages,
  selectCurrentSessionId,
  useChatStore,
} from '../stores/chat'
import type { Session } from '../types'
import { getLocalizedConversationTitle, isDefaultConversationTitle, useLocale } from '../locale'
import { deferEffectWork } from '../utils/effects'
import './Sidebar.css'

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  currentUser?: {
    username: string
    email: string
  } | null
  onLogout?: () => void
}

export default function Sidebar({ collapsed, onToggleCollapse, currentUser = null, onLogout }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const PINNED_SESSIONS_STORAGE_KEY = 'deepeye:pinned-sessions'
  const { t, toggleLocale } = useLocale()
  
  // 每个属性单独订阅 - 最简单可靠的方式
  const sessions = useChatStore((state) => state.sessions)
  const sessionId = useChatStore(selectCurrentSessionId)
  const isLoadingSessions = useChatStore((state) => state.isLoadingSessions)
  const currentSession = useChatStore((state) => state.currentSession)
  const messages = useChatStore(selectCurrentMessages)
  const fetchSessions = useChatStore((state) => state.fetchSessions)
  const selectSession = useChatStore((state) => state.selectSession)
  const deleteSession = useChatStore((state) => state.deleteSession)
  const createDraftSession = useChatStore((state) => state.createDraftSession)
  const updateSessionTitle = useChatStore((state) => state.updateSessionTitle)
  
  const [animatingTitles, setAnimatingTitles] = useState<Map<string, string>>(new Map())
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null)
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [pinnedSessionIds, setPinnedSessionIds] = useState<string[]>(() => {
    if (typeof window === 'undefined') return []
    try {
      const raw = window.localStorage.getItem(PINNED_SESSIONS_STORAGE_KEY)
      if (!raw) return []
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
    } catch {
      return []
    }
  })
  const previousSessionsRef = useRef<Array<{ id: string; title: string }>>([])
  const pinnedSessionSet = useMemo(() => new Set(pinnedSessionIds), [pinnedSessionIds])
  const sortedSessions = useMemo(() => {
    return [...sessions].sort((a, b) => {
      const aTs = Date.parse(a.updated_at || a.created_at || '')
      const bTs = Date.parse(b.updated_at || b.created_at || '')
      return (Number.isNaN(bTs) ? 0 : bTs) - (Number.isNaN(aTs) ? 0 : aTs)
    })
  }, [sessions])
  const pinnedSessions = useMemo(
    () => sortedSessions.filter((session) => pinnedSessionSet.has(session.id)),
    [pinnedSessionSet, sortedSessions],
  )
  const groupedSessions = useMemo(() => {
    const now = new Date()
    now.setHours(0, 0, 0, 0)
    const todayTimestamp = now.getTime()
    const dayMs = 24 * 60 * 60 * 1000
    const getDayDiff = (value: string) => {
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return Number.POSITIVE_INFINITY
      date.setHours(0, 0, 0, 0)
      return Math.floor((todayTimestamp - date.getTime()) / dayMs)
    }
    const groups: { key: string; label: string; sessions: Session[] }[] = [
      { key: 'today', label: t('sidebar.today'), sessions: [] },
      { key: 'yesterday', label: t('sidebar.yesterday'), sessions: [] },
      { key: 'week', label: t('sidebar.last7days'), sessions: [] },
      { key: 'earlier', label: t('sidebar.earlier'), sessions: [] },
    ]
    for (const session of sortedSessions) {
      if (pinnedSessionSet.has(session.id)) {
        continue
      }
      const diff = getDayDiff(session.updated_at || session.created_at)
      if (diff <= 0) {
        groups[0].sessions.push(session)
      } else if (diff === 1) {
        groups[1].sessions.push(session)
      } else if (diff <= 7) {
        groups[2].sessions.push(session)
      } else {
        groups[3].sessions.push(session)
      }
    }
    return groups.filter((group) => group.sessions.length > 0)
  }, [pinnedSessionSet, sortedSessions, t])

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  const animateTitle = useCallback((sessionId: string, fullTitle: string) => {
    setAnimatingTitles((prev) => new Map(prev).set(sessionId, ''))

    let index = 0
    const interval = setInterval(() => {
      if (index < fullTitle.length) {
        setAnimatingTitles((prev) => new Map(prev).set(sessionId, fullTitle.slice(0, index + 1)))
        index++
      } else {
        clearInterval(interval)
        setTimeout(() => {
          setAnimatingTitles((prev) => {
            const newMap = new Map(prev)
            newMap.delete(sessionId)
            return newMap
          })
        }, 100)
      }
    }, 100)
  }, [])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(PINNED_SESSIONS_STORAGE_KEY, JSON.stringify(pinnedSessionIds))
  }, [PINNED_SESSIONS_STORAGE_KEY, pinnedSessionIds])

  useEffect(() => {
    return deferEffectWork(() => {
      setPinnedSessionIds((current) => current.filter((id) => sessions.some((session) => session.id === id)))
    })
  }, [sessions])

  useEffect(() => {
    if (!deleteTarget) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDeleteTarget(null)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [deleteTarget])

  // Watch for title changes and animate
  useEffect(() => {
    const currentSessions = sessions.map((s) => ({ id: s.id, title: s.title }))
    const oldSessions = previousSessionsRef.current

    for (const newSession of currentSessions) {
      const oldSession = oldSessions.find((s) => s.id === newSession.id)
      if (oldSession && isDefaultConversationTitle(oldSession.title) && !isDefaultConversationTitle(newSession.title)) {
        animateTitle(newSession.id, newSession.title)
      }
    }

    previousSessionsRef.current = currentSessions
  }, [animateTitle, sessions])

  const getDisplayTitle = (session: { id: string; title: string }) => {
    // If animating, show animated title
    if (animatingTitles.has(session.id)) {
      return animatingTitles.get(session.id) || ''
    }
    return getLocalizedConversationTitle(session.title, t)
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

  const handleSessionKeyDown = (event: React.KeyboardEvent<HTMLDivElement>, id: string) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      void handleSelectSession(id)
    }
  }

  const handleDeleteSession = (id: string, title: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setDeleteTarget({ id, title: getLocalizedConversationTitle(title, t) })
  }

  const togglePinnedSession = (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setPinnedSessionIds((current) => (
      current.includes(id) ? current.filter((value) => value !== id) : [id, ...current]
    ))
  }

  const startRenamingSession = (session: Session, event: React.MouseEvent) => {
    event.stopPropagation()
    setRenamingSessionId(session.id)
    setRenameValue(isDefaultConversationTitle(session.title) ? '' : session.title)
  }

  const cancelRenamingSession = () => {
    setRenamingSessionId(null)
    setRenameValue('')
  }

  const submitSessionRename = async () => {
    if (!renamingSessionId) return
    const nextTitle = renameValue.trim()
    if (!nextTitle) {
      cancelRenamingSession()
      return
    }
    await updateSessionTitle(renamingSessionId, nextTitle)
    cancelRenamingSession()
  }

  const cancelDeleteSession = () => {
    setDeleteTarget(null)
  }

  const confirmDeleteSession = async () => {
    if (!deleteTarget) return
    await deleteSession(deleteTarget.id)
    setDeleteTarget(null)
  }

  return (
    <div className={`flex flex-col h-full overflow-hidden sidebar ${collapsed ? 'collapsed text-hidden' : 'text-shown'}`}>
      {/* Logo & Collapse Toggle */}
      <div className="sidebar-header border-b border-[var(--sidebar-border)] p-3">
        <div className={`sidebar-header-row ${collapsed ? 'is-collapsed' : ''}`}>
          {!collapsed && (
            <div className="sidebar-brand min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-sm">
                  DE
                </div>
                <span className="font-semibold text-base truncate sidebar-logo-text">DeepEye</span>
              </div>
            </div>
          )}
          <button
            onClick={onToggleCollapse}
            className={`sidebar-toggle-btn hover:bg-[var(--sidebar-hover)] transition-colors ${collapsed ? '' : 'ml-auto'}`}
            title={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
            aria-label={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
          >
            <svg className={`w-5 h-5 transition-transform duration-200 ${collapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Navigation：min-h-0 使 flex 子项在内容过长时可收缩，从而出现滚动条 */}
      <nav className="flex-1 min-h-0 overflow-y-auto p-3">
        <div className="space-y-1 mb-6">
          <button
            onClick={() => navigate('/')}
            className={`nav-item ${isActive('/') ? 'active' : ''}`}
            title={t('common.chat')}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span className="sidebar-label">{t('common.chat')}</span>
          </button>
        </div>

        <div className="mb-4 sidebar-section">
          <div className="flex items-center justify-between mb-2 px-2">
            <div className="sidebar-section-title-wrap">
              <span className="text-xs font-medium text-[var(--sidebar-text-muted)] uppercase">{t('sidebar.conversations')}</span>
              <span className="session-total-chip">{sessions.length}</span>
            </div>
            <button
              onClick={handleNewChat}
              className="p-1 rounded hover:bg-[var(--sidebar-hover)] transition-colors"
              title={t('common.newChat')}
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
              <div className="session-groups">
                {pinnedSessions.length > 0 && (
                  <section className="session-group">
                    <div className="session-group-header">
                      <span>{t('sidebar.pinnedGroup')}</span>
                      <span className="session-group-count">{pinnedSessions.length}</span>
                    </div>
                    <div className="session-group-list">
                      {pinnedSessions.map((session) => (
                        <div
                          key={session.id}
                          onClick={() => handleSelectSession(session.id)}
                          onKeyDown={(event) => handleSessionKeyDown(event, session.id)}
                          className={`session-item ${session.id === sessionId ? 'active' : ''}`}
                          role="button"
                          tabIndex={0}
                          aria-label={t('sidebar.openConversation', { title: getDisplayTitle(session) })}
                        >
                          <div className="session-item-main">
                            {renamingSessionId === session.id ? (
                              <input
                                className="session-rename-input"
                                value={renameValue}
                                autoFocus
                                onChange={(event) => setRenameValue(event.target.value)}
                                onClick={(event) => event.stopPropagation()}
                                onBlur={() => void submitSessionRename()}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter') {
                                    event.preventDefault()
                                    void submitSessionRename()
                                  } else if (event.key === 'Escape') {
                                    event.preventDefault()
                                    cancelRenamingSession()
                                  }
                                }}
                              />
                            ) : (
                              <>
                                <span className="session-title">
                                  {getDisplayTitle(session)}
                                  {isAnimating(session.id) && <span className="typing-cursor">|</span>}
                                </span>
                                <div className="session-meta">
                                  <span className="session-meta-chip">{t('common.pinned')}</span>
                                  {session.id === sessionId && <span className="session-meta-chip is-active">{t('common.active')}</span>}
                                </div>
                              </>
                            )}
                          </div>
                          <div className="session-item-actions">
                            <button
                              onClick={(event) => togglePinnedSession(session.id, event)}
                              className="session-action-btn session-pin-btn"
                              title={t('sidebar.unpinConversation')}
                              aria-label={t('sidebar.unpinConversation')}
                            >
                              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="m11.49 2.19 5.32 5.32a1 1 0 0 1-1.42 1.42l-.66-.66-2.7 2.7 3.06 4.08a1 1 0 0 1-1.48 1.33L9.5 13.14l-3.79 3.79a1 1 0 0 1-1.42-1.42l3.79-3.79-3.24-4.1a1 1 0 0 1 1.31-1.47l4.14 3.11 2.7-2.7-.66-.66a1 1 0 0 1 1.42-1.42Z" />
                              </svg>
                            </button>
                            <button
                              onClick={(event) => startRenamingSession(session, event)}
                              className="session-action-btn"
                              title={t('common.rename')}
                              aria-label={t('common.rename')}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487a2.25 2.25 0 1 1 3.182 3.182L8.25 19.463 4 20l.537-4.25 12.325-11.263Z" />
                              </svg>
                            </button>
                            <button
                              onClick={(e) => handleDeleteSession(session.id, session.title, e)}
                              className="session-action-btn session-delete-btn"
                              title={t('common.delete')}
                              aria-label={t('common.delete')}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
                {groupedSessions.map((group) => (
                  <section key={group.key} className="session-group">
                    <div className="session-group-header">
                      <span>{group.label}</span>
                      <span className="session-group-count">{group.sessions.length}</span>
                    </div>
                    <div className="session-group-list">
                      {group.sessions.map((session) => (
                        <div
                          key={session.id}
                          onClick={() => handleSelectSession(session.id)}
                          onKeyDown={(event) => handleSessionKeyDown(event, session.id)}
                          className={`session-item ${session.id === sessionId ? 'active' : ''}`}
                          role="button"
                          tabIndex={0}
                          aria-label={t('sidebar.openConversation', { title: getDisplayTitle(session) })}
                        >
                          <div className="session-item-main">
                            {renamingSessionId === session.id ? (
                              <input
                                className="session-rename-input"
                                value={renameValue}
                                autoFocus
                                onChange={(event) => setRenameValue(event.target.value)}
                                onClick={(event) => event.stopPropagation()}
                                onBlur={() => void submitSessionRename()}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter') {
                                    event.preventDefault()
                                    void submitSessionRename()
                                  } else if (event.key === 'Escape') {
                                    event.preventDefault()
                                    cancelRenamingSession()
                                  }
                                }}
                              />
                            ) : (
                              <>
                                <span className="session-title">
                                  {getDisplayTitle(session)}
                                  {isAnimating(session.id) && <span className="typing-cursor">|</span>}
                                </span>
                                <div className="session-meta">
                                  {session.id === sessionId && <span className="session-meta-chip is-active">{t('common.active')}</span>}
                                </div>
                              </>
                            )}
                          </div>
                          <div className="session-item-actions">
                            <button
                              onClick={(event) => togglePinnedSession(session.id, event)}
                              className="session-action-btn session-pin-btn"
                              title={t('sidebar.pinConversation')}
                              aria-label={t('sidebar.pinConversation')}
                            >
                              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path d="m11.49 2.19 5.32 5.32a1 1 0 0 1-1.42 1.42l-.66-.66-2.7 2.7 3.06 4.08a1 1 0 0 1-1.48 1.33L9.5 13.14l-3.79 3.79a1 1 0 0 1-1.42-1.42l3.79-3.79-3.24-4.1a1 1 0 0 1 1.31-1.47l4.14 3.11 2.7-2.7-.66-.66a1 1 0 0 1 1.42-1.42Z" />
                              </svg>
                            </button>
                            <button
                              onClick={(event) => startRenamingSession(session, event)}
                              className="session-action-btn"
                              title={t('common.rename')}
                              aria-label={t('common.rename')}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487a2.25 2.25 0 1 1 3.182 3.182L8.25 19.463 4 20l.537-4.25 12.325-11.263Z" />
                              </svg>
                            </button>
                            <button
                              onClick={(e) => handleDeleteSession(session.id, session.title, e)}
                              className="session-action-btn session-delete-btn"
                              title={t('common.delete')}
                              aria-label={t('common.delete')}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}

            {/* Empty state */}
            {!isLoadingSessions && sessions.length === 0 && (
              <div className="text-center text-[var(--sidebar-text-muted)] text-sm py-8">
                <svg className="w-8 h-8 mx-auto mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                {t('sidebar.noConversations')}
              </div>
            )}
          </div>
        </div>
      </nav>

      {currentUser && (
        <div className="sidebar-footer border-t border-[var(--sidebar-border)]">
          <div className="sidebar-account">
            <div className="sidebar-account-avatar" aria-hidden="true">
              {(currentUser.username || currentUser.email || 'U').slice(0, 1).toUpperCase()}
            </div>
            {!collapsed && (
              <div className="sidebar-account-meta">
                <div className="sidebar-account-name">{currentUser.username}</div>
                <div className="sidebar-account-email" title={currentUser.email}>
                  {currentUser.email}
                </div>
              </div>
            )}
            <div className="sidebar-account-actions">
              <button
                type="button"
                onClick={toggleLocale}
                className="sidebar-account-logout"
                title={t('common.localeToggle')}
                aria-label={t('common.localeToggle')}
              >
                <span>{t('common.localeToggle')}</span>
              </button>
              <button
                type="button"
                onClick={onLogout}
                className="sidebar-account-logout"
                title={t('common.signOut')}
                aria-label={t('common.signOut')}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H9m4 4v1a2 2 0 01-2 2H6a2 2 0 01-2-2V7a2 2 0 012-2h5a2 2 0 012 2v1" />
                </svg>
                {!collapsed && <span>{t('common.signOut')}</span>}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="sidebar-delete-overlay" onClick={cancelDeleteSession}>
          <div className="sidebar-delete-dialog" onClick={(event) => event.stopPropagation()}>
            <div className="sidebar-delete-header">
              <div className="sidebar-delete-icon" aria-hidden="true">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <div className="sidebar-delete-header-text">
                <div className="sidebar-delete-title">{t('sidebar.deleteConversationTitle')}</div>
                <div className="sidebar-delete-message">{t('sidebar.deleteConversationMessage')}</div>
              </div>
            </div>
            <div className="sidebar-delete-target">
              <div className="sidebar-delete-target-label">{t('sidebar.conversationLabel')}</div>
              <span className="sidebar-delete-name">"{deleteTarget.title}"</span>
            </div>
            <div className="sidebar-delete-actions">
              <button
                type="button"
                className="sidebar-delete-btn sidebar-delete-btn-cancel"
                onClick={cancelDeleteSession}
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                className="sidebar-delete-btn sidebar-delete-btn-confirm"
                onClick={confirmDeleteSession}
              >
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
