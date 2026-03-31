import { beforeEach, describe, expect, it } from 'vitest'

import { useWorkflowSessionsStore } from './workflowSessions'
import type { WorkspaceState } from '../types'

function resetWorkflowSessionsStore() {
  useWorkflowSessionsStore.setState({ sessions: {} })
}

describe('workflowSessions store', () => {
  beforeEach(() => {
    resetWorkflowSessionsStore()
  })

  it('replaces artifacts with the same kind and node id', () => {
    const store = useWorkflowSessionsStore.getState()

    store.recordArtifact('session-1', {
      kind: 'dashboard',
      node_id: 'node-1',
      dashboard_url: 'https://example.com/first',
    })
    store.recordArtifact('session-1', {
      kind: 'dashboard',
      node_id: 'node-1',
      dashboard_url: 'https://example.com/second',
    })

    const session = useWorkflowSessionsStore.getState().sessions['session-1']
    expect(session.artifacts).toHaveLength(1)
    expect(session.artifacts[0]?.dashboard_url).toBe('https://example.com/second')
  })

  it('hydrates artifact payloads and video preview from workspace snapshots', () => {
    const snapshot: WorkspaceState = {
      session_id: 'session-1',
      turn: null,
      draft: null,
      run: {
        id: 'run-1',
        status: 'success',
        session_id: 'session-1',
        created_at: '2026-03-31T00:00:00Z',
      },
      artifacts: [
        {
          id: 'artifact-dashboard',
          run_id: 'run-1',
          kind: 'dashboard',
          payload: {
            kind: 'dashboard',
            node_id: 'dashboard-node',
            dashboard_url: 'https://example.com/dashboard',
          },
          created_at: '2026-03-31T00:00:00Z',
        },
        {
          id: 'artifact-video',
          run_id: 'run-1',
          kind: 'video',
          payload: {
            kind: 'video',
            node_id: 'video-node',
            task_id: '20260331_010203',
            video_url: 'https://example.com/video',
          },
          created_at: '2026-03-31T00:00:01Z',
        },
      ],
    }

    useWorkflowSessionsStore.getState().hydrateWorkspaceState('session-1', snapshot)

    const session = useWorkflowSessionsStore.getState().sessions['session-1']
    expect(session.viewState).toBe('ready')
    expect(session.artifacts).toEqual([
      expect.objectContaining({
        kind: 'dashboard',
        dashboard_url: 'https://example.com/dashboard',
      }),
      expect.objectContaining({
        kind: 'video',
        task_id: '20260331_010203',
      }),
    ])
    expect(session.videoPreviewUrl).toBe('https://example.com/video')
    expect(session.runPhase).toEqual(
      expect.objectContaining({
        label: 'Video preview ready',
        status: 'done',
      }),
    )
  })
})
