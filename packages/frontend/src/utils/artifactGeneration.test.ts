import { describe, expect, it } from 'vitest'

import { translate, type MessageParams } from '../locale'
import {
  createDashboardGeneration,
  createReportGeneration,
  createVideoGeneration,
} from './artifactGeneration'

const t = (key: string, params?: MessageParams) => translate('en', key, params)

describe('artifactGeneration', () => {
  it('creates a unified report generation model from raw report steps', () => {
    const generation = createReportGeneration({
      t,
      steps: ['📂 [0/7] Loading and parsing data files...'],
      isGenerating: true,
      isDone: false,
      error: null,
      percent: 8,
    })

    expect(generation?.kind).toBe('report')
    expect(generation?.lifecycle).toBe('running')
    expect(generation?.card.status).toBe('running')
    expect(generation?.card.metrics?.[0]).toEqual({ label: 'Phases', value: '1/7' })
    expect(generation?.card.steps[0]).toEqual(
      expect.objectContaining({
        label: 'Load and parse data files',
        status: 'active',
      }),
    )
  })

  it('creates a unified dashboard warmup model', () => {
    const generation = createDashboardGeneration({
      t,
      isGenerating: false,
      isWarming: true,
      isReady: false,
      stage: 0,
      percent: 0,
      logs: [],
      nodeId: 'dashboard_node',
      healthCheckCount: 2,
    })

    expect(generation?.kind).toBe('dashboard')
    expect(generation?.lifecycle).toBe('warming')
    expect(generation?.card.statusLabel).toBe('Connecting')
    expect(generation?.card.metrics).toEqual(
      expect.arrayContaining([{ label: 'Node', value: 'dashboard_node' }]),
    )
    expect(generation?.card.steps.map((step) => step.id)).toEqual(['artifact', 'boot', 'probe', 'mount'])
  })

  it('creates a unified video rendering model', () => {
    const generation = createVideoGeneration({
      t,
      isRendering: true,
      isPreviewWarming: false,
      isPreviewReady: false,
      runFailed: false,
      step: 2,
      percent: 62,
      logs: [{ message: 'Step 3/4: Saving configuration file...' }],
      taskId: '20260510_164500',
      previewCheckCount: 0,
    })

    expect(generation?.kind).toBe('video')
    expect(generation?.lifecycle).toBe('running')
    expect(generation?.card.currentLabel).toBe('Step 3/4: Saving configuration file...')
    expect(generation?.card.metrics).toEqual(
      expect.arrayContaining([{ label: 'Task', value: '20260510_164500' }]),
    )
    expect(generation?.card.steps[2]).toEqual(
      expect.objectContaining({
        label: 'Save config',
        status: 'active',
      }),
    )
  })
})
