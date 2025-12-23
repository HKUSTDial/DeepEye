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
    store.startStreaming()
    store.addUserMessage(text)

    try {
      const { session_id } = await chatApi.start({
        message: text,
        session_id: store.sessionId,
        datasource_id: datasourceId,
      })

      store.sessionId = session_id
      store.fetchSessions()
      connectToSSE(session_id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to send'
      store.stopStreaming()
    }
  }

  return { sendMessage, error }
}
