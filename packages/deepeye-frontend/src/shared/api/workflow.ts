/**
 * 工作流 API
 * 
 * 对接后端工作流接口：
 * - GET /api/v1/workflows - 列出工作流
 * - POST /api/v1/workflows - 创建工作流
 * - GET /api/v1/workflows/{id} - 获取工作流
 * - PUT /api/v1/workflows/{id} - 更新工作流
 * - DELETE /api/v1/workflows/{id} - 删除工作流
 */

import { apiClient } from './client'
import { Node, Edge, Viewport } from 'reactflow'

// ============ 类型定义 ============

export interface WorkflowData {
  nodes: Node[]
  edges: Edge[]
  viewport: Viewport
}

export interface WorkflowCreate {
  name: string
  description?: string
  version?: string
  author?: string
  tags?: string[]
  workflow_data: WorkflowData
}

export interface WorkflowUpdate {
  name?: string
  description?: string
  version?: string
  author?: string
  tags?: string[]
  workflow_data?: WorkflowData
}

export interface WorkflowResponse {
  id: string
  user_id: string
  name: string
  description: string | null
  version: string
  author: string | null
  tags: string[] | null
  workflow_data: WorkflowData
  created_at: string
  updated_at: string | null
}

export interface WorkflowListItem {
  id: string
  name: string
  description: string | null
  version: string
  tags: string[] | null
  created_at: string
  updated_at: string | null
}

// ============ 执行相关类型 ============

export interface WorkflowExecutionRequest {
  inputs?: Record<string, Record<string, any>>
}

export interface WorkflowExecutionResponse {
  execution_id: string
  status: string
  created_at: string
}

export type ExecutionStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled'

export interface WorkflowExecutionResult {
  execution_id: string
  status: ExecutionStatus
  created_at: string
  started_at: string | null
  completed_at: string | null
  execution_time: number | null
  node_status: Record<string, {
    status: ExecutionStatus
    started_at: string | null
    completed_at: string | null
    execution_time: number | null
    outputs: Record<string, any> | null
    error: string | null
  }>
  error: string | null
}

// SSE 事件类型
export type SSEEventType =
  | 'started'
  | 'node_started'
  | 'node_completed'
  | 'node_failed'
  | 'progress'
  | 'completed'
  | 'failed'
  | 'ping'

export interface WorkflowStartedEvent {
  execution_id: string
  workflow_id: string
  total_nodes: number
  started_at: string
}

export interface NodeStartedEvent {
  execution_id: string
  node_id: string
  node_type: string
  started_at: string
}

export interface NodeCompletedEvent {
  execution_id: string
  node_id: string
  outputs: Record<string, any>
  execution_time: number
  completed_at: string
}

export interface NodeFailedEvent {
  execution_id: string
  node_id: string
  error: string
  failed_at: string
}

export interface ProgressEvent {
  execution_id: string
  total_nodes: number
  completed_nodes: number
  current_node: string | null
  progress_percent: number
}

export interface WorkflowCompletedEvent {
  execution_id: string
  execution_time: number
  total_nodes: number
  successful_nodes: number
  completed_at: string
}

export interface WorkflowFailedEvent {
  execution_id: string
  error: string
  failed_at: string
  completed_nodes: number
  total_nodes: number
}

export type SSEEventData =
  | WorkflowStartedEvent
  | NodeStartedEvent
  | NodeCompletedEvent
  | NodeFailedEvent
  | ProgressEvent
  | WorkflowCompletedEvent
  | WorkflowFailedEvent

export interface SSEEvent {
  type: SSEEventType
  data: SSEEventData
}

// ============ API 函数 ============

export const workflowAPI = {
  // ========== CRUD 操作 ==========
  create: (d: WorkflowCreate) => apiClient.post<WorkflowResponse>('/workflows', d),
  list: (skip = 0, limit = 100) => apiClient.get<WorkflowListItem[]>('/workflows', { skip, limit }),
  get: (id: string) => apiClient.get<WorkflowResponse>(`/workflows/${id}`),
  update: (id: string, d: WorkflowUpdate) => apiClient.put<WorkflowResponse>(`/workflows/${id}`, d),
  delete: (id: string) => apiClient.delete(`/workflows/${id}`),

  // ========== 执行操作 ==========

  /**
   * 提交工作流执行
   * @param workflowId 工作流 ID
   * @param request 执行请求（包含输入）
   * @returns 执行响应（包含 execution_id）
   */
  execute: (workflowId: string, request: WorkflowExecutionRequest) =>
    apiClient.post<WorkflowExecutionResult>(`/workflows/${workflowId}/execute`, request),

  /**
   * 获取工作流执行结果
   * @param executionId 执行 ID
   * @returns 执行结果（仅在执行完成后可用）
   */
  getExecutionResult: (executionId: string) =>
    apiClient.get<WorkflowExecutionResult>(`/workflows/${executionId}/result`),

  // ========== 便捷方法 ==========

  async saveFromGraph(
    graphStore: { nodes: Node[]; edges: Edge[]; viewport: Viewport },
    name: string,
    description?: string
  ) {
    return this.create({
      name,
      description,
      version: '1.0.0',
      tags: [],
      workflow_data: {
        nodes: graphStore.nodes,
        edges: graphStore.edges,
        viewport: graphStore.viewport,
      },
    })
  },

  async loadToGraph(
    workflowId: string,
    graphStore: {
      setNodes: (nodes: Node[]) => void
      setEdges: (edges: Edge[]) => void
      setViewport: (viewport: Viewport) => void
    }
  ) {
    const wf = await this.get(workflowId)
    graphStore.setNodes(wf.workflow_data.nodes)
    graphStore.setEdges(wf.workflow_data.edges)
    graphStore.setViewport(wf.workflow_data.viewport)
    return wf
  },
}

