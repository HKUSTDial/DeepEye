import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, ToolStep, Session } from '../types'
import { sessionApi, type AgentEvent } from '../api'

/**
 * Event-Sourced Chat Store
 *
 * Core principle: `reduceEvents()` is a PURE FUNCTION that converts
 * an event stream into messages. Both streaming and history use it.
 */
export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const events = ref<AgentEvent[]>([])  // Raw event stream
  const sessionId = ref<string | null>(null)
  const isStreaming = ref(false)
  const sessions = ref<Session[]>([])
  const isLoadingSessions = ref(false)

  // ============ Pure Function: Event → Message ============

  function reduceEvents(eventList: AgentEvent[]): Message[] {
    const result: Message[] = []
    let current: Message | null = null
    let stepStack: ToolStep[] = []

    for (const e of eventList) {
      const { type, source, content = '', data = {} } = e

      if (type === 'user_message') {
        if (current) result.push(current)
        result.push({ role: 'user', content })
        current = null
        stepStack = []
      }
      else if (type === 'agent_start') {
        if (current) result.push(current)
        current = { role: 'assistant', content: '', steps: [] }
        stepStack = []
      }
      else if (type === 'token' && current) {
        if (source === 'supervisor') {
          current.content += content
        } else if (stepStack.length) {
          const step = stepStack[stepStack.length - 1]
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
        } else if (stepStack.length) {
          stepStack[stepStack.length - 1].subSteps!.push(step)
          stepStack.push(step)
        } else {
          current.steps!.push(step)
          stepStack = [step]
        }
      }
      else if (type === 'tool_end' && current) {
        // output may be string or object with .content
        const rawOutput = data.output as unknown
        const output = typeof rawOutput === 'object' && rawOutput && 'content' in rawOutput ? String((rawOutput as { content: unknown }).content) : String(rawOutput || '')
        if (source === 'supervisor' && stepStack.length) {
          stepStack[stepStack.length - 1].output = output
          if (stepStack.length > 1) stepStack.pop()
        } else if (stepStack.length) {
          for (let i = stepStack.length - 1; i >= 0; i--) {
            if (stepStack[i].source === source) {
              stepStack[i].output = output
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

  function rebuildMessages() {
    messages.value = reduceEvents(events.value)
    // Mark last assistant message as streaming if active
    if (isStreaming.value) {
      const last = messages.value[messages.value.length - 1]
      if (last?.role === 'assistant') last.isStreaming = true
    }
  }

  function pushEvent(event: AgentEvent) {
    events.value.push(event)
    rebuildMessages()
  }

  function setEvents(eventList: AgentEvent[]) {
    events.value = eventList
    rebuildMessages()
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
    events.value = []
    messages.value = []
  }

  async function deleteSession(id: string) {
    try {
      await sessionApi.delete(id)
      sessions.value = sessions.value.filter(s => s.id !== id)
      if (sessionId.value === id) createSession()
    } catch (e) {
      console.error('Failed to delete session', e)
    }
  }

  async function selectSession(id: string) {
    if (sessionId.value === id) return
    sessionId.value = id
    isStreaming.value = false
    try {
      const { events: historyEvents } = await sessionApi.getHistory(id)
      setEvents(historyEvents)
    } catch (e) {
      console.error('Failed to load history', e)
      events.value = []
      messages.value = []
    }
  }

  // ============ Streaming Control ============

  function startStreaming() {
    isStreaming.value = true
  }

  function stopStreaming() {
    isStreaming.value = false
    rebuildMessages()
  }

  function addUserMessage(content: string) {
    pushEvent({ type: 'user_message', source: 'user', content })
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
