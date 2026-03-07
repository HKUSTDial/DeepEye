import type { DataSource, Session, ToolStep, WorkspaceState } from '../types'
import { http } from './client'

/**
 * Agent event types
 */
export type AgentEventType =
  | 'token'
  | 'tool_start'
  | 'tool_end'
  | 'tool_error'
  | 'agent_start'
  | 'agent_end'
  | 'error'
  | 'workflow_event'
  | 'report_step'
  | 'report_done'

/**
 * Sandbox event types
 */
export type SandboxEventType = 'sandbox_started' | 'sandbox_files_changed' | 'sandbox_command_success' | 'sandbox_command_error'

/**
 * Event from backend for real-time streaming.
 */
export interface AgentEvent {
  type: AgentEventType | SandboxEventType
  source: string
  content?: string
  data?: Record<string, unknown> & { report_html?: string; steps?: string[] }
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
  create: (title?: string) => http.post<Session>('/sessions', { title: title || 'New conversation' }),
  list: () => http.get<Session[]>('/sessions'),
  get: (id: string) => http.get<Session>(`/sessions/${id}`),
  update: (id: string, title: string) => http.patch<Session>(`/sessions/${id}`, { title }),
  delete: (id: string) => http.delete<void>(`/sessions/${id}`),
  getMessages: (id: string) => http.get<{ messages: StoredMessage[] }>(`/sessions/${id}/messages`),
  listAttachments: (id: string) => http.get<DataSource[]>(`/sessions/${id}/attachments`),
  getWorkspaceState: (id: string) => http.get<WorkspaceState>(`/sessions/${id}/workspace-state`),
  attachDatasource: (sessionId: string, datasourceId: string) =>
    http.post<DataSource>(`/sessions/${sessionId}/attachments/${datasourceId}`),
  detachDatasource: (sessionId: string, datasourceId: string) =>
    http.delete<void>(`/sessions/${sessionId}/attachments/${datasourceId}`),
}
