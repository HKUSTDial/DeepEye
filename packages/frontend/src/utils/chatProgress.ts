import { getDashboardProgressStage } from './dashboardProgress'
import { translateApp } from '../locale'

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
  'video.step1',
  'video.step2',
  'video.step3',
  'video.step4',
] as const

function trimProgressText(value: string) {
  return value.replace(/^[^\w[]+/, '').replace(/\s+/g, ' ').trim()
}

export function createReportProgressLine(stepIndex: number, totalSteps: number, label: string): ChatProgressLine {
  return {
    tone: 'report',
    badge: translateApp('progress.reportBadge', { stepIndex, totalSteps }),
    label,
    status: 'running',
  }
}

export function parseDashboardProgressLine(text: string): ChatProgressLine | null {
  const stage = getDashboardProgressStage(text)
  if (stage === null) return null
  const detail = trimProgressText(text)
  const label = translateApp(DASHBOARD_PROGRESS_STAGE_KEYS[stage] || 'progress.dashboardFallback')
  const isDone = /deployment complete|successfully synchronized/i.test(text)
  return {
    tone: 'dashboard',
    badge: translateApp('progress.dashboardBadge', { stepIndex: stage + 1, totalSteps: DASHBOARD_PROGRESS_STAGE_KEYS.length }),
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
  const label = translateApp(VIDEO_PROGRESS_STAGES[stepIndex - 1] || 'progress.videoStepFallback', { stepIndex })
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
    badge: translateApp('progress.videoBadge', { stepIndex, totalSteps }),
    label,
    detail: detail && detail.toLowerCase() !== label.toLowerCase() ? detail : undefined,
    status,
  }
}

export function parseChatProgressLine(text: string): ChatProgressLine | null {
  return parseDashboardProgressLine(text) || parseVideoProgressLine(text)
}
const DASHBOARD_PROGRESS_STAGE_KEYS = [
  'dashboard.stage1',
  'dashboard.stage2',
  'dashboard.stage3',
  'dashboard.stage4',
  'dashboard.stage5',
  'dashboard.stage6',
] as const
