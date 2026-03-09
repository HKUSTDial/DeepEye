import { DASHBOARD_PROGRESS_STAGES, getDashboardProgressStage } from './dashboardProgress'

export type ChatProgressTone = 'report' | 'dashboard' | 'video'
export type ChatProgressStatus = 'running' | 'done' | 'warning' | 'error'

export interface ChatProgressLine {
  tone: ChatProgressTone
  badge: string
  label: string
  detail?: string
  status: ChatProgressStatus
}

const VIDEO_PROGRESS_STAGES = [
  'Generate video configuration',
  'Generate audio and align timeline',
  'Save configuration file',
  'Render video components',
] as const

function trimProgressText(value: string) {
  return value.replace(/^[^\w[]+/, '').replace(/\s+/g, ' ').trim()
}

export function createReportProgressLine(stepIndex: number, totalSteps: number, label: string): ChatProgressLine {
  return {
    tone: 'report',
    badge: `Report ${stepIndex}/${totalSteps}`,
    label,
    status: 'running',
  }
}

export function parseDashboardProgressLine(text: string): ChatProgressLine | null {
  const stage = getDashboardProgressStage(text)
  if (stage === null) return null
  const detail = trimProgressText(text)
  const label = DASHBOARD_PROGRESS_STAGES[stage] || 'Dashboard progress'
  const isDone = /deployment complete|successfully synchronized/i.test(text)
  return {
    tone: 'dashboard',
    badge: `Dashboard ${stage + 1}/${DASHBOARD_PROGRESS_STAGES.length}`,
    label,
    detail: detail.toLowerCase() === label.toLowerCase() ? undefined : detail,
    status: isDone ? 'done' : 'running',
  }
}

export function parseVideoProgressLine(text: string): ChatProgressLine | null {
  const match = text.match(/Step\s*(\d+)\s*\/\s*(\d+)/i)
  if (!match) return null
  const stepIndex = Math.max(1, parseInt(match[1], 10))
  const totalSteps = Math.max(stepIndex, parseInt(match[2], 10))
  const label = VIDEO_PROGRESS_STAGES[stepIndex - 1] || `Video step ${stepIndex}`
  const status: ChatProgressStatus =
    /❌|failed/i.test(text)
      ? 'error'
      : /⚠️|warning|skipped|unknown/i.test(text)
        ? 'warning'
        : /✅|done/i.test(text)
          ? 'done'
          : 'running'
  const detail = trimProgressText(
    text
      .replace(/^[^\w[]+/, '')
      .replace(/Step\s*\d+\s*\/\s*\d+\s*/i, '')
      .replace(/^(Done|Warning|Skipped|Failed|Unknown status)\s*:\s*/i, '')
      .replace(/^:\s*/, ''),
  )

  return {
    tone: 'video',
    badge: `Video ${stepIndex}/${totalSteps}`,
    label,
    detail: detail && detail.toLowerCase() !== label.toLowerCase() ? detail : undefined,
    status,
  }
}

export function parseChatProgressLine(text: string): ChatProgressLine | null {
  return parseDashboardProgressLine(text) || parseVideoProgressLine(text)
}
