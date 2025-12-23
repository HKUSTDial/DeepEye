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

export interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  steps?: ToolStep[]
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
  connection_string: string
  created_at: string
}

export interface DataSourceCreate {
  name: string
  type: string
  connection_string: string
}

// API types
export interface ChatPayload {
  message: string
  session_id?: string | null
  datasource_id?: string
}

export interface ChatResponse {
  session_id: string
  task_id: string
  message: string
}

