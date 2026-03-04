import { useRef, useState, useEffect } from 'react'
import { useReportStore } from '../../../stores/report'

const STAGES = [
  { label: 'Load and parse data files', icon: '📂' },
  { label: 'Generate dataset context', icon: '🔍' },
  { label: 'Perform deep exploratory analysis (EDA)', icon: '🕵️' },
  { label: 'Calculate key business indicators (KPI)', icon: '📊' },
  { label: 'Plan and generate visual charts', icon: '📈' },
  { label: 'Write analysis summary and conclusions', icon: '✍️' },
  { label: 'Render final HTML report', icon: '🎨' },
]

// Expected end-percent for each stage – matches pipeline step order
const STAGE_END_PCT = [8, 22, 42, 58, 82, 93, 100]

type StageStatus = 'done' | 'active' | 'warning' | 'pending'

function parseStages(
  steps: string[],
  isDone: boolean,
): { stageStatuses: StageStatus[]; maxStage: number } {
  let maxStage = -1
  const warningStages = new Set<number>()
  let lastStageIdx = -1

  for (const line of steps) {
    const m = line.match(/\[(\d+)\/7\]/)
    if (m) {
      const idx = Math.min(parseInt(m[1], 10), 6)
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

  const stageStatuses: StageStatus[] = STAGES.map((_, i) => {
    if (isDone || i < maxStage) return warningStages.has(i) ? 'warning' : 'done'
    if (i === maxStage) return isDone ? (warningStages.has(i) ? 'warning' : 'done') : 'active'
    return 'pending'
  })

  return { stageStatuses, maxStage }
}

export function ReportPanel() {
  const reportHtml = useReportStore((s) => s.reportHtml)
  const reportSteps = useReportStore((s) => s.reportSteps)
  const reportFilename = useReportStore((s) => s.reportFilename)
  const reportError = useReportStore((s) => s.reportError)
  const isGenerating = useReportStore((s) => s.isGenerating)

  const [displayPercent, setDisplayPercent] = useState(0)
  // Only track the committed stage index – mirroring index.html's _committedStage
  const committedStageRef = useRef(-1)

  const isDone = !!reportHtml
  const showProgress = !isDone && (isGenerating || reportSteps.length > 0) && !reportError

  const { stageStatuses, maxStage } = parseStages(reportSteps, isDone)

  // Keep committedStage in sync; never go backwards
  useEffect(() => {
    if (maxStage > committedStageRef.current) {
      committedStageRef.current = maxStage
    }
  }, [maxStage])

  // Snap to 100% when done
  useEffect(() => {
    if (isDone) setDisplayPercent(100)
  }, [isDone])

  // Tween – fires every 150 ms, identical logic to index.html's startTween()
  //
  //  1. Compute floor  = end of previous stage  (guarantee we never slip behind)
  //  2. Compute ceiling = end of current stage - 0.8  (wait for server confirmation)
  //  3. Creep toward ceiling with exponential decay; fast when far, slow when close
  //
  // Because ceiling advances every time a new [N/7] log arrives, the bar moves
  // continuously through every stage without ever stopping or jumping.
  useEffect(() => {
    if (!showProgress || isDone) return
    const id = setInterval(() => {
      setDisplayPercent((prev) => {
        const stage = committedStageRef.current
        // floor: start of current stage (= end of previous stage, or 0)
        const floor = stage <= 0 ? 0 : STAGE_END_PCT[stage - 1]
        // ceiling: just below end of current stage
        const ceiling = STAGE_END_PCT[Math.min(Math.max(stage, 0), STAGE_END_PCT.length - 1)] - 0.8
        // Snap up to floor if we've fallen behind (stage jumped forward)
        const current = Math.max(prev, floor)
        if (current >= ceiling) return current
        // Exponential decay: fast when far from ceiling, slow when close
        const gap = ceiling - current
        const step = Math.max(0.03, gap * 0.012)
        return Math.min(current + step, ceiling)
      })
    }, 150)
    return () => clearInterval(id)
  }, [showProgress, isDone])

  // Full reset when a new generation starts (showProgress goes false → true)
  useEffect(() => {
    if (!showProgress) {
      committedStageRef.current = -1
      setDisplayPercent(0)
    }
  }, [showProgress])

  const handleDownload = () => {
    if (!reportHtml) return
    const blob = new Blob([reportHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = reportFilename || 'report.html'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Displayed integer percent (for the counter label)
  const roundedPct = isDone ? 100 : Math.round(displayPercent)

  if (!reportHtml && reportSteps.length === 0 && !isGenerating) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-[var(--main-text-muted)] p-6">
        <svg className="w-12 h-12 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-sm">No report yet</p>
        <p className="text-xs mt-1 opacity-75">
          Upload CSV file(s) and describe the report you want. The report will appear here when ready.
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[var(--panel-bg)]">

      {/* Progress section – hidden when report is done to free space */}
      {showProgress && (
        <div
          className="flex-shrink-0 border-b border-[var(--border-color)] px-4 pt-4 pb-3"
          style={{ background: 'rgba(255,255,255,0.03)' }}
        >
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">⚡</span>
            <span className="text-sm font-bold" style={{ color: '#a5b4fc' }}>
              Generating Report
            </span>
          </div>

          <div className="mb-3">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-xs font-semibold" style={{ color: '#a5b4fc' }}>Progress</span>
              <span className="text-xs font-bold tabular-nums" style={{ color: '#818cf8' }}>
                {roundedPct}%
              </span>
            </div>
            <div
              className="h-1.5 rounded-full overflow-hidden"
              style={{ background: 'rgba(129,140,248,0.18)' }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${displayPercent}%`,
                  background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                  transition: 'width 0.6s ease',
                }}
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            {STAGES.map((stage, i) => {
              const status = stageStatuses[i]
              return (
                <div
                  key={i}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all duration-300"
                  style={{
                    border: `1px solid ${
                      status === 'active'
                        ? 'rgba(99,179,237,0.5)'
                        : status === 'done'
                        ? 'rgba(104,211,145,0.35)'
                        : status === 'warning'
                        ? 'rgba(251,191,36,0.4)'
                        : 'rgba(255,255,255,0.12)'
                    }`,
                    background:
                      status === 'active'
                        ? 'rgba(99,179,237,0.1)'
                        : status === 'done'
                        ? 'rgba(104,211,145,0.08)'
                        : status === 'warning'
                        ? 'rgba(251,191,36,0.08)'
                        : 'rgba(255,255,255,0.04)',
                  }}
                >
                  <span
                    className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm transition-all duration-300"
                    style={{
                      border: `1px solid ${
                        status === 'active'
                          ? 'rgba(99,179,237,0.6)'
                          : status === 'done'
                          ? 'rgba(104,211,145,0.5)'
                          : status === 'warning'
                          ? 'rgba(251,191,36,0.5)'
                          : 'rgba(255,255,255,0.15)'
                      }`,
                      background:
                        status === 'active'
                          ? 'rgba(99,179,237,0.18)'
                          : status === 'done'
                          ? 'rgba(104,211,145,0.15)'
                          : status === 'warning'
                          ? 'rgba(251,191,36,0.15)'
                          : 'rgba(255,255,255,0.06)',
                      animation: status === 'active' ? 'pulse-ring 1.6s ease-in-out infinite' : undefined,
                    }}
                  >
                    {status === 'done' ? '✓' : stage.icon}
                  </span>

                  <span
                    className="text-xs transition-colors duration-300"
                    style={{
                      color:
                        status === 'active'
                          ? '#e0e7ff'
                          : status === 'done'
                          ? '#c4b5fd'
                          : status === 'warning'
                          ? '#fbbf24'
                          : '#a5b4fc',
                      fontWeight: status === 'active' ? 700 : 500,
                    }}
                  >
                    {stage.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-auto p-4 flex flex-col">
        {reportError ? (
          <div className="flex flex-col items-center justify-center text-center p-6">
            <svg className="w-12 h-12 mb-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-sm font-medium text-red-500 mb-2">Report Generation Failed</p>
            <p className="text-xs text-[var(--main-text)] max-w-md">{reportError}</p>
          </div>
        ) : reportHtml ? (
          <>
            <div className="flex-shrink-0 mb-3 flex items-center justify-between">
              <div className="text-xs font-medium text-[var(--main-text)]">
                {reportFilename && (
                  <span>
                    Report saved to workspace: <span className="font-mono">{reportFilename}</span>
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={handleDownload}
                className="px-3 py-1 text-xs font-medium rounded-md bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
              >
                Download HTML
              </button>
            </div>
            <iframe
              title="Report"
              srcDoc={reportHtml}
              className="flex-1 w-full min-h-[400px] border-0 rounded-lg bg-white text-black"
              sandbox="allow-same-origin allow-scripts"
            />
          </>
        ) : isGenerating ? (
          <div className="flex items-center justify-center text-xs font-semibold py-4" style={{ color: '#a5b4fc' }}>
            The report is being generated, please wait...
          </div>
        ) : null}
      </div>

      <style>{`
        @keyframes pulse-ring {
          0%, 100% { box-shadow: 0 0 0 0 rgba(99,179,237,0.4); }
          50%       { box-shadow: 0 0 0 6px rgba(99,179,237,0); }
        }
      `}</style>
    </div>
  )
}
