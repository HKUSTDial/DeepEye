import { describe, expect, it } from 'vitest'

import {
  buildWorkflowExportFilename,
  getWorkflowMiniMapNodeColor,
  hasRenderableWorkflow,
} from './workflowPanelUtils'

describe('workflowPanelUtils', () => {
  it('builds a stable export filename from draft metadata', () => {
    expect(
      buildWorkflowExportFilename(
        {
          id: 'draft-12345678',
          session_id: 'session-1',
          user_id: 'user-1',
          source: 'workflow_editor',
          status: 'ready',
          file_path: '/workspace/workflow/demo.json',
          display_name: 'demo-workflow',
          definition: {},
          version: 1,
          created_at: '2026-03-31T00:00:00Z',
          updated_at: '2026-03-31T00:00:00Z',
        },
        'draft-12345678',
      ),
    ).toBe('demo-workflow.json')

    expect(buildWorkflowExportFilename(null, 'draft-12345678')).toBe('draft-draft-12.json')
    expect(buildWorkflowExportFilename(null, null)).toBe('workflow.json')
  })

  it('detects whether the workflow panel has anything renderable', () => {
    expect(hasRenderableWorkflow(null, {}, {})).toBe(false)
    expect(hasRenderableWorkflow({ root: {} }, {}, {})).toBe(true)
    expect(hasRenderableWorkflow(null, { nodeA: { id: 'nodeA', type: 'sql' } }, {})).toBe(true)
  })

  it('maps node run status to deterministic mini map colors', () => {
    expect(getWorkflowMiniMapNodeColor('running', true)).toBe('#7ed9ca')
    expect(getWorkflowMiniMapNodeColor('success', false)).toBe('#15803d')
    expect(getWorkflowMiniMapNodeColor('failed', true)).toBe('#ef4444')
    expect(getWorkflowMiniMapNodeColor(undefined, false)).toBe('#7aa59b')
  })
})
