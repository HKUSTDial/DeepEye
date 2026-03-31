import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SessionChat } from '../models/SessionChat'
import { disconnectSessionEventStream, ensureSessionEventStream } from './sessionEventStream'
import { useChatStore } from '../stores/chat'
import { useRightPanelStore } from '../stores/rightPanel'
import { useReportStore } from '../stores/report'
import { useWorkflowSessionsStore } from '../stores/workflowSessions'

const { createEventSourceMock } = vi.hoisted(() => ({
  createEventSourceMock: vi.fn(),
}))

vi.mock('../api', () => ({
  chatApi: {
    createEventSource: createEventSourceMock,
  },
  sandboxApi: {},
  sessionApi: {},
}))

class FakeEventSource {
  static CLOSED = 2

  readyState = 1
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onerror: (() => void) | null = null

  close() {
    this.readyState = FakeEventSource.CLOSED
  }

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent<string>)
  }
}

function resetFrontendStores() {
  window.localStorage.clear()
  useChatStore.setState({
    currentSession: null,
    sessions: [],
    isLoadingSessions: false,
    filesChangedTrigger: 0,
    sandboxReadySessionId: null,
    isSwitchingSession: false,
  })
  useRightPanelStore.setState({
    collapsed: true,
    panelRatio: 28,
    panes: [],
    activePaneId: null,
    activeSessionKey: null,
    sessionLayouts: {},
  })
  useReportStore.setState({ sessions: {} })
  useWorkflowSessionsStore.setState({ sessions: {} })
}

describe('sessionEventStream', () => {
  beforeEach(() => {
    vi.stubGlobal('EventSource', FakeEventSource)
    createEventSourceMock.mockReset()
    resetFrontendStores()
  })

  afterEach(() => {
    disconnectSessionEventStream()
    vi.unstubAllGlobals()
  })

  it('records dashboard artifacts and opens the dashboard tab from the shared stream', () => {
    useChatStore.setState({
      currentSession: new SessionChat('session-1', 'Session 1'),
    })

    const source = new FakeEventSource()
    createEventSourceMock.mockReturnValue(source)

    ensureSessionEventStream('session-1')
    source.emit({
      type: 'workflow_event',
      data: {
        phase: 'artifact_ready',
        payload: {
          artifact: {
            kind: 'dashboard',
            node_id: 'dashboard-node',
            dashboard_url: 'https://example.com/dashboard',
          },
        },
      },
    })

    const workflowSession = useWorkflowSessionsStore.getState().sessions['session-1']
    expect(workflowSession.artifacts).toEqual([
      expect.objectContaining({
        kind: 'dashboard',
        dashboard_url: 'https://example.com/dashboard',
      }),
    ])

    const tabs = useRightPanelStore.getState().panes.flatMap((pane) => pane.tabs)
    expect(tabs).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          pluginId: 'dashboard',
        }),
      ]),
    )
  })

  it('does not infer a video task id from prior assistant text on run_end', () => {
    const currentSession = new SessionChat('session-1', 'Session 1')
    currentSession.loadMessages([
      {
        role: 'assistant',
        content: 'Task ID: 20260331_010203',
      },
    ])
    useChatStore.setState({ currentSession })

    const source = new FakeEventSource()
    createEventSourceMock.mockReturnValue(source)

    ensureSessionEventStream('session-1')
    source.emit({
      type: 'workflow_event',
      data: {
        phase: 'run_end',
        run_id: 'run-1',
        draft_id: 'draft-1',
        payload: {
          status: 'success',
        },
      },
    })

    const workflowSession = useWorkflowSessionsStore.getState().sessions['session-1']
    const tabs = useRightPanelStore
      .getState()
      .panes.flatMap((pane) => pane.tabs)
      .filter((tab) => tab.pluginId === 'video-preview')

    expect(workflowSession.runStatus).toBe('success')
    expect(workflowSession.runOutput).toBe('')
    expect(workflowSession.artifacts).toEqual([])
    expect(tabs).toHaveLength(0)
  })
})
