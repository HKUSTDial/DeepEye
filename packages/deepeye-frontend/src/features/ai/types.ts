/**
 * AI 功能相关类型定义
 */

/**
 * 消息角色
 */
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool'

/**
 * 聊天消息
 */
export interface ChatMessage {
  role: MessageRole
  content: string
  /** 工具调用（如果是 assistant 消息） */
  toolCalls?: ToolCall[]
  /** 工具调用结果（如果是 tool 消息） */
  toolCallId?: string
  /** 时间戳 */
  timestamp?: number
}

/**
 * 工具调用
 */
export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, any>
}

/**
 * 工具调用结果
 */
export interface ToolCallResult {
  toolCallId: string
  result: any
  error?: string
}

/**
 * AI 响应
 */
export interface AIResponse {
  content: string
  toolCalls?: ToolCall[]
  finishReason: 'stop' | 'tool_calls' | 'length' | 'error'
}

