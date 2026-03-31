import type { Message, ToolStep } from '../types'

export function buildStepActivityKey(steps?: ToolStep[]): string {
  if (!steps || steps.length === 0) return ''
  return steps
    .map((step) => {
      const subKey = buildStepActivityKey(step.subSteps)
      return [
        step.type,
        step.name,
        step.status,
        step.input?.length || 0,
        step.output?.length || 0,
        step.thought?.length || 0,
        subKey,
      ].join(':')
    })
    .join('|')
}

export function buildMessageActivityKey(message?: Message): string {
  if (!message) return ''
  const timelineKey = (message.timeline || [])
    .map((item) => {
      if (item.kind === 'text') {
        return `text:${item.content.length}:${item.isStreaming ? 1 : 0}`
      }
      if (item.kind === 'report_step') {
        return `report:${item.stepIndex}:${item.label}`
      }
      return `step:${buildStepActivityKey([item.step])}`
    })
    .join('|')
  return [
    message.role,
    message.content.length,
    message.isStreaming ? 1 : 0,
    buildStepActivityKey(message.steps),
    timelineKey,
  ].join('~')
}

export function hasText(value?: string) {
  return Boolean(value && value.trim().length > 0)
}
