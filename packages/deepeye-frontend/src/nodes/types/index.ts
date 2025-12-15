/**
 * 节点系统核心类型定义
 */

import { ComponentType } from 'react'

// ============================================================================
// 数据类型
// ============================================================================

/**
 * 支持的数据类型
 */
export type DataType = 'number' | 'string' | 'boolean' | 'object' | 'array' | 'any'

/**
 * 属性面板类型
 */
export type PropertyType = 'text' | 'string' | 'number' | 'boolean' | 'select' | 'color' | 'textarea' | 'database-select' | 'model-select'

// ============================================================================
// 端口定义
// ============================================================================

/**
 * 输入端口定义
 */
export interface InputDefinition {
  type: DataType
  label?: string
  description?: string
  default?: any
  required?: boolean
  /** 是否支持多个输入连接 */
  multiple?: boolean
}

/**
 * 输出端口定义
 */
export interface OutputDefinition {
  type: DataType
  label?: string
  description?: string
}

/**
 * 属性定义
 */
export interface PropertyDefinition {
  type: PropertyType
  label?: string
  description?: string
  placeholder?: string
  default?: any
  options?: Array<{ label: string; value: any }>  // 用于 select 类型
  min?: number        // 用于 number 类型
  max?: number        // 用于 number 类型
  multiline?: boolean // 用于 text/string 类型
  required?: boolean
}

// ============================================================================
// 视图组件
// ============================================================================

/**
 * 视图组件 Props
 */
export interface NodeViewProps<TConfig = any> {
  attributes: Record<string, any>
  updateAttributes: (updates: Record<string, any>) => void
  config: TConfig
}

/**
 * 视图组件类型
 */
export type NodeViewComponent<TConfig = any> = ComponentType<NodeViewProps<TConfig>>

/**
 * 视图定义
 */
export interface ViewDefinition {
  component?: NodeViewComponent<any>
  config?: Record<string, any>
  render?: (props: NodeViewProps) => JSX.Element
}

// ============================================================================
// 节点定义
// ============================================================================

/**
 * 节点配置
 */
export interface NodeConfig {
  type: string
  label: string
  category: string
  icon?: ComponentType
  color?: string
}

/**
 * AI 辅助配置
 */
export interface AIAssistedOptions {
  enableChat?: boolean
  placeholder?: string
}

/**
 * ViewData 配置
 */
export interface ViewDataOptions {
  label?: string
  maxRows?: number
  showIndex?: boolean
}

/**
 * 节点定义（注册表中存储的完整定义）
 */
export interface NodeDefinition extends NodeConfig {
  class: new () => any
  inputs: Record<string, InputDefinition>
  outputs: Record<string, OutputDefinition>
  properties: Record<string, PropertyDefinition>
  view?: ViewDefinition
  aiConfig?: AIAssistedOptions
  viewData?: Record<string, ViewDataOptions>
}

// ============================================================================
// 节点实例
// ============================================================================

/**
 * 节点数据
 */
export interface NodeData {
  attributes: Record<string, any>
}

