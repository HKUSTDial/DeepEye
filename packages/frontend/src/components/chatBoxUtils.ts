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

export function buildFollowUpPrompts(content: string, hasAttachedData: boolean): string[] {
  const normalized = content.toLowerCase()

  if (normalized.includes('dashboard') || normalized.includes('chart')) {
    return [
      'Turn this into a dashboard plan with KPI cards and filters.',
      'Which chart should I build first, and why?',
      'What follow-up analysis would strengthen this visual story?',
    ]
  }

  if (normalized.includes('report') || normalized.includes('summary')) {
    return [
      'Condense this into an executive summary.',
      'What are the top three risks or watchouts here?',
      'Turn this into concrete next-step recommendations.',
    ]
  }

  if (hasAttachedData) {
    return [
      'What is the strongest next question to ask about this data?',
      'Recommend charts or a dashboard based on this answer.',
      'Turn this into a concise business report outline.',
    ]
  }

  return [
    'Summarize this more concisely.',
    'What follow-up questions should I ask next?',
    'Turn this into an action-oriented checklist.',
  ]
}
