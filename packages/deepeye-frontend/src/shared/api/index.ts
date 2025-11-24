/**
 * API 统一导出
 */

export * from './client'
export * from './auth'
export * from './workflow'
export * from './nodes'

// 导入各个 API 模块
import { authAPI } from './auth'
import { workflowAPI } from './workflow'
import { nodesAPI } from './nodes'

// 统一的 API 对象（推荐使用）
export const api = {
  auth: authAPI,
  workflow: workflowAPI,
  nodes: nodesAPI,
}

// 导出配置管理器
export { apiConfig } from '../config/api.config'

