import { useState } from 'react'
import { useReportStore } from '../../../stores/report'

export function ReportPanel() {
  const reportHtml = useReportStore((s) => s.reportHtml)
  const reportSteps = useReportStore((s) => s.reportSteps)
  const reportFilename = useReportStore((s) => s.reportFilename)
  const reportError = useReportStore((s) => s.reportError)
  const [showSteps, setShowSteps] = useState(true)
  
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

  if (!reportHtml && reportSteps.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-[var(--main-text-muted)] p-6">
        <svg
          className="w-12 h-12 mb-4 opacity-50"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
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
      {/* Steps / log toggle */}
      {reportSteps.length > 0 && (
        <div className="flex-shrink-0 border-b border-[var(--border-color)]">
          <button
            type="button"
            onClick={() => setShowSteps(!showSteps)}
            className="w-full px-4 py-2 text-left text-sm font-medium text-[var(--main-text)] hover:bg-white/5 flex items-center justify-between"
          >
            <span>Generation steps {showSteps ? '▼' : '▶'}</span>
            <span className="text-xs text-[var(--main-text-muted)]">{reportSteps.length} lines</span>
          </button>
          {showSteps && (
            <div className="max-h-48 overflow-auto border-t border-[var(--border-color)] bg-[var(--sidebar-bg)]">
              <pre className="p-3 text-xs text-[var(--main-text)] whitespace-pre-wrap font-mono">
                {reportSteps.join('\n')}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Report HTML */}
      <div className="flex-1 min-h-0 overflow-auto p-4 flex flex-col">
        {reportError ? (
          <div className="flex flex-col items-center justify-center text-center p-6">
            <svg
              className="w-12 h-12 mb-4 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-sm font-medium text-red-500 mb-2">Report Generation Failed</p>
            <p className="text-xs text-[var(--main-text-muted)] max-w-md">
              {reportError}
            </p>
            <p className="text-xs text-[var(--main-text-muted)] mt-4">
              Check the generation steps above for more details.
            </p>
          </div>
        ) : reportHtml ? (
          <>
            <div className="flex-shrink-0 mb-3 flex items-center justify-between">
              <div className="text-xs text-[var(--main-text-muted)]">
                {reportFilename && (
                  <span>Report saved to workspace: <span className="font-mono">{reportFilename}</span></span>
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
              // Allow inline Plotly / JS in the generated report while keeping same-origin isolation
              sandbox="allow-same-origin allow-scripts"
            />
          </>
        ) : reportSteps.length > 0 ? (
          <div className="text-sm text-[var(--main-text-muted)]">
            Report is still generating… Check the steps above.
          </div>
        ) : null}
      </div>
    </div>
  )
}
