import type { Message, ToolStep } from '../types'
import type { AgentEvent } from '../api'

/**
 * SessionChat - Represents a single chat window/session
 * 
 * Manages all state for one chat session including:
 * - Unique session_id
 * - Message history
 * - Streaming state
 * - Event accumulation
 */
export class SessionChat {
  readonly id: string
  title: string
  messages: Message[]
  streamEvents: AgentEvent[]
  isStreaming: boolean
  isDraft: boolean
  createdAt: Date
  updatedAt: Date

  constructor(id: string, title: string = 'New conversation', isDraft: boolean = false) {
    this.id = id
    this.title = title
    this.messages = []
    this.streamEvents = []
    this.isStreaming = false
    this.isDraft = isDraft
    this.createdAt = new Date()
    this.updatedAt = new Date()
  }

  /**
   * Add a user message
   */
  addUserMessage(content: string) {
    this.messages.push({ role: 'user', content })
    this.updatedAt = new Date()
  }

  /**
   * Start streaming mode
   */
  startStreaming() {
    this.isStreaming = true
    this.streamEvents = []
  }

  /**
   * Stop streaming and finalize
   */
  stopStreaming() {
    this.isStreaming = false
    const last = this.messages[this.messages.length - 1]
    if (last?.isStreaming) {
      last.isStreaming = false
    }
    this.streamEvents = []
    this.updatedAt = new Date()
  }

  /**
   * Add streaming event
   */
  pushEvent(event: AgentEvent) {
    this.streamEvents.push(event)
    this.rebuildStreamingMessage()
  }

  /**
   * Load history messages (from backend)
   */
  loadMessages(messages: Message[]) {
    this.messages = messages
    this.updatedAt = new Date()
  }

  /**
   * Clear all data
   */
  clear() {
    this.messages = []
    this.streamEvents = []
    this.isStreaming = false
  }

  /**
   * Rebuild streaming message from events
   */
  private rebuildStreamingMessage() {
    const streamingMsgs = this.reduceStreamEvents(this.streamEvents)
    const lastStreaming = streamingMsgs[streamingMsgs.length - 1]
    
    if (lastStreaming) {
      lastStreaming.isStreaming = true
      // Remove previous streaming message and append new one
      const baseMessages = this.messages.filter(m => !m.isStreaming)
      this.messages = [...baseMessages, lastStreaming]
    }
  }

  /**
   * Reduce stream events to messages (same logic as before)
   */
  private reduceStreamEvents(eventList: AgentEvent[]): Message[] {
    const result: Message[] = []
    let current: Message | null = null
    let stepStack: ToolStep[] = []
    const pendingBySource: Record<string, ToolStep[]> = {}

    for (const e of eventList) {
      const { type, data = {} } = e
      const d = data as Record<string, unknown>
      // Token：后端 workflow 进度放在 data 里，顶层 source 为 "system"，需优先用 data 以正确展示
      const content = (typeof e.content === 'string' ? e.content : (typeof d?.content === 'string' ? d.content : '')) ?? ''
      const source = (typeof d?.source === 'string' ? d.source : (typeof e.source === 'string' ? e.source : '')) ?? ''

      if (type === 'agent_start') {
        if (current) result.push(current)
        current = { role: 'assistant', content: '', steps: [] }
        stepStack = []
      }
      else if (type === 'token') {
        if (!content) continue
        // 如果没有 current，创建一个新的 assistant 消息（用于 workflow 进度消息）
        if (!current) {
          current = { role: 'assistant', content: '', steps: [] }
        }
        if (source === 'supervisor' || source === 'workflow' || !source) {
          // 对于 supervisor 或 workflow 来源的 token，每行一个步骤追加到 content
          current.content += (current.content ? '\n' : '') + content
        } else {
          // 对于其他来源的 token，追加到当前步骤的 thought
          const pending = pendingBySource[source]
          const step = pending ? pending[pending.length - 1] : null
          if (!step) {
            continue
          }
          const subs = step.subSteps ??= []
          const last = subs[subs.length - 1]
          if (last?.type === 'thought') {
            last.thought = (last.thought || '') + content
          } else {
            subs.push({
              type: 'thought',
              name: 'Thinking',
              source,
              thought: content,
              status: 'completed',
              subSteps: [],
            })
          }
        }
      }
      else if (type === 'tool_start' && current) {
        const step: ToolStep = { type: 'tool', name: String(data.name || ''), source, input: String(data.input || ''), status: 'completed', subSteps: [] }
        if (source === 'supervisor') {
          current.steps!.push(step)
          stepStack = [step]
        } else {
          const parent = stepStack[0]
          if (parent) {
            parent.subSteps!.push(step)
          } else {
            current.steps!.push(step)
          }
          pendingBySource[source] ??= []
          pendingBySource[source].push(step)
        }
      }
      else if (type === 'tool_end' && current) {
        const rawOutput = data.output as unknown
        const output = typeof rawOutput === 'object' && rawOutput && 'content' in rawOutput ? String((rawOutput as { content: unknown }).content) : String(rawOutput || '')
        if (source === 'supervisor' && stepStack.length > 0) {
          stepStack[stepStack.length - 1]!.output = output
          if (stepStack.length > 1) stepStack.pop()
        } else {
          const pending = pendingBySource[source]
          if (pending && pending.length > 0) {
            const step = pending.shift()!
            step.output = output
            if (pending.length === 0) {
              delete pendingBySource[source]
            }
          }
        }
      }
      else if (type === 'agent_end' || type === 'error') {
        if (current) result.push(current)
        current = null
        stepStack = []
      }
    }

    if (current) result.push(current)
    return result
  }

  /**
   * Serialize to plain object (for storage)
   */
  toJSON() {
    return {
      id: this.id,
      title: this.title,
      messages: this.messages,
      createdAt: this.createdAt.toISOString(),
      updatedAt: this.updatedAt.toISOString(),
    }
  }

  /**
   * Create from plain object
   */
  static fromJSON(data: any): SessionChat {
    const session = new SessionChat(data.id, data.title)
    session.messages = data.messages || []
    session.createdAt = new Date(data.createdAt)
    session.updatedAt = new Date(data.updatedAt)
    return session
  }
}

