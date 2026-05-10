import { describe, expect, it } from 'vitest'

import { parseVideoProgressStep } from './videoProgress'

describe('videoProgress', () => {
  it('normalizes one-based video progress messages into zero-based stage indexes', () => {
    expect(parseVideoProgressStep('Step 1/4: Generate scenes')).toBe(0)
    expect(parseVideoProgressStep('Step 4/4 Done: Video generation completed')).toBe(3)
    expect(parseVideoProgressStep('Step 9/4: overflow')).toBe(3)
  })
})
