export const REPORT_PROGRESS_TOTAL_STEPS = 7

export const REPORT_PROGRESS_STAGE_KEYS = [
  'report.stage1',
  'report.stage2',
  'report.stage3',
  'report.stage4',
  'report.stage5',
  'report.stage6',
  'report.stage7',
] as const

export const REPORT_PROGRESS_STAGE_FALLBACK_LABELS = [
  'Load and parse data files',
  'Generate dataset context',
  'Perform deep exploratory analysis (EDA)',
  'Calculate key business indicators (KPI)',
  'Plan and generate visual charts',
  'Write analysis summary and conclusions',
  'Render final HTML report',
] as const

export const REPORT_PROGRESS_STAGE_ICONS = ['📂', '🔍', '🕵️', '📊', '📈', '✍️', '🎨'] as const

export const REPORT_PROGRESS_STAGE_END_PCT = [8, 22, 42, 58, 82, 93, 100] as const

export type ReportProgressStepStatus = 'done' | 'active' | 'warning' | 'pending'

export interface ReportProgressState {
  stageStatuses: ReportProgressStepStatus[]
  maxStage: number
  progressedCount: number
}

function clampStageIndex(value: number, stageCount: number) {
  return Math.min(Math.max(Math.trunc(value), 0), Math.max(stageCount - 1, 0))
}

export function parseReportProgressStage(message: string, stageCount = REPORT_PROGRESS_TOTAL_STEPS): number | null {
  const match = message.match(/\[(\d+)\s*\/\s*(\d+)\]/)
  if (!match) return null

  const rawStep = Number.parseInt(match[1], 10)
  const rawTotal = Number.parseInt(match[2], 10)
  if (Number.isNaN(rawStep)) return null

  const total = Number.isNaN(rawTotal) || rawTotal <= 0 ? stageCount : rawTotal
  return clampStageIndex(rawStep, Math.min(total, stageCount))
}

export function getReportProgressDisplayStep(stageIndex: number) {
  return clampStageIndex(stageIndex, REPORT_PROGRESS_TOTAL_STEPS) + 1
}

export function isReportProgressWarning(message: string) {
  const normalized = message.toLowerCase()
  return (
    message.includes('△') ||
    message.includes('⚠️') ||
    message.includes('❌') ||
    normalized.includes('failed') ||
    normalized.includes('error') ||
    normalized.includes('warning')
  )
}

export function deriveReportProgressState(
  steps: string[],
  isDone: boolean,
  stageCount = REPORT_PROGRESS_TOTAL_STEPS,
): ReportProgressState {
  let maxStage = -1
  let lastStage = -1
  const warningStages = new Set<number>()

  for (const line of steps) {
    const stage = parseReportProgressStage(line, stageCount)
    if (stage !== null) {
      maxStage = Math.max(maxStage, stage)
      lastStage = stage
    }
    if (lastStage >= 0 && isReportProgressWarning(line)) {
      warningStages.add(lastStage)
    }
  }

  const stageStatuses = Array.from({ length: stageCount }, (_, index): ReportProgressStepStatus => {
    if (isDone || index < maxStage) {
      return warningStages.has(index) ? 'warning' : 'done'
    }
    if (index === maxStage) {
      return isDone && warningStages.has(index) ? 'warning' : 'active'
    }
    return 'pending'
  })

  return {
    stageStatuses,
    maxStage,
    progressedCount: stageStatuses.filter((status) => status !== 'pending').length,
  }
}
