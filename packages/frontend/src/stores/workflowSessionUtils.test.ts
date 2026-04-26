import { describe, expect, it } from 'vitest'

import {
  appendCappedLogEntry,
  createProgressLogEntry,
  deriveDashboardStageState,
  deriveNodeStatus,
  deriveVideoPreviewUrl,
  deriveVideoStepPercent,
} from './workflowSessionUtils'

describe('workflowSessionUtils', () => {
  it('derives node status from workflow run outputs', () => {
    const nodeStatus = deriveNodeStatus({
      id: 'run-1',
      status: 'success',
      session_id: 'session-1',
      created_at: '2026-03-31T00:00:00Z',
      result: {
        outputs: {
          nodeA: { status: 'running', value: 1 },
          nodeB: { value: 2 },
          nodeC: 'skip-me',
        },
      },
    })

    expect(nodeStatus).toEqual({
      nodeA: { status: 'running', outputs: { status: 'running', value: 1 } },
      nodeB: { status: 'completed', outputs: { value: 2 } },
    })
  })

  it('keeps the latest ready video preview artifact', () => {
    const url = deriveVideoPreviewUrl([
      {
        id: 'artifact-1',
        run_id: 'run-1',
        kind: 'video',
        payload: { kind: 'video', node_id: 'node-1', video_url: 'https://example.com/old' },
        created_at: '2026-03-31T00:00:00Z',
      },
      {
        id: 'artifact-2',
        run_id: 'run-1',
        kind: 'dashboard',
        payload: { kind: 'dashboard', node_id: 'node-2', dashboard_url: 'https://example.com/dashboard' },
        created_at: '2026-03-31T00:00:01Z',
      },
      {
        id: 'artifact-3',
        run_id: 'run-2',
        kind: 'video',
        payload: {
          kind: 'video',
          node_id: 'node-3',
          preview: { type: 'iframe', url: 'https://example.com/new' },
          video_url: 'https://example.com/fallback',
        },
        created_at: '2026-03-31T00:00:02Z',
      },
    ])

    expect(url).toBe('https://example.com/new')
  })

  it('caps progress logs and clamps derived progress values', () => {
    const entry = createProgressLogEntry('hello', new Date('2026-03-31T12:34:56Z'))
    const logs = Array.from({ length: 50 }, (_, index) => ({
      id: `old-${index}`,
      time: '00:00:00',
      message: `old-${index}`,
    }))
    const nextLogs = appendCappedLogEntry(logs, entry)

    expect(entry.time).toBe('12:34:56')
    expect(nextLogs).toHaveLength(50)
    expect(nextLogs.at(-1)).toEqual(entry)
    expect(deriveDashboardStageState(10, 2, 46)).toEqual({ stage: 5, percent: 94 })
    expect(deriveVideoStepPercent(3)).toBe(75)
  })
})
