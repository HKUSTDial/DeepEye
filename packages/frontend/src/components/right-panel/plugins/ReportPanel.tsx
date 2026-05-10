import { useEffect, useRef, useState } from 'react'
import { Download, FileText, Loader2, Sparkles, TriangleAlert } from 'lucide-react'
import { ArtifactProgressCard } from '../ArtifactProgressCard'
import { useReportStore } from '../../../stores/report'
import { useLocale } from '../../../locale'
import { createReportGeneration } from '../../../utils/artifactGeneration'
import {
  deriveReportProgressState,
  REPORT_PROGRESS_STAGE_END_PCT,
} from '../../../utils/reportProgress'

const REPORT_IFRAME_SANDBOX = 'allow-scripts'

export function ReportPanel({ sessionId }: { sessionId: string | null }) {
  const { t } = useLocale()
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

  const { maxStage } = deriveReportProgressState(
    reportSteps,
    isDone,
  )

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
        const floor = stage <= 0 ? 0 : REPORT_PROGRESS_STAGE_END_PCT[stage - 1]
        const ceiling = REPORT_PROGRESS_STAGE_END_PCT[Math.min(Math.max(stage, 0), REPORT_PROGRESS_STAGE_END_PCT.length - 1)] - 0.8
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
  const reportGeneration = createReportGeneration({
    t,
    steps: reportSteps,
    isGenerating,
    isDone,
    error: reportError,
    percent: roundedPct,
  })

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
          {reportGeneration ? <ArtifactProgressCard icon={<FileText size={18} />} {...reportGeneration.card} /> : null}
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
