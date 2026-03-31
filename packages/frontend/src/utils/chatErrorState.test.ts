import { describe, expect, it } from 'vitest'

import { deriveChatErrorState } from './chatErrorState'

describe('chatErrorState', () => {
  it('maps connection failures to a user-friendly state', () => {
    expect(deriveChatErrorState('Connection lost while streaming').title).toBe('Connection interrupted')
  })

  it('maps connection failures to a localized Chinese state', () => {
    expect(deriveChatErrorState('Connection lost while streaming', 'zh-CN').title).toBe('连接已中断')
  })

  it('maps backend readiness errors to a startup message', () => {
    expect(deriveChatErrorState('Backend is not ready or unreachable. 502 Bad Gateway').title).toBe('Backend is still starting')
  })

  it('falls back to a generic error state', () => {
    expect(deriveChatErrorState('unexpected failure').title).toBe('The reply stopped before completion')
  })
})
