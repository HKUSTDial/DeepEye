import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { ReportPanel } from './ReportPanel'
import { useReportStore } from '../../../stores/report'

function resetReportStore() {
  useReportStore.setState({ sessions: {} })
}

describe('ReportPanel', () => {
  let container: HTMLDivElement
  let root: Root | null

  beforeEach(() => {
    resetReportStore()
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
  })

  afterEach(() => {
    act(() => {
      root?.unmount()
    })
    container.remove()
    root = null
  })

  it('renders report HTML inside an isolated iframe sandbox', () => {
    useReportStore.setState({
      sessions: {
        'session-1': {
          reportHtml: '<!DOCTYPE html><html><body><script>window.top.location="/boom"</script></body></html>',
          reportSteps: [],
          reportFilename: 'report.html',
          reportError: null,
          isGenerating: false,
        },
      },
    })

    act(() => {
      root?.render(<ReportPanel sessionId="session-1" />)
    })

    const iframe = container.querySelector('iframe')
    expect(iframe).not.toBeNull()
    expect(iframe?.getAttribute('sandbox')).toBe('allow-scripts')
    expect(iframe?.getAttribute('srcdoc')).toContain('window.top.location')
  })
})
