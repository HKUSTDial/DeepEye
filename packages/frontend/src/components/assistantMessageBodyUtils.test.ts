import { describe, expect, it } from 'vitest'

import { splitAssistantMessageSections } from './assistantMessageBodyUtils'

describe('assistantMessageBodyUtils', () => {
  it('splits process entries from final assistant text', () => {
    const sections = splitAssistantMessageSections({
      role: 'assistant',
      content: 'ignored',
      timeline: [
        { kind: 'text', content: 'Generating visualization config for the sales overview chart' },
        { kind: 'step', step: { type: 'tool', name: 'fetch_data', source: 'workflow', status: 'completed' } },
        { kind: 'text', content: 'Here is the final answer.' },
      ],
    })

    expect(sections.processEntries).toHaveLength(2)
    expect(sections.finalContent).toBe('Here is the final answer.')
  })

  it('falls back to steps and raw content when no timeline exists', () => {
    const sections = splitAssistantMessageSections({
      role: 'assistant',
      content: 'Summary',
      steps: [{ type: 'tool', name: 'analyze', source: 'workflow', status: 'completed' }],
    })

    expect(sections.processEntries).toHaveLength(1)
    expect(sections.finalContent).toBe('Summary')
  })
})
