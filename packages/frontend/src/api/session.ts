import type { Session, ToolStep } from '../types'
import { http } from './client'

/**
 * Agent event from backend for real-time streaming.
 */
export interface AgentEvent {
  type: 'token' | 'tool_start' | 'tool_end' | 'tool_error' | 'agent_start' | 'agent_end' | 'error'
  source: string
  content?: string
  data?: Record<string, unknown>
}

/**
 * Stored message format from backend (matches frontend Message/ToolStep structure).
 */
export interface StoredMessage {
  role: 'user' | 'assistant'
  content: string
  steps?: ToolStep[]
}

export const sessionApi = {
  list: () => http.get<Session[]>('/sessions'),
  get: (id: string) => http.get<Session>(`/sessions/${id}`),
  delete: (id: string) => http.delete<void>(`/sessions/${id}`),
  getMessages: (id: string) => http.get<{ messages: StoredMessage[] }>(`/sessions/${id}/messages`),
}

