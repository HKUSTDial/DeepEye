import type { WorkflowDraft } from '../../../types'
import { dedupeFilePaths, type DefinitionEdge, type DefinitionNode } from './workflowPanelUtils'

export function buildWorkflowDraftFileList(
  drafts: WorkflowDraft[],
  activeFilePath: string | null,
): string[] {
  const draftPaths = dedupeFilePaths(drafts.map((draft) => draft.file_path))
  if (!activeFilePath || draftPaths.includes(activeFilePath)) {
    return draftPaths
  }
  return [activeFilePath, ...draftPaths]
}

export function hasTrackedWorkflowState(params: {
  definition: Record<string, unknown> | null
  activeRun: unknown | null
  activeDraftId: string | null
  draftNodeCount: number
  draftEdgeCount: number
  validatedNodeCount: number
  validatedEdgeCount: number
}) {
  return (
    !!params.definition ||
    !!params.activeRun ||
    !!params.activeDraftId ||
    params.draftNodeCount > 0 ||
    params.draftEdgeCount > 0 ||
    params.validatedNodeCount > 0 ||
    params.validatedEdgeCount > 0
  )
}

export function readWorkflowDraftGraph(draft: WorkflowDraft | null) {
  if (!draft || typeof draft.definition !== 'object') {
    throw new Error('Workflow draft is not available.')
  }

  const parsed = draft.definition
  const root = (parsed.root as Record<string, unknown>) || parsed
  const nodes = (root.nodes as Record<string, DefinitionNode>) || {}
  const edges = (root.edges as Record<string, DefinitionEdge>) || {}

  return {
    definition: parsed,
    nodes,
    edges,
  }
}
