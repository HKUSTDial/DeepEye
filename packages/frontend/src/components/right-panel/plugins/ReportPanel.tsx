import { useEffect, useRef, useState } from 'react'
import { Download, FileText, Loader2, Sparkles, TriangleAlert } from 'lucide-react'
import { ArtifactProgressCard } from '../ArtifactProgressCard'
import { useReportStore } from '../../../stores/report'
import { useLocale } from '../../../locale'

const REPORT_IFRAME_SANDBOX = 'allow-scripts'

const STAGE_END_PCT = [8, 22, 42, 58, 82, 93, 100]

type StageStatus = 'done' | 'active' | 'warning' | 'pending'

function getStageDetail(status: StageStatus, t: (key: string) => string) {
  switch (status) {
    case 'done':
      return t('report.stageDone')
    case 'active':
      return t('report.stageActive')
    case 'warning':
      return t('report.stageWarning')
    default:
      return t('report.stagePending')
  }
}

function parseStages(
  steps: string[],
  isDone: boolean,
  stageCount: number,
): { stageStatuses: StageStatus[]; maxStage: number } {
  let maxStage = -1
  const warningStages = new Set<number>()
  let lastStageIdx = -1

  for (const line of steps) {
    const match = line.match(/\[(\d+)\/7\]/)
    if (match) {
      const idx = Math.min(parseInt(match[1], 10), 6)
      if (idx > maxStage) maxStage = idx
      lastStageIdx = idx
    }
    if (
      lastStageIdx >= 0 &&
      (line.includes('△') ||
        line.includes('❌') ||
        line.toLowerCase().includes('failed') ||
        line.toLowerCase().includes('error'))
    ) {
      warningStages.add(lastStageIdx)
    }
  }

  const stageStatuses: StageStatus[] = Array.from({ length: stageCount }, (_, index) => {
    if (isDone || index < maxStage) return warningStages.has(index) ? 'warning' : 'done'
    if (index === maxStage) return isDone ? (warningStages.has(index) ? 'warning' : 'done') : 'active'
    return 'pending'
  })

  return { stageStatuses, maxStage }
}

export function ReportPanel({ sessionId }: { sessionId: string | null }) {
  const { t } = useLocale()
  const STAGES = [
    { label: t('report.stage1'), icon: '📂' },
    { label: t('report.stage2'), icon: '🔍' },
    { label: t('report.stage3'), icon: '🕵️' },
    { label: t('report.stage4'), icon: '📊' },
    { label: t('report.stage5'), icon: '📈' },
    { label: t('report.stage6'), icon: '✍️' },
    { label: t('report.stage7'), icon: '🎨' },
  ]
  const sessionReport = useReportStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )
  const reportHtml = sessionReport?.reportHtml ?? null
  const reportSteps = sessionReport?.reportSteps ?? []
  const reportFilename = sessionReport?.reportFilename ?? null
  const reportError = sessionReport?.reportError ?? null
  const isGenerating = sessionReport?.isGenerating ?? false

  const [displayPercent, setDisplayPercent] = useState(0)
  const committedStageRef = useRef(-1)

  const isDone = !!reportHtml
  const showProgress = !isDone && (isGenerating || reportSteps.length > 0) && !reportError
  const isWaiting = isGenerating && reportSteps.length === 0 && !reportError

  const { stageStatuses, maxStage } = parseStages(reportSteps, isDone, STAGES.length)

  useEffect(() => {
    if (maxStage > committedStageRef.current) {
      committedStageRef.current = maxStage
    }
  }, [maxStage])

  useEffect(() => {
    if (!isDone) return
    const timeoutId = window.setTimeout(() => setDisplayPercent(100), 0)
    return () => window.clearTimeout(timeoutId)
  }, [isDone])

  useEffect(() => {
    if (!showProgress || isDone) return
    const id = window.setInterval(() => {
      setDisplayPercent((prev) => {
        const stage = committedStageRef.current
        const floor = stage <= 0 ? 0 : STAGE_END_PCT[stage - 1]
        const ceiling = STAGE_END_PCT[Math.min(Math.max(stage, 0), STAGE_END_PCT.length - 1)] - 0.8
        const current = Math.max(prev, floor)
        if (current >= ceiling) return current
        const gap = ceiling - current
        const step = Math.max(0.03, gap * 0.012)
        return Math.min(current + step, ceiling)
      })
    }, 150)
    return () => window.clearInterval(id)
  }, [showProgress, isDone])

  useEffect(() => {
    if (showProgress) return
    committedStageRef.current = -1
    const timeoutId = window.setTimeout(() => setDisplayPercent(0), 0)
    return () => window.clearTimeout(timeoutId)
  }, [showProgress])

  const handleDownload = () => {
    if (!reportHtml) return
    const blob = new Blob([reportHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = reportFilename || 'report.html'
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(url)
  }

  const roundedPct = isDone ? 100 : Math.round(displayPercent)
  const progressedCount = stageStatuses.filter((status) => status !== 'pending').length
  const currentStageLabel =
    maxStage >= 0 && maxStage < STAGES.length
      ? STAGES[maxStage].label
      : t('report.preparingPipeline')
  const reportStepsProgress = STAGES.map((stage, index) => ({
    id: stage.label,
    label: stage.label,
    detail: getStageDetail(stageStatuses[index], t),
    icon: stageStatuses[index] === 'done' ? '✓' : stage.icon,
    status: stageStatuses[index],
  }))

  if (!reportHtml && reportSteps.length === 0 && !isGenerating) {
    return (
      <div className="right-panel-empty">
        <div className="right-panel-empty-kicker">{t('panel.report.title')}</div>
        <FileText className="right-panel-empty-icon" />
        <h3 className="right-panel-empty-title">{t('report.emptyTitle')}</h3>
        <p className="right-panel-empty-subtitle">
          {t('report.emptySubtitle')}
        </p>
      </div>
    )
  }

  return (
    <div className="panel-view">
      {showProgress && (
        <div className="artifact-progress-shell">
          <ArtifactProgressCard
            artifact={t('panel.report.title')}
            title={t('report.generatingTitle')}
            description={t('report.generatingDescription')}
            icon={<FileText size={18} />}
            variant="report"
            signature={t('report.signature')}
            status={isWaiting ? 'waiting' : 'running'}
            statusLabel={isWaiting ? t('common.queued') : t('common.running')}
            percent={roundedPct}
            currentLabel={currentStageLabel}
            metrics={[
              { label: t('report.phasesMetric'), value: `${progressedCount}/7` },
              { label: 'Output', value: t('report.outputMetric') },
            ]}
            steps={reportStepsProgress}
            tone="#c2410c"
          />
        </div>
      )}

      <div className={`panel-surface${reportHtml ? ' panel-surface--report' : ''}`}>
        {reportError ? (
          <div className="panel-state-card panel-state-card--error">
            <div className="panel-state-icon">
              <TriangleAlert size={16} />
            </div>
            <div className="panel-state-copy">
              <div className="panel-state-title">{t('report.failedTitle')}</div>
              <div className="panel-state-body">{reportError}</div>
            </div>
          </div>
        ) : reportHtml ? (
          <div className="panel-report-layout">
            <div className="panel-inline-header">
              <div className="panel-inline-note">
                {reportFilename ? (
                  <span>
                    {t('report.savedToWorkspace', { filename: reportFilename })} <code>{reportFilename}</code>
                  </span>
                ) : (
                  t('report.readyToReview')
                )}
              </div>
              <button type="button" onClick={handleDownload} className="panel-toolbar-btn panel-toolbar-btn--primary">
                <Download />
                {t('common.download')}
              </button>
            </div>
            <iframe
              title={t('report.iframeTitle')}
              srcDoc={reportHtml}
              className="panel-report-frame"
              sandbox={REPORT_IFRAME_SANDBOX}
            />
          </div>
        ) : isWaiting ? (
          <div className="panel-state-card">
            <div className="panel-state-icon">
              <Loader2 size={16} className="animate-spin" />
            </div>
            <div className="panel-state-copy">
              <div className="panel-state-title">{t('report.waitingTitle')}</div>
              <div className="panel-state-body">
                {t('report.waitingBody')}
              </div>
            </div>
          </div>
        ) : isGenerating ? (
          <div className="panel-state-card">
            <div className="panel-state-icon">
              <Sparkles size={16} />
            </div>
            <div className="panel-state-copy">
              <div className="panel-state-title">{t('report.inProgressTitle')}</div>
              <div className="panel-state-body">
                {t('report.inProgressBody')}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
