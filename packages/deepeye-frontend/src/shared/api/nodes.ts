/**
 * 节点 API
 * 
 * 对接后端节点接口：
 * - GET /api/v1/nodes - 列出所有节点
 * - GET /api/v1/nodes/{type} - 获取节点信息
 * - POST /api/v1/nodes/{type}/execute - 执行单个节点
 */

import { apiClient } from './client'

// ============ 类型定义 ============

export interface PortInfo {
  name: string
  type: string
  description?: string
  required?: boolean
}

export interface NodeInfo {
  type: string
  label: string
  category: string
  description?: string
  inputs: PortInfo[]
  outputs: PortInfo[]
  config_schema?: Record<string, any>
}

export interface NodeListResponse {
  total: number
  nodes: NodeInfo[]
}

export interface NodeExecutionRequest {
  inputs: Record<string, any>
  config?: Record<string, any>
}

export interface NodeExecutionResult {
  status: 'success' | 'failed'
  outputs: Record<string, any>
  execution_time: number
  error: string | null
}

// ============ API 函数 ============

export const nodesAPI = {
  list: () => apiClient.get<NodeListResponse>('/nodes'),
  getInfo: (type: string) => apiClient.get<NodeInfo>(`/nodes/${type}`),

  execute: (type: string, inputs: Record<string, any>, config?: Record<string, any>) =>
    apiClient.post<NodeExecutionResult>(`/nodes/${type}/execute`, {
      inputs,
      config: config || {},
    }),
}

