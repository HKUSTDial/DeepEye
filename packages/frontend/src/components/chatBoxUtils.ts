import type { Message, ToolStep } from '../types'
import type { AppLocale } from '../locale'

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

export function buildFollowUpPrompts(
  content: string,
  hasAttachedData: boolean,
  locale: AppLocale = 'en',
): string[] {
  const normalized = content.toLowerCase()
  const isZh = locale === 'zh-CN'

  if (normalized.includes('dashboard') || normalized.includes('chart')) {
    return isZh
      ? [
          '把这条结论整理成 dashboard 方案，包含 KPI 卡片和筛选器。',
          '如果只做一张图，应该先做哪一张？为什么？',
          '还需要补什么后续分析，才能让这个可视化更有说服力？',
        ]
      : [
          'Turn this into a dashboard plan with KPI cards and filters.',
          'Which chart should I build first, and why?',
          'What follow-up analysis would strengthen this visual story?',
        ]
  }

  if (normalized.includes('report') || normalized.includes('summary')) {
    return isZh
      ? [
          '把这段内容压缩成高层摘要。',
          '这里最重要的三个风险或注意点是什么？',
          '把它改写成可执行的下一步建议。',
        ]
      : [
          'Condense this into an executive summary.',
          'What are the top three risks or watchouts here?',
          'Turn this into concrete next-step recommendations.',
        ]
  }

  if (hasAttachedData) {
    return isZh
      ? [
          '基于这份数据，下一步最值得追问的问题是什么？',
          '基于这条回答，推荐图表或 dashboard 方向。',
          '把它整理成一版简洁的业务报告大纲。',
        ]
      : [
          'What is the strongest next question to ask about this data?',
          'Recommend charts or a dashboard based on this answer.',
          'Turn this into a concise business report outline.',
        ]
  }

  return isZh
    ? [
        '把这段内容再压缩得更简洁一些。',
        '我下一步最值得追问的问题有哪些？',
        '把它整理成行动清单。',
      ]
    : [
        'Summarize this more concisely.',
        'What follow-up questions should I ask next?',
        'Turn this into an action-oriented checklist.',
      ]
}
