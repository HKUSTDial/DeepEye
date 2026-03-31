import { createReportProgressLine, parseChatProgressLine, type ChatProgressLine } from '../utils/chatProgress'
import type { Message, ToolStep } from '../types'
import { hasText } from './chatBoxUtils'

export type AssistantProcessEntry =
  | { kind: 'step'; step: ToolStep }
  | { kind: 'progress'; progress: ChatProgressLine }

export interface AssistantMessageSections {
  finalContent: string
  processEntries: AssistantProcessEntry[]
}

export function splitAssistantMessageSections(message: Message): AssistantMessageSections {
  const processEntries: AssistantProcessEntry[] = []

  if (message.timeline && message.timeline.length > 0) {
    const finalParts: string[] = []
    for (const item of message.timeline) {
      if (item.kind === 'step') {
        processEntries.push({ kind: 'step', step: item.step })
        continue
      }
      if (item.kind === 'report_step') {
        processEntries.push({
          kind: 'progress',
          progress: createReportProgressLine(item.stepIndex, item.totalSteps, item.label),
        })
        continue
      }

      const progress = parseChatProgressLine(item.content || '')
      if (progress) {
        processEntries.push({ kind: 'progress', progress })
      } else if (hasText(item.content)) {
        finalParts.push(item.content || '')
      }
    }

    return {
      finalContent: finalParts.join('').trim(),
      processEntries,
    }
  }

  if (message.steps && message.steps.length > 0) {
    for (const step of message.steps) {
      processEntries.push({ kind: 'step', step })
    }
  }

  return {
    finalContent: hasText(message.content) ? message.content.trim() : '',
    processEntries,
  }
}
