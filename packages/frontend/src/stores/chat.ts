import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session } from '../types'
import { sessionApi, type AgentEvent, type StoredMessage } from '../api'
import { SessionChat } from '../models/SessionChat'

/**
 * Chat Store
 *
 * Uses SessionChat class to manage individual chat sessions.
 * Each session has its own state encapsulated in SessionChat instance.
 */
export const useChatStore = defineStore('chat', () => {
  // Active session instance
  const currentSession = ref<SessionChat | null>(null)
  
  // Session list from backend
  const sessions = ref<Session[]>([])
  const isLoadingSessions = ref(false)
  
  // File refresh trigger - increments when sandbox files change
  const filesChangedTrigger = ref(0)
  
  // Sandbox started trigger - increments when sandbox starts
  const sandboxStartedTrigger = ref(0)
  
  // Computed properties for backwards compatibility
  const sessionId = computed(() => currentSession.value?.id || null)
  const messages = computed(() => currentSession.value?.messages || [])
  const isStreaming = computed(() => currentSession.value?.isStreaming || false)

  // ============ Helper Functions ============

  function convertStoredMessages(stored: StoredMessage[]) {
    return stored.map((m) => ({
      role: m.role,
      content: m.content,
      steps: m.steps,
    }))
  }

  function pushEvent(event: AgentEvent) {
    if (currentSession.value) {
      currentSession.value.pushEvent(event)
    }
  }

  // ============ Session Management ============

  async function fetchSessions() {
    isLoadingSessions.value = true
    try {
      sessions.value = await sessionApi.list()
    } catch (e) {
      console.error('Failed to fetch sessions', e)
    } finally {
      isLoadingSessions.value = false
    }
  }

  /**
   * Create a new session by calling backend API
   */
  async function createSession() {
    try {
      const newSession = await sessionApi.create()
      currentSession.value = new SessionChat(newSession.id, newSession.title)
      await fetchSessions() // Refresh session list
    } catch (e) {
      console.error('Failed to create session', e)
    }
  }

  /**
   * Delete a session
   */
  async function deleteSession(id: string) {
    try {
      await sessionApi.delete(id)
      sessions.value = sessions.value.filter((s) => s.id !== id)
      if (currentSession.value?.id === id) {
        await createSession()  // 等待新 session 创建完成
      }
    } catch (e) {
      console.error('Failed to delete session', e)
    }
  }

  /**
   * Update session title
   */
  async function updateSessionTitle(id: string, title: string) {
    try {
      const updated = await sessionApi.update(id, title)
      // Update in sessions list
      const idx = sessions.value.findIndex((s) => s.id === id)
      if (idx !== -1) {
        sessions.value[idx] = updated
      }
      // Update current session if it's the same
      if (currentSession.value?.id === id) {
        currentSession.value.title = updated.title
      }
    } catch (e) {
      console.error('Failed to update session title', e)
    }
  }

  /**
   * Select an existing session and load its history
   */
  async function selectSession(id: string) {
    if (currentSession.value?.id === id) return
    
    try {
      // 1. Get session details from backend
      const sessionInfo = await sessionApi.get(id)
      const session = new SessionChat(sessionInfo.id, sessionInfo.title)
      
      // 2. Load messages
      const { messages: storedMessages } = await sessionApi.getMessages(id)
      session.loadMessages(convertStoredMessages(storedMessages))
      
      currentSession.value = session
    } catch (e) {
      console.error('Failed to load session', e)
    }
  }

  // ============ Streaming Control ============

  function startStreaming() {
    if (currentSession.value) {
      currentSession.value.startStreaming()
    }
  }

  function stopStreaming() {
    if (currentSession.value) {
      currentSession.value.stopStreaming()
    }
  }

  function addUserMessage(content: string) {
    if (currentSession.value) {
      currentSession.value.addUserMessage(content)
    }
  }

  function notifyFilesChanged() {
    filesChangedTrigger.value++
  }

  function notifySandboxStarted() {
    sandboxStartedTrigger.value++
  }

  return {
    // State
    currentSession,
    sessions,
    isLoadingSessions,
    filesChangedTrigger,
    sandboxStartedTrigger,
    // Computed (backwards compatible)
    sessionId,
    messages,
    isStreaming,
    // Methods
    pushEvent,
    addUserMessage,
    startStreaming,
    stopStreaming,
    fetchSessions,
    createSession,
    selectSession,
    deleteSession,
    updateSessionTitle,
    notifyFilesChanged,
    notifySandboxStarted,
  }
})
