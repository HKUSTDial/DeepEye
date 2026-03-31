import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SessionOutputCenter } from './SessionOutputCenter'
import { useWorkflowSessionsStore } from '../../stores/workflowSessions'

function resetWorkflowSessionsStore() {
  useWorkflowSessionsStore.setState({ sessions: {} })
}

describe('SessionOutputCenter', () => {
  let container: HTMLDivElement
  let root: Root | null

  beforeEach(() => {
    resetWorkflowSessionsStore()
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

  it('renders a placeholder when the session has no outputs yet', () => {
    useWorkflowSessionsStore.getState().ensureSession('session-1')

    act(() => {
      root?.render(<SessionOutputCenter sessionId="session-1" onOpenPanel={vi.fn()} />)
    })

    expect(container.innerHTML).toContain('Results from this thread will appear here.')
    expect(container.innerHTML).toContain('Latest Outputs')
  })

  it('renders workflow and artifact cards from the current session state', () => {
    useWorkflowSessionsStore.setState({
      sessions: {
        'session-1': {
          artifacts: [
            { kind: 'report', report_filename: 'summary.html' },
            { kind: 'dashboard', dashboard_url: 'https://example.com/dashboard' },
            { kind: 'video', task_id: '20260331_010203' },
          ],
          files: [],
          fileError: null,
          viewState: 'ready',
          activeFilePath: null,
          activeDraftId: null,
          definition: { root: { nodes: {}, edges: {} } },
          draftNodes: {},
          draftEdges: {},
          validatedNodes: {},
          validatedEdges: {},
          nodeStatus: {},
          runStatus: 'success',
          runError: null,
          error: null,
          runPhase: {
            key: 'workflow-complete',
            label: 'Workflow complete',
            detail: 'All workflow steps completed successfully.',
            status: 'done',
            suggestion: null,
            nodeId: null,
            nodeType: null,
            source: 'workflow',
            updatedAt: Date.now(),
          },
          activeRun: null,
          runOutput: '',
          dashboardRefreshKey: 0,
          dashboardProgress: { visible: false, stage: 0, percent: 0, logs: [] },
          videoProgress: { visible: false, step: 0, percent: 0, logs: [] },
          videoPreviewUrl: null,
          lastUpdated: Date.now(),
        },
      },
    })

    act(() => {
      root?.render(<SessionOutputCenter sessionId="session-1" onOpenPanel={vi.fn()} />)
    })

    expect(container.innerHTML).toContain('Workflow')
    expect(container.innerHTML).toContain('Report')
    expect(container.innerHTML).toContain('Dashboard')
    expect(container.innerHTML).toContain('Video')
    expect(container.innerHTML).toContain('summary.html')
    expect(container.innerHTML).toContain('task 20260331_010203')
  })
})
