import { useCallback, useRef } from 'react'
import type { Node, Edge } from 'reactflow'
import { workflowsApi } from '../api'
import { useWorkflowStore } from '../stores/workflow'
import { API_BASE } from '../api/client'
import type { Workflow, WorkflowRun } from '../types'
import { useWorkflowNodesStore, type NodeDef } from '../stores/workflowNodes'

type WorkflowCanvasNodeData = {
  type: string
  params?: Record<string, unknown>
}

type WorkflowCanvasNode = Node<WorkflowCanvasNodeData>

type WorkflowDefinitionNode = {
  id: string
  type: string
  metadata?: {
    position?: {
      x?: number
      y?: number
    }
  }
  params?: Record<string, unknown>
}

type WorkflowDefinitionEdge = {
  id: string
  source: { node_id: string; port_id?: string }
  target: { node_id: string; port_id?: string }
  condition?: unknown
  transform?: unknown
}

type WorkflowDefinitionGraph = {
  nodes?: Record<string, WorkflowDefinitionNode>
  edges?: Record<string, WorkflowDefinitionEdge>
}

function typeToLabel(type: string) {
  return type
    .replace(/[._]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function toDefinition(nodes: WorkflowCanvasNode[], edges: Edge[], nodeDefs: Record<string, NodeDef>) {
  const nodeMap: Record<string, Record<string, unknown>> = {}
  nodes.forEach((node) => {
    const def = nodeDefs[node.data.type]
    if (!def) return
    nodeMap[node.id] = {
      id: node.id,
      type: node.data.type,
      params: node.data.params || {},
      metadata: { position: node.position },
    }
  })

  const edgeMap: Record<string, Record<string, unknown>> = {}
  edges.forEach((edge) => {
    const id = edge.id || `${edge.source}-${edge.sourceHandle}-${edge.target}-${edge.targetHandle}`
    const edgeData = (edge.data as { condition?: unknown; transform?: unknown } | undefined) ?? {}
    edgeMap[id] = {
      id,
      source: { node_id: edge.source, port_id: edge.sourceHandle || 'rows' },
      target: { node_id: edge.target, port_id: edge.targetHandle || 'rows' },
      condition: edgeData.condition,
      transform: edgeData.transform,
    }
  })

  return { nodes: nodeMap, edges: edgeMap }
}

function fromDefinition(definition: Record<string, unknown>, nodeDefs: Record<string, NodeDef>) {
  const graph = ((definition.root as WorkflowDefinitionGraph | undefined) || definition) as WorkflowDefinitionGraph
  const nodes: Node[] = Object.values(graph.nodes || {}).map((node) => {
    const def = nodeDefs[node.type]
    const xRaw = node.metadata?.position?.x
    const yRaw = node.metadata?.position?.y
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

  const edges: Edge[] = Object.values(graph.edges || {}).map((edge) => ({
    id: edge.id,
    source: edge.source.node_id,
    target: edge.target.node_id,
    sourceHandle: edge.source.port_id,
    targetHandle: edge.target.port_id,
    data: { condition: edge.condition, transform: edge.transform },
  }))

  return { nodes, edges }
}

export function useWorkflow() {
  const eventSourceRef = useRef<EventSource | null>(null)
  const nodeDefs = useWorkflowNodesStore((state) => state.nodeDefs)

  const loadWorkflows = useCallback(async () => {
    try {
      const workflows = await workflowsApi.list()
      useWorkflowStore.getState().setWorkflows(workflows)
    } catch {
      useWorkflowStore.getState().setWorkflows([])
    }
  }, [])

  const loadWorkflow = useCallback(
    (wf: Workflow) => {
      const { nodes, edges } = fromDefinition(wf.definition, nodeDefs)
      const state = useWorkflowStore.getState()
      state.setWorkflowId(wf.id)
      state.setWorkflowName(wf.name)
      state.setDescription(wf.description || '')
      state.setNodes(nodes)
      state.setEdges(edges)
      state.setSelectedNodeId(null)
      state.setSelectedNodeIds([])
      state.setActiveRun(null)
      state.setRunOutput('')
      state.setIsDirty(false)
      state.addToHistory(nodes, edges)
    },
    [nodeDefs],
  )

  const saveWorkflow = useCallback(async (): Promise<Workflow | null> => {
    const state = useWorkflowStore.getState()
    const definition = { root: toDefinition(state.nodes, state.edges, nodeDefs) }
    const payload: Omit<Workflow, 'id' | 'created_at' | 'updated_at'> = {
      name: state.workflowName,
      description: state.description,
      definition,
    }
    try {
      if (state.workflowId) {
        const updated = await workflowsApi.update(state.workflowId, payload)
        state.setStatus('Saved')
        state.setWorkflows(state.workflows.map((wf) => (wf.id === updated.id ? updated : wf)))
        state.setIsDirty(false)
        return updated
      } else {
        const created = await workflowsApi.create(payload)
        state.setWorkflowId(created.id)
        state.setStatus('Created')
        state.setWorkflows([...state.workflows, created])
        state.setIsDirty(false)
        return created
      }
    } catch {
      state.setStatus('Save failed')
    }
    return null
  }, [nodeDefs])

  const deleteWorkflow = useCallback(async (workflowId: string) => {
    const state = useWorkflowStore.getState()
    try {
      await workflowsApi.delete(workflowId)
      state.setWorkflows(state.workflows.filter((wf) => wf.id !== workflowId))
      if (state.workflowId === workflowId) {
        state.reset()
      }
    } catch {
      state.setStatus('Delete failed')
    }
  }, [])

  const runWorkflow = useCallback(async () => {
    const state = useWorkflowStore.getState()
    let id = state.workflowId
    if (!id || state.isDirty) {
      const saved = await saveWorkflow()
      if (!saved) return
      id = saved.id
    }
    
    state.setStatus('Running...')
    state.setRunOutput('')
    state.setNodes((nodes) => nodes.map((node) => ({ ...node, data: { ...node.data, runStatus: undefined } })))
    
    const run = await workflowsApi.run(id)
    state.setActiveRun(run)
    
    eventSourceRef.current?.close()
    // Support relative paths (e.g. /api/v1) for VITE_API_URL
    const url = new URL(
      `${API_BASE}/workflows/runs/${run.id}/stream`,
      window.location.origin
    )
    
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as Record<string, unknown>
        const payloadType = typeof payload.type === 'string' ? payload.type : ''
        if (payloadType === 'node') {
          const nodeId = typeof payload.node_id === 'string' ? payload.node_id : null
          const status = typeof payload.status === 'string' ? payload.status : undefined
          if (!nodeId) return
          useWorkflowStore.getState().setNodes((nodes) =>
            nodes.map((node) =>
              node.id === nodeId ? { ...node, data: { ...node.data, runStatus: status } } : node,
            ),
          )
          return
        }
        if (payloadType === 'run') {
          const status = typeof payload.status === 'string' ? payload.status : undefined
          const runState = useWorkflowStore.getState()
          runState.setActiveRun(payload as unknown as WorkflowRun)
          if (status && status !== 'running' && status !== 'pending') {
            runState.setStatus(`Run ${status}`)
            runState.setRunOutput(JSON.stringify(payload.result ?? null, null, 2))
            es.close()
          }
        }
      } catch {
        // ignore invalid payloads
      }
    }
    
    es.onerror = () => {
      useWorkflowStore.getState().setStatus('Run stream error')
      es.close()
    }
  }, [saveWorkflow])

  const addNode = useCallback(
    (type: string) => {
      const def = nodeDefs[type]
      if (!def) return
      
      const id = `${type}-${Date.now()}`
      const state = useWorkflowStore.getState()
      const newNode: Node = {
        id,
        type: 'workflowNode',
        position: { x: 120 + state.nodes.length * 30, y: 120 + state.nodes.length * 30 },
        data: {
          type,
          label: def.label,
          inputs: def.inputs.map((p) => ({ id: p.id, label: p.label })),
          outputs: def.outputs.map((p) => ({ id: p.id, label: p.label })),
          params: Object.fromEntries(Object.entries(def.params).map(([key, param]) => [key, param.default])),
        },
      }
      
      const newNodes = [...state.nodes, newNode]
      state.setNodes(newNodes)
      state.addToHistory(newNodes, state.edges)
    },
    [nodeDefs],
  )

  const deleteNode = useCallback(
    (nodeId: string) => {
      const state = useWorkflowStore.getState()
      const newNodes = state.nodes.filter((node) => node.id !== nodeId)
      const newEdges = state.edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
      state.setNodes(newNodes)
      state.setEdges(newEdges)
      if (state.selectedNodeId === nodeId) {
        state.setSelectedNodeId(null)
      }
      if (state.selectedNodeIds.length > 0) {
        state.setSelectedNodeIds(state.selectedNodeIds.filter((id) => id !== nodeId))
      }
      state.addToHistory(newNodes, newEdges)
    },
    [],
  )

  const deleteNodes = useCallback((nodeIds: string[]) => {
    if (nodeIds.length === 0) return
    const state = useWorkflowStore.getState()
    const newNodes = state.nodes.filter((node) => !nodeIds.includes(node.id))
    const newEdges = state.edges.filter(
      (edge) => !nodeIds.includes(edge.source) && !nodeIds.includes(edge.target),
    )
    state.setNodes(newNodes)
    state.setEdges(newEdges)
    state.setSelectedNodeId(null)
    state.setSelectedNodeIds([])
    state.addToHistory(newNodes, newEdges)
  }, [])

  const updateNodeParam = useCallback(
    (nodeId: string, key: string, value: string) => {
      const state = useWorkflowStore.getState()
      const newNodes = state.nodes.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, params: { ...node.data.params, [key]: value } } } : node,
      )
      state.setNodes(newNodes)
    },
    [],
  )

  const cleanup = useCallback(() => {
    eventSourceRef.current?.close()
  }, [])

  return {
    loadWorkflows,
    loadWorkflow,
    saveWorkflow,
    deleteWorkflow,
    runWorkflow,
    addNode,
    deleteNode,
    deleteNodes,
    updateNodeParam,
    cleanup,
    nodeDefs,
  }
}
