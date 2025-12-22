import { ref } from 'vue'
import { useChatStore } from '../stores/chat'

// TODO: Load from env
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001/api'

export function useChat() {
  const store = useChatStore()
  const error = ref<string | null>(null)

  async function sendMessage(text: string, datasourceId?: string) {
    if (!text.trim()) return

    // 1. Add User Message locally
    store.addMessage({ role: 'user', content: text })
    error.value = null

    try {
      // 2. Call Backend to Start Task
      store.isConnecting = true
      
      const payload: any = { 
          message: text,
          session_id: store.sessionId 
      }
      
      // If we have a datasource_id, we need to pass it.
      // But currently the backend /api/chat endpoint accepts ChatRequest(message, session_id).
      // We need to update ChatRequest schema in backend or pass it differently.
      // Wait, we updated AgentInput but not ChatRequest? Let's check backend.
      
      // Actually, ChatRequest in backend/app/api/schemas.py currently only has message and session_id.
      // We need to update ChatRequest to accept datasource_id as well.
      if (datasourceId) {
          payload.datasource_id = datasourceId
      }

      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!res.ok) throw new Error('Failed to send message')

      const data = await res.json()
      store.sessionId = data.session_id // Update/Set Session ID
      
      // Refresh session list to show new chat
      store.fetchSessions()

      // 3. Connect SSE to listen for response
      connectToSSE(data.session_id)

    } catch (e: any) {
      error.value = e.message
      store.isConnecting = false
    }
  }

  function connectToSSE(sessionId: string) {
    // Add a placeholder message for assistant response
    store.addMessage({ role: 'assistant', content: '', isStreaming: true })

    const eventSource = new EventSource(`${API_BASE}/chat/${sessionId}/stream`)

    eventSource.onmessage = (event) => {
      // console.log('SSE Message:', event.data)
      try {
        const payload = JSON.parse(event.data)
        
        switch (payload.type) {
            case 'token':
                store.handleToken(payload.source, payload.content || '')
                break;
                
            case 'tool_start':
                store.handleToolStart(
                    payload.source, 
                    payload.data?.name || 'Unknown Tool', 
                    payload.data?.input || ''
                )
                break;
                
            case 'tool_end':
                store.handleToolEnd(payload.source, payload.data?.output || '')
                break;
                
            case 'agent_end':
                console.log('Agent finished, closing connection')
                eventSource.close()
                store.isConnecting = false
                const lastMsg = store.messages[store.messages.length - 1]
                if (lastMsg) lastMsg.isStreaming = false
                break;
                
            case 'error':
                console.error('SSE Payload Error:', payload)
                error.value = payload.content || "Unknown error"
                eventSource.close()
                store.isConnecting = false
                break;
        }
        
      } catch (e) {
        console.error('SSE Parse Error', e)
      }
    }

    eventSource.onerror = (e) => {
      console.log('SSE Error triggered. ReadyState:', eventSource.readyState)
      
      // If the connection was closed cleanly by our 'done' handler, 
      // eventSource.readyState will be CLOSED (2). We shouldn't treat that as an error.
      if (eventSource.readyState === 2) {
          console.log('SSE connection closed cleanly (readyState=2)')
          return
      }

      console.error('SSE Error Event:', e)
      eventSource.close()
      store.isConnecting = false
      error.value = "Connection lost"
    }
  }

  return {
    sendMessage,
    isConnecting: store.isConnecting,
    error
  }
}

