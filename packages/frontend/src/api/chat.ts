import type { ChatPayload, ChatResponse } from '../types'
import { http, API_BASE } from './client'

export const chatApi = {
  start: (payload: ChatPayload) => http.post<ChatResponse>('/chat', payload),

  createEventSource: (sessionId: string) => {
    // Support relative paths (e.g. /api/v1) for VITE_API_URL
    const url = new URL(
      `${API_BASE}/chat/${sessionId}/stream`,
      window.location.origin
    )
    // Auth uses cookie/header; avoid leaking token via URL query.
    return new EventSource(url, { withCredentials: true })
  },
}
