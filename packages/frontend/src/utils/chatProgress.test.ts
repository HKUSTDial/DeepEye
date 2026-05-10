import { describe, expect, it } from 'vitest'

import { createReportProgressLine, parseChatProgressLine } from './chatProgress'

describe('chatProgress', () => {
  it('renders report timeline items from the shared report stage labels', () => {
    const progress = createReportProgressLine(2, 7, 'legacy label')

    expect(progress.tone).toBe('report')
    expect(progress.badge).toBe('Report 2/7')
    expect(progress.label).toBe('Generate dataset context')
  })

  it('parses raw report progress lines through the shared report stage mapping', () => {
    const progress = parseChatProgressLine('📈 [4/7] Planning and generating visual charts...')

    expect(progress).toEqual(
      expect.objectContaining({
        tone: 'report',
        badge: 'Report 5/7',
        label: 'Plan and generate visual charts',
        status: 'running',
      }),
    )
  })

  it('parses video progress lines through the shared video stage mapping', () => {
    const progress = parseChatProgressLine('Step 4/4 Done: Video generation completed')

    expect(progress).toEqual(
      expect.objectContaining({
        tone: 'video',
        badge: 'Video 4/4',
        label: 'Render components',
        status: 'done',
      }),
    )
  })
})
