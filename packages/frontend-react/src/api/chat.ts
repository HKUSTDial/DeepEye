import type { ChatPayload, ChatResponse } from '../types'
import { http, API_BASE } from './client'
import { useAuthStore } from '../stores/auth'

export const chatApi = {
  start: (payload: ChatPayload) => http.post<ChatResponse>('/chat', payload),

  createEventSource: (sessionId: string) => {
    const token = useAuthStore.getState().accessToken
    // Support relative paths (e.g. /api/v1) for VITE_API_URL
    const url = new URL(
      `${API_BASE}/chat/${sessionId}/stream`,
      window.location.origin
    )
    if (token) {
      url.searchParams.set('token', token)
    }
    return new EventSource(url)
  },
}

