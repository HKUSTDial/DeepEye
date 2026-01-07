import { ref } from 'vue'
import { useChatStore } from '../stores/chat'
import { chatApi, type AgentEvent } from '../api'

/**
 * Chat composable - handles SSE connection and message sending.
 * All events flow through store.pushEvent() which uses the same
 * reduceEvents() pure function as history replay.
 */
export function useChat() {
  const store = useChatStore()
  const error = ref<string | null>(null)

  function connectToSSE(sessionId: string) {
    const es = chatApi.createEventSource(sessionId)

    es.onmessage = (event) => {
      try {
        const agentEvent: AgentEvent = JSON.parse(event.data)
        
        // Handle sandbox events
        if (agentEvent.type === 'sandbox_started') {
          store.notifySandboxStarted()
          return
        }
        if (agentEvent.type === 'sandbox_files_changed') {
          store.notifyFilesChanged()
          return
        }
        
        store.pushEvent(agentEvent)

        if (agentEvent.type === 'agent_end' || agentEvent.type === 'error') {
          es.close()
          store.stopStreaming()
          if (agentEvent.type === 'error') {
            error.value = agentEvent.content || 'Unknown error'
          }
        }
      } catch (e) {
        console.error('SSE parse error', e)
      }
    }

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return
      es.close()
      store.stopStreaming()
      error.value = 'Connection lost'
    }
  }

  async function sendMessage(text: string, datasourceId?: string) {
    if (!text.trim()) return

    error.value = null
    
    // Ensure we have a session (create if needed)
    if (!store.currentSession) {
      await store.createSession()
    }
    
    // Now we must have a session_id
    const session_id = store.sessionId
    if (!session_id) {
      error.value = 'Failed to create session'
      return
    }
    
    // Check if this is the first message (for title update)
    const isFirstMessage = store.messages.length === 0
    
    store.startStreaming()
    store.addUserMessage(text)

    try {
      // Send message with session_id from backend
      await chatApi.start({
        message: text,
        session_id: session_id,
        datasource_id: datasourceId,
      })

      // Update session title with first message content
      if (isFirstMessage) {
        const title = text.length > 50 ? text.substring(0, 47) + '...' : text
        await store.updateSessionTitle(session_id, title)
      }

      store.fetchSessions()
      connectToSSE(session_id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to send'
      store.stopStreaming()
    }
  }

  return { sendMessage, error }
}
