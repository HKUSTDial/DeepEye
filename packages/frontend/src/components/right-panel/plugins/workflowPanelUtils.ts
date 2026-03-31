import type { Edge, Node } from 'reactflow'

import type { WorkflowDraft, WorkflowRun } from '../../../types'
import type { NodeDef } from '../../../stores/workflowNodes'

export type DefinitionNode = {
  id: string
  type: string
  position?: { x?: number; y?: number }
  params?: Record<string, unknown>
  metadata?: { position?: { x?: number; y?: number } }
}

export type DefinitionEdge = {
  id: string
  source: { node_id: string; port_id?: string }
  target: { node_id: string; port_id?: string }
}

export type WorkflowNodeData = {
  type: string
  label: string
  inputs: Array<{ id: string; label: string }>
  outputs: Array<{ id: string; label: string }>
  params?: Record<string, unknown>
  runStatus?: string
  isNew?: boolean
}

export type WorkflowFlowNode = Node<WorkflowNodeData>
export type WorkflowFlowEdge = Edge

export function buildOptimisticRun(
  sessionId: string,
  filePath: string | null,
  status: string,
  options?: {
    error?: string | null
    taskId?: string | null
    turnId?: string | null
    draftId?: string | null
    runId?: string | null
  },
): WorkflowRun {
  return {
    id: options?.runId || options?.taskId || `pending:${sessionId}:${Date.now()}`,
    workflow_id: null,
    session_id: sessionId,
    turn_id: options?.turnId || null,
    draft_id: options?.draftId || null,
    file_path: filePath ?? null,
    source: 'workflow_editor',
    status,
    error: options?.error || undefined,
    created_at: new Date().toISOString(),
    finished_at: status === 'running' ? null : new Date().toISOString(),
  }
}

export function typeToLabel(type: unknown) {
  if (typeof type !== 'string' || !type.trim()) {
    return 'Unknown Node'
  }
  return type
    .replace(/[._]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

export function dedupeFilePaths(paths: Array<string | null | undefined>) {
  return [...new Set(paths.filter((path): path is string => typeof path === 'string' && path.length > 0))]
}

export function getDraftDisplayName(draft: WorkflowDraft) {
  if (draft.display_name?.trim()) return draft.display_name.trim()
  const fileName = draft.file_path?.split('/').pop()?.replace(/\.json$/i, '')
  if (fileName) return fileName
  return `draft-${draft.id.slice(0, 8)}`
}

export function buildWorkflowExportFilename(
  activeDraft: WorkflowDraft | null,
  activeDraftId: string | null,
) {
  return (
    (activeDraft?.display_name ? `${activeDraft.display_name}.json` : null) ||
    (activeDraftId ? `draft-${activeDraftId.slice(0, 8)}.json` : 'workflow.json')
  )
}

export function hasRenderableWorkflow(
  definition: WorkflowDefinitionLike,
  validatedNodes: Record<string, DefinitionNode>,
  validatedEdges: Record<string, DefinitionEdge>,
) {
  return !!definition || Object.keys(validatedNodes).length > 0 || Object.keys(validatedEdges).length > 0
}

export function getWorkflowMiniMapNodeColor(
  runStatus: string | undefined,
  isDark: boolean,
) {
  switch (runStatus) {
    case 'running':
      return isDark ? '#7ed9ca' : '#0f766e'
    case 'success':
      return isDark ? '#4ade80' : '#15803d'
    case 'failed':
      return '#ef4444'
    case 'pending':
      return isDark ? '#f3b560' : '#c27a1a'
    default:
      return isDark ? '#385250' : '#7aa59b'
  }
}

type WorkflowDefinitionLike = Record<string, unknown> | null

export function validateGraph(
  nodesMap: Record<string, DefinitionNode>,
  edgesMap: Record<string, DefinitionEdge>,
  nodeDefs: Record<string, NodeDef>,
) {
  if (Object.keys(nodeDefs).length === 0) {
    return null
  }
  for (const node of Object.values(nodesMap)) {
    if (!node || typeof node.type !== 'string') {
      return 'Invalid node definition.'
    }
    if (!nodeDefs[node.type]) {
      return `Unknown node type: ${node.type}`
    }
  }
  for (const edge of Object.values(edgesMap)) {
    if (!edge?.source?.node_id || !edge?.target?.node_id) {
      return 'Invalid edge definition.'
    }
    if (!nodesMap[edge.source.node_id] || !nodesMap[edge.target.node_id]) {
      return 'Edge references missing node.'
    }
  }
  return null
}

export function toFlow(definition: Record<string, unknown>, nodeDefs: Record<string, NodeDef>) {
  const root = (definition.root as Record<string, unknown>) || definition
  const nodesMap = (root.nodes as Record<string, DefinitionNode>) || {}
  const edgesMap = (root.edges as Record<string, DefinitionEdge>) || {}

  const nodes = Object.values(nodesMap).map((node) => {
    const def = nodeDefs[node.type]
    const xRaw = node.metadata?.position?.x ?? node.position?.x
    const yRaw = node.metadata?.position?.y ?? node.position?.y
    const x = typeof xRaw === 'number' ? xRaw : Number(xRaw)
    const y = typeof yRaw === 'number' ? yRaw : Number(yRaw)
    return {
      id: node.id,
      type: 'workflowNode',
      position: {
        x: Number.isFinite(x) ? x : 80,
        y: Number.isFinite(y) ? y : 80,
      },
      data: {
        type: node.type,
        label: typeToLabel(node.type),
        inputs: def?.inputs || [],
        outputs: def?.outputs || [],
        params: node.params || {},
      },
    }
  })

  const edges = Object.values(edgesMap)
    .filter((edge) => edge?.source?.node_id && edge?.target?.node_id)
    .map((edge) => ({
      id: edge.id,
      source: edge.source.node_id,
      target: edge.target.node_id,
      sourceHandle: edge.source.port_id,
      targetHandle: edge.target.port_id,
      animated: false,
      style: { stroke: 'var(--workflow-link)', strokeWidth: 2.25 },
    }))

  return { nodes, edges }
}

export function toDefinition(
  nodes: WorkflowFlowNode[],
  edges: WorkflowFlowEdge[],
  nodeDefs: Record<string, NodeDef>,
) {
  const nodeMap: Record<string, Record<string, unknown>> = {}
  nodes.forEach((node) => {
    const def = nodeDefs[node.data.type]
    if (!def) return
    nodeMap[node.id] = {
      id: node.id,
      type: node.data.type,
      inputs: Object.fromEntries(
        def.inputs.map((p) => [p.id, { schema: p.schema, required: !!p.required, multiple: p.multiple }]),
      ),
      outputs: Object.fromEntries(def.outputs.map((p) => [p.id, { schema: p.schema }])),
      params: node.data.params || {},
      metadata: { position: node.position },
    }
  })

  const edgeMap: Record<string, Record<string, unknown>> = {}
  edges.forEach((edge) => {
    const id = edge.id || `${edge.source}-${edge.sourceHandle}-${edge.target}-${edge.targetHandle}`
    edgeMap[id] = {
      id,
      source: { node_id: edge.source, port_id: edge.sourceHandle || 'rows' },
      target: { node_id: edge.target, port_id: edge.targetHandle || 'rows' },
    }
  })

  return { root: { nodes: nodeMap, edges: edgeMap } }
}
