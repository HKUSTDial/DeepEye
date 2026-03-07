import { http } from './client'

export type NodeSpecPort = {
  schema?: string | Record<string, unknown> | null
  required?: boolean
  multiple?: boolean
  description?: string | null
}

export type NodeSpec = {
  type: string
  version?: string
  description?: string | null
  params_schema?: Record<string, unknown> | null
  inputs?: Record<string, NodeSpecPort>
  outputs?: Record<string, NodeSpecPort>
}

export const workflowNodesApi = {
  list: () => http.get<NodeSpec[]>('/workflow-nodes'),
}
