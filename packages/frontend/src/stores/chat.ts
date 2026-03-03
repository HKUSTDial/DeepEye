import { create } from 'zustand'
import type { Session } from '../types'
import { sandboxApi, sessionApi, type AgentEvent, type StoredMessage } from '../api'
import { useWorkflowStore } from './workflow'
import { SessionChat } from '../models/SessionChat'

interface ChatStore {
  // State
  currentSession: SessionChat | null
  sessions: Session[]
  isLoadingSessions: boolean
  filesChangedTrigger: number
  sandboxReadySessionId: string | null
  isSwitchingSession: boolean
  
  // Derived state (NOT getters, actual state values)
  sessionId: string | null
  messages: ReturnType<SessionChat['messages']['slice']>
  isStreaming: boolean
  
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
  _syncDerivedState: () => void  // Internal helper
}

function convertStoredMessages(stored: StoredMessage[]) {
  return stored.map((m) => ({
    role: m.role,
    content: m.content,
    steps: m.steps,
  }))
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // Initial state
  currentSession: null,
  sessions: [],
  isLoadingSessions: false,
  filesChangedTrigger: 0,
  sandboxReadySessionId: null,
  isSwitchingSession: false,
  
  // Derived state (actual values, NOT getters)
  sessionId: null,
  messages: [],
  isStreaming: false,
  
  // Internal helper to sync derived state
  _syncDerivedState: () => {
    const current = get().currentSession
    set({
      sessionId: current?.id || null,
      messages: current?.messages || [],
      isStreaming: current?.isStreaming || false,
    })
  },
  
  // Actions
  pushEvent: (event) => {
    const current = get().currentSession
    if (current) {
      current.pushEvent(event)
      set({ currentSession: current })
      get()._syncDerivedState()
    }
  },
  
  addUserMessage: (content) => {
    const current = get().currentSession
    if (current) {
      current.addUserMessage(content)
      set({ currentSession: current })
      get()._syncDerivedState()
    }
  },
  
  startStreaming: () => {
    const current = get().currentSession
    if (current) {
      current.startStreaming()
      set({ currentSession: current })
      get()._syncDerivedState()
    }
  },
  
  stopStreaming: () => {
    const current = get().currentSession
    if (current) {
      current.stopStreaming()
      set({ currentSession: current })
      get()._syncDerivedState()
    }
  },
  
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
      get()._syncDerivedState()
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
    get()._syncDerivedState()
    return sessionChat
  },
  
  deleteSession: async (id) => {
    try {
      await sessionApi.delete(id)
      const sessions = get().sessions.filter((s) => s.id !== id)
      set({ sessions })
      if (get().currentSession?.id === id) {
        set({ currentSession: null })
        get()._syncDerivedState()
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
      const current = get().currentSession
      if (current?.id === id) {
        current.title = updated.title
        set({ currentSession: current })
        get()._syncDerivedState()
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
      useWorkflowStore.getState().reset()
      // 1. Get session details from backend
      const sessionInfo = await sessionApi.get(id)
      const session = new SessionChat(sessionInfo.id, sessionInfo.title)
      
      // 2. Load messages
      const { messages: storedMessages } = await sessionApi.getMessages(id)
      session.loadMessages(convertStoredMessages(storedMessages))
      
      set({ currentSession: session })
      get()._syncDerivedState()

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

