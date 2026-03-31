import { describe, expect, it } from 'vitest'

import {
  buildWorkflowDraftFileList,
  hasTrackedWorkflowState,
  readWorkflowDraftGraph,
} from './workflowLiveControllerUtils'

describe('workflowLiveControllerUtils', () => {
  it('keeps the active file path at the front when it is not part of the draft list', () => {
    expect(
      buildWorkflowDraftFileList(
        [
          {
            id: 'draft-1',
            session_id: 'session-1',
            user_id: 'user-1',
            source: 'workflow_editor',
            status: 'ready',
            display_name: 'alpha',
            file_path: '/workspace/workflow/alpha.json',
            definition: {},
            version: 1,
            created_at: '2026-03-31T00:00:00Z',
            updated_at: '2026-03-31T00:00:00Z',
          },
        ],
        '/workspace/workflow/active.json',
      ),
    ).toEqual(['/workspace/workflow/active.json', '/workspace/workflow/alpha.json'])
  })

  it('detects whether the workspace already has tracked state', () => {
    expect(
      hasTrackedWorkflowState({
        definition: null,
        activeRun: null,
        activeDraftId: null,
        draftNodeCount: 0,
        draftEdgeCount: 0,
        validatedNodeCount: 0,
        validatedEdgeCount: 0,
      }),
    ).toBe(false)

    expect(
      hasTrackedWorkflowState({
        definition: null,
        activeRun: { id: 'run-1' },
        activeDraftId: null,
        draftNodeCount: 0,
        draftEdgeCount: 0,
        validatedNodeCount: 0,
        validatedEdgeCount: 0,
      }),
    ).toBe(true)
  })

  it('reads nodes and edges from a workflow draft definition', () => {
    expect(
      readWorkflowDraftGraph({
        id: 'draft-1',
        session_id: 'session-1',
        user_id: 'user-1',
        source: 'workflow_editor',
        status: 'ready',
        display_name: 'alpha',
        file_path: '/workspace/workflow/alpha.json',
        definition: {
          root: {
            nodes: {
              nodeA: { id: 'nodeA', type: 'sql' },
            },
            edges: {
              edgeA: { id: 'edgeA', source: 'nodeA', target: 'nodeB' },
            },
          },
        },
        version: 1,
        created_at: '2026-03-31T00:00:00Z',
        updated_at: '2026-03-31T00:00:00Z',
      }),
    ).toMatchObject({
      nodes: {
        nodeA: { id: 'nodeA', type: 'sql' },
      },
      edges: {
        edgeA: { id: 'edgeA', source: 'nodeA', target: 'nodeB' },
      },
    })
  })
})
