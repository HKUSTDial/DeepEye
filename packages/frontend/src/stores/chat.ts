import { create } from 'zustand'
import type { Message, Session } from '../types'
import { sandboxApi, sessionApi, type AgentEvent, type StoredMessage } from '../api'
import { SessionChat } from '../models/SessionChat'

export interface ChatStore {
  // State
  currentSession: SessionChat | null
  sessions: Session[]
  isLoadingSessions: boolean
  filesChangedTrigger: number
  sandboxReadySessionId: string | null
  isSwitchingSession: boolean

  // Actions
  pushEvent: (event: AgentEvent) => void
  addUserMessage: (content: string) => void
  startStreaming: () => void
  stopStreaming: () => void
  fetchSessions: () => Promise<void>
  createSession: () => Promise<SessionChat | null>
  createDraftSession: () => SessionChat
  selectSession: (id: string) => Promise<void>
  deleteSession: (id: string) => Promise<void>
  updateSessionTitle: (id: string, title: string) => Promise<void>
  notifyFilesChanged: () => void
  setSandboxReady: (sessionId: string | null) => void
  resetSandboxSignals: () => void
}

export const EMPTY_CHAT_MESSAGES: Message[] = []

export const selectCurrentSessionId = (state: ChatStore) => state.currentSession?.id ?? null
export const selectCurrentMessages = (state: ChatStore) =>
  state.currentSession?.messages ?? EMPTY_CHAT_MESSAGES
export const selectIsStreaming = (state: ChatStore) => state.currentSession?.isStreaming ?? false

function convertStoredMessages(stored: StoredMessage[]) {
  return stored.map((m) => ({
    role: m.role,
    content: m.content,
    steps: m.steps,
  }))
}

function updateCurrentSession(
  get: () => ChatStore,
  set: (
    partial:
      | Partial<ChatStore>
      | ((state: ChatStore) => Partial<ChatStore> | ChatStore),
  ) => void,
  updater: (session: SessionChat) => void,
) {
  const current = get().currentSession
  if (!current) {
    return
  }

  const next = current.clone()
  updater(next)
  set({ currentSession: next })
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // Initial state
  currentSession: null,
  sessions: [],
  isLoadingSessions: false,
  filesChangedTrigger: 0,
  sandboxReadySessionId: null,
  isSwitchingSession: false,

  // Actions
  pushEvent: (event) => updateCurrentSession(get, set, (session) => session.pushEvent(event)),

  addUserMessage: (content) =>
    updateCurrentSession(get, set, (session) => session.addUserMessage(content)),

  startStreaming: () => updateCurrentSession(get, set, (session) => session.startStreaming()),

  stopStreaming: () => updateCurrentSession(get, set, (session) => session.stopStreaming()),

  fetchSessions: async () => {
    set({ isLoadingSessions: true })
    try {
      const sessions = await sessionApi.list()
      set({ sessions })
    } catch (e) {
      console.error('Failed to fetch sessions', e)
    } finally {
      set({ isLoadingSessions: false })
    }
  },
  
  createSession: async () => {
    try {
      const newSession = await sessionApi.create()
      const sessionChat = new SessionChat(newSession.id, newSession.title)
      set({ currentSession: sessionChat })
      await get().fetchSessions() // Refresh session list
      return sessionChat
    } catch (e) {
      console.error('Failed to create session', e)
      return null
    }
  },

  createDraftSession: () => {
    const sessionChat = new SessionChat('draft', 'New conversation', true)
    set({ currentSession: sessionChat })
    return sessionChat
  },
  
  deleteSession: async (id) => {
    try {
      await sessionApi.delete(id)
      const sessions = get().sessions.filter((s) => s.id !== id)
      set({ sessions })
      if (get().currentSession?.id === id) {
        set({ currentSession: null })
        get().createDraftSession()
      }
    } catch (e) {
      console.error('Failed to delete session', e)
    }
  },
  
  updateSessionTitle: async (id, title) => {
    try {
      const updated = await sessionApi.update(id, title)
      // Update in sessions list
      const sessions = get().sessions.map((s) => (s.id === id ? updated : s))
      set({ sessions })
      // Update current session if it's the same
      if (get().currentSession?.id === id) {
        updateCurrentSession(get, set, (session) => {
          session.title = updated.title
        })
      }
    } catch (e) {
      console.error('Failed to update session title', e)
    }
  },
  
  selectSession: async (id) => {
    if (get().currentSession?.id === id) return
    
    try {
      set({ isSwitchingSession: true })
      get().resetSandboxSignals()
      // 1. Get session details from backend
      const sessionInfo = await sessionApi.get(id)
      const session = new SessionChat(sessionInfo.id, sessionInfo.title)
      
      // 2. Load messages
      const { messages: storedMessages } = await sessionApi.getMessages(id)
      session.loadMessages(convertStoredMessages(storedMessages))
      
      set({ currentSession: session })

      const hasChatHistory = storedMessages.some(
        (message) => message.role === 'user' || message.role === 'assistant',
      )
      if (hasChatHistory) {
        try {
          await sandboxApi.startSession(id)
          get().setSandboxReady(id)
          get().notifyFilesChanged()
        } catch (e) {
          console.error('Failed to start sandbox', e)
        }
      }
      set({ isSwitchingSession: false })
    } catch (e) {
      const isAbort = e instanceof Error && e.name === 'AbortError'
      if (isAbort) {
        console.warn('Load session was cancelled (e.g. switched session or request timed out).')
      } else {
        console.error('Failed to load session', e)
      }
      set({ isSwitchingSession: false })
    }
  },
  
  notifyFilesChanged: () => {
    set({ filesChangedTrigger: get().filesChangedTrigger + 1 })
  },
  
  setSandboxReady: (sessionId) => {
    set({ sandboxReadySessionId: sessionId })
  },

  resetSandboxSignals: () => {
    set({ filesChangedTrigger: 0, sandboxReadySessionId: null })
  },
}))
