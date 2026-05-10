import { describe, expect, it } from 'vitest'

import {
  deriveReportProgressState,
  getReportProgressDisplayStep,
  parseReportProgressStage,
} from './reportProgress'

describe('reportProgress', () => {
  it('normalizes backend zero-based report progress messages', () => {
    expect(parseReportProgressStage('📂 [0/7] Loading and parsing data files...')).toBe(0)
    expect(parseReportProgressStage('🔍 [1/7] Generating dataset context...')).toBe(1)
    expect(parseReportProgressStage('✅ [7/7] Report saved to: /workspace/report.html')).toBe(6)
  })

  it('uses the same display step for chat badges and workspace stages', () => {
    expect(getReportProgressDisplayStep(0)).toBe(1)
    expect(getReportProgressDisplayStep(6)).toBe(7)
    expect(getReportProgressDisplayStep(99)).toBe(7)
  })

  it('derives stage statuses from raw report log lines', () => {
    const state = deriveReportProgressState(
      [
        '📂 [0/7] Loading and parsing data files...',
        '🔍 [1/7] Generating dataset context...',
      ],
      false,
    )

    expect(state.maxStage).toBe(1)
    expect(state.progressedCount).toBe(2)
    expect(state.stageStatuses.slice(0, 4)).toEqual(['done', 'active', 'pending', 'pending'])
  })
})
