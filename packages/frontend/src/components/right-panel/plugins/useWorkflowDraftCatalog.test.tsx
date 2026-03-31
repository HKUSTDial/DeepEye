import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useWorkflowDraftCatalog, type WorkflowSessionActions } from './useWorkflowDraftCatalog'

const { listWorkflowDraftsMock } = vi.hoisted(() => ({
  listWorkflowDraftsMock: vi.fn(),
}))

vi.mock('../../../api', () => ({
  sessionApi: {
    listWorkflowDrafts: listWorkflowDraftsMock,
  },
}))

function createActions(): WorkflowSessionActions {
  return {
    ensureSession: vi.fn(),
    setWorkflowError: vi.fn(),
    setRunStatus: vi.fn(),
    setWorkflowDefinition: vi.fn(),
    clearWorkflow: vi.fn(),
    addWorkflowNode: vi.fn(),
    addWorkflowEdge: vi.fn(),
    setActiveFilePath: vi.fn(),
    setActiveDraftId: vi.fn(),
    setActiveRun: vi.fn(),
    setRunOutput: vi.fn(),
    setViewState: vi.fn(),
    setFiles: vi.fn(),
    setFileError: vi.fn(),
    setValidatedGraph: vi.fn(),
    clearValidated: vi.fn(),
  }
}

async function flushEffects() {
  await Promise.resolve()
  await Promise.resolve()
  await new Promise((resolve) => setTimeout(resolve, 0))
}

function HookHarness({ actions }: { actions: WorkflowSessionActions }) {
  useWorkflowDraftCatalog({
    sessionId: 'session-1',
    sessionIdFromStore: 'session-1',
    sessionMessagesCount: 1,
    filesChangedTrigger: 0,
    isStreaming: false,
    nodeDefs: {},
    definition: null,
    activeRun: null,
    activeFiles: [],
    activeFilePath: null,
    activeDraftId: null,
    activeViewState: 'empty',
    activeDraftNodes: {},
    activeDraftEdges: {},
    activeValidatedNodes: {},
    activeValidatedEdges: {},
    actions,
  })
  return null
}

describe('useWorkflowDraftCatalog', () => {
  let container: HTMLDivElement
  let root: Root | null

  beforeEach(() => {
    ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
      true
    listWorkflowDraftsMock.mockReset()
    container = document.createElement('div')
    document.body.appendChild(container)
    root = createRoot(container)
  })

  afterEach(() => {
    act(() => {
      root?.unmount()
    })
    container.remove()
    root = null
    ;(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
      false
  })

  it('fetches workflow drafts only once on mount when the draft list state updates', async () => {
    listWorkflowDraftsMock.mockResolvedValue([])
    const actions = createActions()

    act(() => {
      root?.render(<HookHarness actions={actions} />)
    })
    await flushEffects()

    expect(listWorkflowDraftsMock).toHaveBeenCalledTimes(1)
    expect(listWorkflowDraftsMock).toHaveBeenCalledWith('session-1')
  })
})
