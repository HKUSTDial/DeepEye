import { describe, expect, it } from 'vitest'

import { buildFollowUpPrompts, buildMessageActivityKey, buildStepActivityKey, hasText } from './chatBoxUtils'

describe('chatBoxUtils', () => {
  it('builds stable activity keys for nested steps and timelines', () => {
    expect(
      buildStepActivityKey([
        {
          type: 'tool',
          name: 'workflow_agent',
          source: 'supervisor',
          status: 'completed',
          subSteps: [
            {
              type: 'thought',
              name: 'plan',
              source: 'workflow',
              status: 'running',
            },
          ],
        },
      ]),
    ).toContain('workflow_agent')

    expect(
      buildMessageActivityKey({
        role: 'assistant',
        content: 'hello',
        timeline: [{ kind: 'text', content: 'hello', isStreaming: false }],
      }),
    ).toContain('assistant')
  })

  it('detects whether a message has meaningful text', () => {
    expect(hasText('  hello  ')).toBe(true)
    expect(hasText('   ')).toBe(false)
    expect(hasText(undefined)).toBe(false)
  })

  it('builds follow-up prompts based on the reply context', () => {
    expect(buildFollowUpPrompts('Create a dashboard from this analysis', true)[0]).toContain('dashboard')
    expect(buildFollowUpPrompts('Write an executive summary', true)[0]).toContain('executive')
    expect(buildFollowUpPrompts('Create a dashboard from this analysis', true, 'zh-CN')[0]).toContain('dashboard')
    expect(buildFollowUpPrompts('Plain answer', false)).toHaveLength(3)
  })
})
