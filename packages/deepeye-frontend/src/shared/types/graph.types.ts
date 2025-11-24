import { Node, Edge, Viewport } from 'reactflow'

export interface NodeHistoryEntry {
  id: string
  timestamp: number
  type: 'ai_request' | 'compute' | 'manual'
  inputs: Record<string, any>
  outputs: Record<string, any>
  config: Record<string, any>
  prompt?: string
  modelId?: string
  success: boolean
  error?: string
}

export interface GraphState {
  nodes: Node[]
  edges: Edge[]
  viewport: Viewport
  timestamp: number
}

export interface Selection {
  nodes: string[]
  edges: string[]
}

