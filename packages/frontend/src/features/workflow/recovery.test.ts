import { describe, expect, it } from 'vitest'

import { buildWorkflowRecoveryState } from './recovery'

describe('workflowRecovery', () => {
  it('suggests datasource review for datasource execution failures', () => {
    const recovery = buildWorkflowRecoveryState({
      runPhase: {
        key: 'node-read-failed',
        label: 'Reading data failed',
        detail: 'Datasource connection timed out while loading the table.',
        status: 'error',
        suggestion: 'Open Attached data and verify the selected file or table.',
        nodeId: 'read_source',
        nodeType: 'datasource.read',
        source: 'workflow',
        updatedAt: Date.now(),
      },
      runError: null,
      error: null,
      activeFilePath: null,
      runOutput: '',
    })

    expect(recovery?.actions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ kind: 'open-datasources' }),
        expect.objectContaining({ kind: 'retry-run' }),
        expect.objectContaining({ kind: 'copy-diagnostics' }),
      ]),
    )
  })

  it('suggests opening the related file when one is available', () => {
    const recovery = buildWorkflowRecoveryState({
      runPhase: {
        key: 'node-report-failed',
        label: 'Writing report failed',
        detail: 'The generated report file could not be updated.',
        status: 'error',
        suggestion: 'Retry the report step or inspect the upstream data inputs.',
        nodeId: 'report_step',
        nodeType: 'report.generate',
        source: 'artifact',
        updatedAt: Date.now(),
      },
      runError: 'Could not update /workspace/reports/latest.html',
      error: null,
      activeFilePath: '/workspace/reports/latest.html',
      runOutput: '',
    })

    expect(recovery?.actions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ kind: 'open-related-file' }),
      ]),
    )
    expect(recovery?.diagnostics).toContain('/workspace/reports/latest.html')
  })

  it('returns null when there is no failure state', () => {
    const recovery = buildWorkflowRecoveryState({
      runPhase: {
        key: 'dashboard-ready',
        label: 'Dashboard preview ready',
        detail: 'Preview deployed and ready to open.',
        status: 'done',
        suggestion: null,
        nodeId: 'dashboard_node',
        nodeType: 'data.generate_dashboard',
        source: 'artifact',
        updatedAt: Date.now(),
      },
      runError: null,
      error: null,
      activeFilePath: null,
      runOutput: '',
    })

    expect(recovery).toBeNull()
  })
})
