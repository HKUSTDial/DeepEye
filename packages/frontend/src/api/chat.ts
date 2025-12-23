import type { ChatPayload, ChatResponse } from '../types'
import { http, API_BASE } from './client'

export const chatApi = {
  start: (payload: ChatPayload) => http.post<ChatResponse>('/chat', payload),

  createEventSource: (sessionId: string) => new EventSource(`${API_BASE}/chat/${sessionId}/stream`),
}

