import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message, ToolStep, Session } from '../types/chat'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const sessionId = ref<string | null>(null)
  const isConnecting = ref(false)
  const sessions = ref<Session[]>([])
  const isLoadingSessions = ref(false)

  // --- Session Management ---

  async function fetchSessions() {
    isLoadingSessions.value = true
    try {
      const res = await fetch(`${API_BASE}/sessions`)
      if (res.ok) {
        sessions.value = await res.json()
      }
    } catch (e) {
      console.error("Failed to fetch sessions", e)
    } finally {
      isLoadingSessions.value = false
    }
  }

  async function createSession() {
    // Clear current state to start fresh
    sessionId.value = null
    messages.value = []
    // We don't necessarily create it on backend until first message, 
    // OR we can explicitly create it.
    // The current backend creates on first message if ID is new.
    // We'll let the first message creation handle the persistence,
    // but visually we are in a "New Chat" state.
  }

  async function deleteSession(id: string) {
      try {
          await fetch(`${API_BASE}/sessions/${id}`, { method: 'DELETE' })
          sessions.value = sessions.value.filter(s => s.id !== id)
          if (sessionId.value === id) {
              createSession()
          }
      } catch (e) {
          console.error("Failed to delete session", e)
      }
  }

  async function selectSession(id: string) {
      if (sessionId.value === id) return
      
      sessionId.value = id
      isConnecting.value = false
      messages.value = [] // Clear current messages
      
      // Load History
      try {
          const res = await fetch(`${API_BASE}/sessions/${id}/history`)
          if (res.ok) {
              const data = await res.json()
              // Transform history to Message[]
              // Backend returns { messages: [{role, content, ...}] }
              // We need to adapt it. 
              // TODO: Handle Tool steps structure if possible.
              // For now, flat mapping.
              messages.value = data.messages.map((m: any) => ({
                  role: (m.role === 'user' || m.role === 'assistant') ? m.role : 'user',
                  content: m.content || '',
                  steps: []
              }))
          } else {
             console.error("Failed to load history, status:", res.status)
          }
      } catch (e) {
          console.error("Failed to load history", e)
      }
  }

  // --- Message Handling ---

  function addMessage(msg: Message) {
    messages.value.push(msg)
  }

  function appendToLastMessage(content: string) {
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.content += content
    }
  }
  
  // --- Advanced Recursive Step Management ---

  function getLastAssistantMessage(): Message | null {
      const lastMsg = messages.value[messages.value.length - 1]
      return (lastMsg && lastMsg.role === 'assistant') ? lastMsg : null
  }

  function handleToken(source: string, content: string) {
      const msg = getLastAssistantMessage()
      if (!msg) return

      if (source === 'supervisor') {
          // Supervisor thinking -> Main Content
          msg.content += content
      } else {
          // Sub-Agent thinking -> Should be a Thought Step
          const activeStep = findActiveParentStep(msg.steps || [])
          
          if (activeStep) {
              // Check if the last sub-step is an active thought
              if (!activeStep.subSteps) activeStep.subSteps = []
              const lastSub = activeStep.subSteps[activeStep.subSteps.length - 1]
              
              if (lastSub && lastSub.type === 'thought' && lastSub.status === 'running') {
                  lastSub.thought = (lastSub.thought || "") + content
              } else {
                  // Create new thought step
                  activeStep.subSteps.push({
                      type: 'thought',
                      name: 'Thinking',
                      source: source,
                      thought: content,
                      status: 'running',
                      subSteps: []
                  })
              }
          }
      }
  }

  function handleToolStart(source: string, name: string, input: string) {
      const msg = getLastAssistantMessage()
      if (!msg) return

      const newStep: ToolStep = {
          type: 'tool',
          name,
          source,
          input,
          status: 'running',
          subSteps: []
      }

      if (source === 'supervisor') {
          // Top-level tool call
          if (!msg.steps) msg.steps = []
          msg.steps.push(newStep)
      } else {
          // Nested tool call (Sub-Agent calling a tool)
          const parentStep = findActiveParentStep(msg.steps || [])
          
          if (parentStep) {
              // Close previous thought if running
              if (parentStep.subSteps) {
                  const lastSub = parentStep.subSteps[parentStep.subSteps.length - 1]
                  if (lastSub && lastSub.type === 'thought') {
                      lastSub.status = 'completed'
                  }
              } else {
                  parentStep.subSteps = []
              }
              parentStep.subSteps.push(newStep)
          } else {
              // Fallback
              if (!msg.steps) msg.steps = []
              msg.steps.push(newStep)
          }
      }
  }

  function handleToolEnd(source: string, output: string) {
      const msg = getLastAssistantMessage()
      if (!msg || !msg.steps) return
      
      const steps = msg.steps

      if (source === 'supervisor') {
          // Closing a top-level tool
          const lastStep = steps[steps.length - 1]
          if (lastStep && lastStep.status === 'running') {
              lastStep.output = output
              lastStep.status = 'completed'
          }
      } else {
          // Closing a nested tool
          const parentStep = findActiveParentStep(steps)
          if (parentStep && parentStep.subSteps) {
              // Find the last running TOOL step (skip thoughts)
              // Actually, simpler: find the last sub-step. If it's a tool, close it.
              const lastSubStep = parentStep.subSteps[parentStep.subSteps.length - 1]
              if (lastSubStep && lastSubStep.type === 'tool' && lastSubStep.status === 'running') {
                  lastSubStep.output = output
                  lastSubStep.status = 'completed'
              }
          }
      }
  }

  // Helper to find the deepest active step that acts as a container (i.e. a running Tool)
  // Logic: We want the step that "contains" the current activity.
  // - Top level steps are container candidates.
  // - If a top level step is running, it might contain sub-steps.
  function findActiveParentStep(steps: ToolStep[]): ToolStep | null {
      if (!steps || steps.length === 0) return null
      
      const lastStep = steps[steps.length - 1]
      if (!lastStep) return null
      
      // If the last step is completed, it cannot accept children.
      if (lastStep.status === 'completed') return null
      
      // If the last step is a 'thought', it generally doesn't contain sub-steps (in our current model).
      // But if we had recursive thoughts... no, thoughts are leaf nodes usually.
      // So we return this step because it IS the parent we are looking for (e.g. the "ask_database" tool).
      
      // Check if this step has running sub-steps that act as parents?
      // Currently we only have 1 level of nesting (Supervisor -> Agent -> Tool).
      // So "ask_database" is the parent.
      
      return lastStep
  }

  return {
    messages,
    sessionId,
    isConnecting,
    sessions,
    isLoadingSessions,
    addMessage,
    appendToLastMessage,
    handleToken,
    handleToolStart,
    handleToolEnd,
    fetchSessions,
    createSession,
    selectSession,
    deleteSession
  }
})
