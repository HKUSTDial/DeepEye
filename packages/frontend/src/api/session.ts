import type { Session } from '../types'
import { http } from './client'

/**
 * Agent event from backend (same structure for real-time and history).
 * This is the single source of truth for UI rendering.
 */
export interface AgentEvent {
  type: 'user_message' | 'token' | 'tool_start' | 'tool_end' | 'tool_error' | 'agent_start' | 'agent_end' | 'agent_thought' | 'error'
  source: string
  content?: string
  data?: Record<string, unknown>
}

export const sessionApi = {
  list: () => http.get<Session[]>('/sessions'),
  get: (id: string) => http.get<Session>(`/sessions/${id}`),
  delete: (id: string) => http.delete<void>(`/sessions/${id}`),
  getHistory: (id: string) => http.get<{ events: AgentEvent[] }>(`/sessions/${id}/history`),
}

