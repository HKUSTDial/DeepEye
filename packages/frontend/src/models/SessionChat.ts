import type { Message, MessageTimelineItem, ToolStep } from '../types'
import type { AgentEvent } from '../api'
import {
  parseReportProgressStage,
  REPORT_PROGRESS_STAGE_FALLBACK_LABELS,
  REPORT_PROGRESS_TOTAL_STEPS,
} from '../utils/reportProgress'

interface SerializedSessionChat {
  id: string
  title: string
  messages?: Message[]
  createdAt: string
  updatedAt: string
}

function cloneToolStep(step: ToolStep): ToolStep {
  return {
    ...step,
    subSteps: step.subSteps?.map(cloneToolStep),
  }
}

function cloneTimelineItem(item: MessageTimelineItem): MessageTimelineItem {
  if (item.kind === 'step') {
    return { kind: 'step', step: cloneToolStep(item.step) }
  }
  return { ...item }
}

function cloneMessage(message: Message): Message {
  return {
    ...message,
    steps: message.steps?.map(cloneToolStep),
    timeline: message.timeline?.map(cloneTimelineItem),
  }
}

function cloneAgentEvent(event: AgentEvent): AgentEvent {
  return {
    ...event,
    data: event.data ? { ...event.data } : undefined,
  }
}

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
    if (last?.timeline) {
      this.clearTextStreamingFlags(last)
    }
    // 不再这里清空 streamEvents，允许在 agent_end 之后到达的“延迟”Token 继续追加到当前消息
    // this.streamEvents = []
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

  clone() {
    const session = new SessionChat(this.id, this.title, this.isDraft)
    session.messages = this.messages.map(cloneMessage)
    session.streamEvents = this.streamEvents.map(cloneAgentEvent)
    session.isStreaming = this.isStreaming
    session.createdAt = new Date(this.createdAt)
    session.updatedAt = new Date(this.updatedAt)
    return session
  }

  /**
   * Rebuild streaming message from events
   */
  private rebuildStreamingMessage() {
    const streamingMsgs = this.reduceStreamEvents(this.streamEvents)
    const lastStreaming = streamingMsgs[streamingMsgs.length - 1]
    
    if (lastStreaming) {
      if (this.isStreaming) {
        lastStreaming.isStreaming = true
      }
      
      // 过滤掉所有当前正在流式显示的临时消息
      let baseMessages = this.messages.filter(m => !m.isStreaming)

      // 处理“延迟”事件：如果当前已经停止流式传输，但又有新事件进来，
      // 说明我们在更新最后一条已完成的助理消息。
      if (!this.isStreaming && baseMessages.length > 0) {
        const last = baseMessages[baseMessages.length - 1]
        if (last.role === 'assistant') {
          baseMessages = baseMessages.slice(0, -1)
        }
      }

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
    const appendTextToTimeline = (
      message: Message,
      text: string,
      isStreaming: boolean = false,
      mergeWithPrevious: boolean = true,
    ) => {
      if (!message.timeline) message.timeline = []
      const last = message.timeline[message.timeline.length - 1]
      if (mergeWithPrevious && last && last.kind === 'text') {
        last.content += text
        last.isStreaming = isStreaming
      } else {
        message.timeline.push({ kind: 'text', content: text, isStreaming })
      }
    }
    const appendStepToTimeline = (message: Message, step: ToolStep) => {
      if (!message.timeline) message.timeline = []
      message.timeline.push({ kind: 'step', step })
    }
    let lastReportStage = -1
    const appendReportStepToTimeline = (message: Message, stageIndex: number) => {
      if (stageIndex <= lastReportStage) return
      lastReportStage = stageIndex
      const label = REPORT_PROGRESS_STAGE_FALLBACK_LABELS[stageIndex] ?? `Step ${stageIndex + 1}`
      if (!message.timeline) message.timeline = []
      message.timeline.push({
        kind: 'report_step',
        stepIndex: stageIndex + 1,
        totalSteps: REPORT_PROGRESS_TOTAL_STEPS,
        label,
      })
    }
    for (const e of eventList) {
      const { type, data = {} } = e
      const d = data as Record<string, unknown>
      // Token：后端 workflow 进度放在 data 里，顶层 source 为 "system"，需优先用 data 以正确展示
      const content = (typeof e.content === 'string' ? e.content : (typeof d?.content === 'string' ? d.content : '')) ?? ''
      const source = (typeof d?.source === 'string' ? d.source : (typeof e.source === 'string' ? e.source : '')) ?? ''

      if (type === 'agent_start') {
        if (current) result.push(current)
        current = { role: 'assistant', content: '', steps: [], timeline: [] }
        stepStack = []
      }
      else if (type === 'token') {
        if (!content) continue
        if (source === 'supervisor') {
          if (current) {
            current.content += content
            appendTextToTimeline(current, content, this.isStreaming)
          } else {
            // Late token after agent_end, append to last assistant message if exists.
            const last = result[result.length - 1]
            if (last && last.role === 'assistant') {
              last.content += content
              appendTextToTimeline(last, content, false)
            } else {
              current = { role: 'assistant', content, steps: [], timeline: [] }
              appendTextToTimeline(current, content, false)
            }
          }
        } else if (source === 'workflow' || !source) {
          // workflow tokens are progress lines; keep each token on a separate line.
          if (!current) {
            current = { role: 'assistant', content: '', steps: [], timeline: [] }
          }
          const chunk = current.content ? `\n${content}` : content
          current.content += chunk
          appendTextToTimeline(current, content, this.isStreaming, false)
        } else {
          // 对于其他来源的 token，追加到当前步骤的 thought
          const pending = pendingBySource[source]
          const step = pending ? pending[pending.length - 1] : null
          if (!step) {
            continue
          }
          const subs = (step.subSteps ??= [])
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
      else if (type === 'workflow_event' && current) {
        const phase = typeof d.phase === 'string' ? d.phase : ''
        const payload = typeof d.payload === 'object' && d.payload ? d.payload as Record<string, unknown> : {}
        const artifact =
          typeof payload.artifact === 'object' && payload.artifact
            ? payload.artifact as Record<string, unknown>
            : null
        const artifactKind = typeof artifact?.kind === 'string' ? artifact.kind : ''

        if (artifactKind === 'report' && phase === 'artifact_progress') {
          const messageText = typeof payload.message === 'string' ? payload.message.trim() : ''
          if (messageText) {
            const stageIndex = parseReportProgressStage(messageText)
            if (stageIndex !== null) {
              appendReportStepToTimeline(current, stageIndex)
            }
          }
        }
      }
      else if (type === 'tool_start' && current) {
        const step: ToolStep = { type: 'tool', name: String(data.name || ''), source, input: String(data.input || ''), status: 'running', subSteps: [] }
        if (source === 'supervisor') {
          current.steps!.push(step)
          appendStepToTimeline(current, step)
          stepStack = [step]
        } else {
          const parent = stepStack[0]
          if (parent) {
            parent.subSteps!.push(step)
          } else {
            current.steps!.push(step)
            appendStepToTimeline(current, step)
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
          stepStack[stepStack.length - 1]!.status = 'completed'
          if (stepStack.length > 1) stepStack.pop()
        } else {
          const pending = pendingBySource[source]
          if (pending && pending.length > 0) {
            const step = pending.shift()!
            step.output = output
            step.status = 'completed'
            if (pending.length === 0) {
              delete pendingBySource[source]
            }
          }
        }
      }
      else if (type === 'tool_error' && current) {
        const rawError = data.output ?? data.error
        const errorText = typeof rawError === 'object' && rawError && 'content' in rawError
          ? String((rawError as { content: unknown }).content)
          : String(rawError || '')
        if (source === 'supervisor' && stepStack.length > 0) {
          stepStack[stepStack.length - 1]!.output = errorText
          stepStack[stepStack.length - 1]!.status = 'error'
          if (stepStack.length > 1) stepStack.pop()
        } else {
          const pending = pendingBySource[source]
          if (pending && pending.length > 0) {
            const step = pending.shift()!
            step.output = errorText
            step.status = 'error'
            if (pending.length === 0) {
              delete pendingBySource[source]
            }
          }
        }
      }
      else if (type === 'agent_end' || type === 'error') {
        if (current) {
          this.clearTextStreamingFlags(current)
          current.isStreaming = false
        }
        if (current) result.push(current)
        current = null
        stepStack = []
      }
    }

    if (current) result.push(current)
    return result
  }

  private clearTextStreamingFlags(message: Message) {
    if (!message.timeline) return
    message.timeline.forEach((item) => {
      if (item.kind === 'text') {
        item.isStreaming = false
      }
    })
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
  static fromJSON(data: SerializedSessionChat): SessionChat {
    const session = new SessionChat(data.id, data.title)
    session.messages = data.messages || []
    session.createdAt = new Date(data.createdAt)
    session.updatedAt = new Date(data.updatedAt)
    return session
  }
}
