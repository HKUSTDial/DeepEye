import { DASHBOARD_PROGRESS_STAGE_KEYS, getDashboardProgressStage } from './dashboardProgress'
import {
  getReportProgressDisplayStep,
  parseReportProgressStage,
  REPORT_PROGRESS_STAGE_KEYS,
  REPORT_PROGRESS_TOTAL_STEPS,
} from './reportProgress'
import {
  parseVideoProgressStep,
  VIDEO_PROGRESS_STAGE_KEYS,
  VIDEO_PROGRESS_TOTAL_STEPS,
} from './videoProgress'
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

function trimProgressText(value: string) {
  return value.replace(/^[^\w[]+/, '').replace(/\s+/g, ' ').trim()
}

export function createReportProgressLine(stepIndex: number, totalSteps: number, label: string): ChatProgressLine {
  const normalizedStepIndex = Math.min(Math.max(Math.trunc(stepIndex), 1), Math.max(totalSteps, 1))
  const stageIndex = Math.min(normalizedStepIndex - 1, REPORT_PROGRESS_STAGE_KEYS.length - 1)
  const stageKey = REPORT_PROGRESS_STAGE_KEYS[stageIndex]
  return {
    tone: 'report',
    badge: translateApp('progress.reportBadge', { stepIndex: normalizedStepIndex, totalSteps }),
    label: stageKey ? translateApp(stageKey) : label,
    status: 'running',
  }
}

export function parseReportProgressLine(text: string): ChatProgressLine | null {
  const stage = parseReportProgressStage(text)
  if (stage === null) return null

  const label = translateApp(REPORT_PROGRESS_STAGE_KEYS[stage] || 'report.preparingPipeline')
  const detail = trimProgressText(
    text
      .replace(/\[\d+\s*\/\s*\d+\]/, '')
      .replace(/^(Done|Warning|Skipped|Failed|Unknown status)\s*:\s*/i, '')
      .replace(/^:\s*/, ''),
  )
  const status: ChatProgressStatus =
    /❌|failed|error/i.test(text)
      ? 'error'
      : /⚠️|△|warning|skipped|unknown/i.test(text)
        ? 'warning'
        : /✅|done|saved/i.test(text)
          ? 'done'
          : 'running'

  return {
    tone: 'report',
    badge: translateApp('progress.reportBadge', {
      stepIndex: getReportProgressDisplayStep(stage),
      totalSteps: REPORT_PROGRESS_TOTAL_STEPS,
    }),
    label,
    detail: detail && detail.toLowerCase() !== label.toLowerCase() ? detail : undefined,
    status,
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
  const stage = parseVideoProgressStep(text)
  if (stage === null) return null
  const stepIndex = stage + 1
  const label = translateApp(VIDEO_PROGRESS_STAGE_KEYS[stage] || 'progress.videoStepFallback', { stepIndex })
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
    badge: translateApp('progress.videoBadge', { stepIndex, totalSteps: VIDEO_PROGRESS_TOTAL_STEPS }),
    label,
    detail: detail && detail.toLowerCase() !== label.toLowerCase() ? detail : undefined,
    status,
  }
}

export function parseChatProgressLine(text: string): ChatProgressLine | null {
  return parseReportProgressLine(text) || parseDashboardProgressLine(text) || parseVideoProgressLine(text)
}
