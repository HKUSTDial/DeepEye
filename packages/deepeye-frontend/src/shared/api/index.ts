/**
 * API 统一导出
 */

export * from './client'
export * from './auth'
export * from './workflow'
export * from './nodes'
export * from './databaseConnections'
export * from './llmModels'
export * from './files'

// 导入各个 API 模块
import { authAPI } from './auth'
import { workflowAPI } from './workflow'
import { nodesAPI } from './nodes'
import { databaseConnectionsAPI } from './databaseConnections'
import { llmModelsAPI } from './llmModels'
import { filesAPI } from './files'

// 统一的 API 对象（推荐使用）
export const api = {
  auth: authAPI,
  workflow: workflowAPI,
  nodes: nodesAPI,
  connections: databaseConnectionsAPI,
  llms: llmModelsAPI,
  files: filesAPI,
}

// 导出配置管理器
export { apiConfig } from '../config/api.config'

