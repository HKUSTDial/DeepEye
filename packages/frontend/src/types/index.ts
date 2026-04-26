// Chat types
export type StepType = 'tool' | 'thought'
export type StepStatus = 'running' | 'completed' | 'error'

export interface ToolStep {
  type: StepType
  name: string
  source: string
  input?: string
  output?: string
  status: StepStatus
  thought?: string
  subSteps?: ToolStep[]
}

export type MessageTimelineItem =
  | { kind: 'step'; step: ToolStep }
  | { kind: 'text'; content: string; isStreaming?: boolean }
  | { kind: 'report_step'; stepIndex: number; totalSteps: number; label: string }

export interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  steps?: ToolStep[]
  timeline?: MessageTimelineItem[]
}

export interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
}

// DataSource types
export interface DataSource {
  id: string
  name: string
  type: string
  category: 'database' | 'file'
  connection_string?: string | null
  storage_path?: string | null
  file_metadata?: Record<string, unknown> | null
  created_at: string
}

export interface DataSourceCreate {
  name: string
  type: string
  connection_string?: string | null
}

export interface DataSourceUpdate {
  name?: string
  type?: string
  connection_string?: string | null
}

export interface DataSourceConnectionTestResponse {
  ok: boolean
  type: string
  table_count: number
  sample_tables: string[]
}

// API types
export interface ChatPayload {
  message: string
  session_id?: string | null
  datasource_ids?: string[]
}

export interface ChatResponse {
  session_id: string
  task_id: string
  message: string
}

// Workflow types
export interface Workflow {
  id: string
  name: string
  description?: string | null
  definition: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface WorkflowRun {
  id: string
  workflow_id?: string | null
  session_id?: string | null
  turn_id?: string | null
  draft_id?: string | null
  source?: string | null
  file_path?: string | null
  status: string
  result?: Record<string, unknown> | null
  artifacts?: WorkflowArtifactPayload[] | null
  error?: string | null
  created_at: string
  finished_at?: string | null
}

export interface ChatTurn {
  id: string
  session_id: string
  user_id: string
  user_message_id?: number | null
  assistant_message_id?: number | null
  status: string
  intent_type?: string | null
  input_text: string
  error?: string | null
  created_at: string
  finished_at?: string | null
}

export interface WorkflowDraft {
  id: string
  session_id: string
  turn_id?: string | null
  user_id: string
  source: string
  status: string
  display_name: string
  file_path?: string | null
  definition: Record<string, unknown>
  version: number
  created_at: string
  updated_at: string
}

export interface WorkflowArtifactPreview {
  type: string
  url?: string
  path?: string
  content_key?: string
  mime_type?: string
  rows?: unknown[]
  columns?: string[]
  [key: string]: unknown
}

export type WorkflowArtifactStatus = 'pending' | 'running' | 'ready' | 'failed' | 'expired'

export interface WorkflowArtifactFile {
  name?: string
  path?: string
  url?: string
  role?: string
  mime_type?: string
  [key: string]: unknown
}

export interface WorkflowArtifactPayload {
  kind: string
  status?: WorkflowArtifactStatus
  title?: string
  summary?: string
  node_id?: string
  preview?: WorkflowArtifactPreview
  files?: WorkflowArtifactFile[]
  payload?: Record<string, unknown>
  [key: string]: unknown
}

export interface WorkflowArtifact {
  id: string
  run_id: string
  session_id?: string | null
  turn_id?: string | null
  draft_id?: string | null
  kind: string
  payload: WorkflowArtifactPayload
  created_at: string
}

export interface WorkspaceState {
  session_id: string
  turn: ChatTurn | null
  draft: WorkflowDraft | null
  run: WorkflowRun | null
  artifacts: WorkflowArtifact[]
}
