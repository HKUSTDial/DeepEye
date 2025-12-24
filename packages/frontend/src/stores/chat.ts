import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, ToolStep, Session } from '../types'
import { sessionApi, type AgentEvent, type StoredMessage } from '../api'

/**
 * Chat Store
 *
 * - Streaming: uses reduceStreamEvents() to build messages from real-time events
 * - History: loads pre-built messages directly from backend
 */
export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const streamEvents = ref<AgentEvent[]>([])  // Events for current streaming session only
  const sessionId = ref<string | null>(null)
  const isStreaming = ref(false)
  const sessions = ref<Session[]>([])
  const isLoadingSessions = ref(false)

  // ============ Convert stored messages to UI Message format ============

  function convertStoredMessages(stored: StoredMessage[]): Message[] {
    // Backend now stores in the same structure as frontend Message
    return stored.map((m) => ({
      role: m.role,
      content: m.content,
      steps: m.steps,
    }))
  }

  // ============ Streaming: Event → Message (real-time only) ============

  function reduceStreamEvents(eventList: AgentEvent[]): Message[] {
    const result: Message[] = []
    let current: Message | null = null
    let stepStack: ToolStep[] = []

    for (const e of eventList) {
      const { type, source, content = '', data = {} } = e

      if (type === 'agent_start') {
        if (current) result.push(current)
        current = { role: 'assistant', content: '', steps: [] }
        stepStack = []
      }
      else if (type === 'token' && current) {
        if (source === 'supervisor') {
          current.content += content
        } else if (stepStack.length > 0) {
          const step = stepStack[stepStack.length - 1]!
          const subs = step.subSteps ??= []
          const last = subs[subs.length - 1]
          if (last?.type === 'thought') {
            last.thought = (last.thought || '') + content
          } else {
            subs.push({ type: 'thought', name: 'Thinking', source, thought: content, status: 'completed', subSteps: [] })
          }
        }
      }
      else if (type === 'tool_start' && current) {
        const step: ToolStep = { type: 'tool', name: String(data.name || ''), source, input: String(data.input || ''), status: 'completed', subSteps: [] }
        if (source === 'supervisor') {
          current.steps!.push(step)
          stepStack = [step]
        } else if (stepStack.length > 0) {
          stepStack[stepStack.length - 1]!.subSteps!.push(step)
          stepStack.push(step)
        } else {
          current.steps!.push(step)
          stepStack = [step]
        }
      }
      else if (type === 'tool_end' && current) {
        const rawOutput = data.output as unknown
        const output = typeof rawOutput === 'object' && rawOutput && 'content' in rawOutput ? String((rawOutput as { content: unknown }).content) : String(rawOutput || '')
        if (source === 'supervisor' && stepStack.length > 0) {
          stepStack[stepStack.length - 1]!.output = output
          if (stepStack.length > 1) stepStack.pop()
        } else if (stepStack.length > 0) {
          for (let i = stepStack.length - 1; i >= 0; i--) {
            const s = stepStack[i]!
            if (s.source === source) {
              s.output = output
              stepStack = stepStack.slice(0, i)
              break
            }
          }
        }
      }
      else if (type === 'agent_end' || type === 'error') {
        if (current) result.push(current)
        current = null
        stepStack = []
      }
    }

    if (current) result.push(current)
    return result
  }

  // ============ State Management ============

  function rebuildStreamingMessages() {
    // Keep existing messages, append streaming assistant message
    const streamingMsgs = reduceStreamEvents(streamEvents.value)
    const lastStreaming = streamingMsgs[streamingMsgs.length - 1]
    if (lastStreaming) {
      lastStreaming.isStreaming = true
      // Remove any previous streaming message and append new one
      const baseMessages = messages.value.filter((m) => !m.isStreaming)
      messages.value = [...baseMessages, lastStreaming]
    }
  }

  function pushEvent(event: AgentEvent) {
    streamEvents.value.push(event)
    rebuildStreamingMessages()
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

  function createSession() {
    sessionId.value = null
    streamEvents.value = []
    messages.value = []
  }

  async function deleteSession(id: string) {
    try {
      await sessionApi.delete(id)
      sessions.value = sessions.value.filter((s) => s.id !== id)
      if (sessionId.value === id) createSession()
    } catch (e) {
      console.error('Failed to delete session', e)
    }
  }

  async function selectSession(id: string) {
    if (sessionId.value === id) return
    sessionId.value = id
    isStreaming.value = false
    streamEvents.value = []
    try {
      const { messages: storedMessages } = await sessionApi.getMessages(id)
      messages.value = convertStoredMessages(storedMessages)
    } catch (e) {
      console.error('Failed to load messages', e)
      messages.value = []
    }
  }

  // ============ Streaming Control ============

  function startStreaming() {
    isStreaming.value = true
    streamEvents.value = []
  }

  function stopStreaming() {
    isStreaming.value = false
    // Mark last message as not streaming
    const last = messages.value[messages.value.length - 1]
    if (last?.isStreaming) last.isStreaming = false
    streamEvents.value = []
  }

  function addUserMessage(content: string) {
    messages.value.push({ role: 'user', content })
  }

  return {
    messages,
    sessionId,
    isStreaming,
    sessions,
    isLoadingSessions,
    pushEvent,
    addUserMessage,
    startStreaming,
    stopStreaming,
    fetchSessions,
    createSession,
    selectSession,
    deleteSession,
  }
})
