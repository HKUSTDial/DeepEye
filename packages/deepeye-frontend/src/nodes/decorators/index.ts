/**
 * 统一装饰器系统
 * 将原来的 7 个装饰器合并为 1 个配置对象方案
 */

import { registry } from '../registry'
import type { DataType, PropertyType, NodeViewComponent } from '../types'
import type { ComponentType } from 'react'

// ============================================================================
// 类型定义
// ============================================================================

/**
 * 端口定义（输入/输出）
 */
export interface PortDef {
  type: DataType
  label?: string
  description?: string
  default?: any
  required?: boolean
  multiple?: boolean
}

/**
 * 属性定义
 */
export interface PropDef {
  type: PropertyType
  label?: string
  description?: string
  placeholder?: string
  default?: any
  options?: Array<{ label: string; value: any }>
  min?: number
  max?: number
  multiline?: boolean
  required?: boolean
}

/**
 * ViewData 配置
 */
export interface ViewDataConfig {
  label?: string
  maxRows?: number
  showIndex?: boolean
}

/**
 * AI 辅助配置
 */
export interface AIConfig {
  enableChat?: boolean
  placeholder?: string
}

/**
 * 视图配置
 */
export interface ViewConfig {
  component?: NodeViewComponent<any>
  config?: Record<string, any>
}

/**
 * 节点配置（统一配置对象）
 */
export interface NodeConfig {
  type: string
  label: string
  category: string
  icon?: ComponentType
  color?: string
  inputs?: Record<string, PortDef>
  outputs?: Record<string, PortDef>
  properties?: Record<string, PropDef>
  ai?: AIConfig
  viewData?: Record<string, ViewDataConfig>
  view?: ViewConfig
}

// ============================================================================
// 统一装饰器
// ============================================================================

/**
 * @Node 装饰器 - 统一节点定义
 *
 * @example
 * ```typescript
 * @Node({
 *   type: 'ai.datacoder',
 *   label: '智能数据处理',
 *   category: 'ai',
 *   icon: Code2,
 *   color: '#8B5CF6',
 *   inputs: {
 *     data: { type: 'object', label: '输入数据', required: true }
 *   },
 *   properties: {
 *     task: { type: 'string', label: '任务描述', multiline: true }
 *   },
 *   outputs: {
 *     result: { type: 'object', label: '处理结果' }
 *   },
 *   ai: {
 *     enableChat: true,
 *     placeholder: '输入数据处理任务'
 *   }
 * })
 * export class DataCoderNode {
 *   data: any = null
 *   task: string = ''
 *   result: any = null
 *   async compute() { }
 * }
 * ```
 */
export function Node(config: NodeConfig) {
  return function <T extends { new (...args: any[]): {} }>(constructor: T) {
    // 转换为 NodeDefinition 格式
    const definition = {
      type: config.type,
      label: config.label,
      category: config.category,
      icon: config.icon,
      color: config.color,
      class: constructor,
      inputs: config.inputs || {},
      outputs: config.outputs || {},
      properties: config.properties || {},
      view: config.view,
      aiConfig: config.ai,
      viewData: config.viewData
    }

    // 注册节点
    registry.register(definition)

    return constructor
  }
}



