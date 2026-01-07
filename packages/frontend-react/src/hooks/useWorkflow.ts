import { useCallback, useRef } from 'react'
import type { Node, Edge } from 'reactflow'
import { workflowsApi } from '../api'
import { useWorkflowStore } from '../stores/workflow'
import { useAuthStore } from '../stores/auth'
import { API_BASE } from '../api/client'
import type { Workflow, WorkflowRun } from '../types'
import { useWorkflowNodesStore, type NodeDef } from '../stores/workflowNodes'

function typeToLabel(type: string) {
  return type
    .replace(/[._]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function toDefinition(nodes: Node[], edges: Edge[], nodeDefs: Record<string, NodeDef>) {
  const nodeMap: Record<string, any> = {}
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

  const edgeMap: Record<string, any> = {}
  edges.forEach((edge) => {
    const id = edge.id || `${edge.source}-${edge.sourceHandle}-${edge.target}-${edge.targetHandle}`
    edgeMap[id] = {
      id,
      source: { node_id: edge.source, port_id: edge.sourceHandle || 'rows' },
      target: { node_id: edge.target, port_id: edge.targetHandle || 'rows' },
      condition: edge.data?.condition || undefined,
      transform: edge.data?.transform || undefined,
    }
  })

  return { nodes: nodeMap, edges: edgeMap }
}

function fromDefinition(definition: any, nodeDefs: Record<string, NodeDef>) {
  const graph = definition.root || definition
  const nodes: Node[] = Object.values(graph.nodes || {}).map((node: any) => {
    const def = nodeDefs[node.type]
    return {
      id: node.id,
      type: 'workflowNode',
      position: node.metadata?.position || { x: 80, y: 80 },
      data: {
        type: node.type,
        label: typeToLabel(node.type),
        inputs: def?.inputs || [],
        outputs: def?.outputs || [],
        params: node.params || {},
      },
    }
  })

  const edges: Edge[] = Object.values(graph.edges || {}).map((edge: any) => ({
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
    const payload = { name: state.workflowName, description: state.description, definition }
    try {
      if (state.workflowId) {
        const updated = await workflowsApi.update(state.workflowId, payload)
        state.setStatus('Saved')
        state.setWorkflows(state.workflows.map((wf) => (wf.id === updated.id ? updated : wf)))
        state.setIsDirty(false)
        return updated
      } else {
        const created = await workflowsApi.create(payload as any)
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
    const token = useAuthStore.getState().accessToken
    const url = new URL(`${API_BASE}/workflows/runs/${run.id}/stream`)
    if (token) {
      url.searchParams.set('token', token)
    }
    
    const es = new EventSource(url)
    eventSourceRef.current = es

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as any
        if (payload.type === 'node') {
          useWorkflowStore.getState().setNodes((nodes) =>
            nodes.map((node) =>
              node.id === payload.node_id ? { ...node, data: { ...node.data, runStatus: payload.status } } : node,
            ),
          )
          return
        }
        if (payload.type === 'run') {
          const runState = useWorkflowStore.getState()
          runState.setActiveRun(payload as WorkflowRun)
          if (payload.status && payload.status !== 'running' && payload.status !== 'pending') {
            runState.setStatus(`Run ${payload.status}`)
            runState.setRunOutput(JSON.stringify(payload.result, null, 2))
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

