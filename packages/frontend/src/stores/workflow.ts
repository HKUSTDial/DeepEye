import { create } from 'zustand'
import { applyEdgeChanges, applyNodeChanges, type Edge, type EdgeChange, type Node, type NodeChange } from 'reactflow'
import type { Workflow, WorkflowRun } from '../types'

interface WorkflowState {
  // Current workflow
  workflowId: string | null
  workflowName: string
  description: string
  isDirty: boolean
  
  // Canvas state
  nodes: Node[]
  edges: Edge[]
  selectedNodeId: string | null
  selectedNodeIds: string[]
  
  // Execution
  activeRun: WorkflowRun | null
  runOutput: string
  status: string | null
  
  // Workflows list
  workflows: Workflow[]
  
  // History for undo/redo
  history: Array<{ nodes: Node[]; edges: Edge[] }>
  historyIndex: number
  
  // Actions
  setWorkflowId: (id: string | null) => void
  setWorkflowName: (name: string) => void
  setDescription: (desc: string) => void
  setIsDirty: (dirty: boolean) => void
  
  setNodes: (nodes: Node[] | NodeChange[] | ((prev: Node[]) => Node[])) => void
  setEdges: (edges: Edge[] | EdgeChange[] | ((prev: Edge[]) => Edge[])) => void
  setSelectedNodeId: (id: string | null) => void
  setSelectedNodeIds: (ids: string[]) => void
  
  setActiveRun: (run: WorkflowRun | null) => void
  setRunOutput: (output: string) => void
  setStatus: (status: string | null) => void
  
  setWorkflows: (workflows: Workflow[]) => void
  
  addToHistory: (nodes: Node[], edges: Edge[]) => void
  undo: () => void
  redo: () => void
  canUndo: () => boolean
  canRedo: () => boolean
  
  reset: () => void
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  workflowId: null,
  workflowName: 'Untitled workflow',
  description: '',
  isDirty: false,
  
  nodes: [],
  edges: [],
  selectedNodeId: null,
  selectedNodeIds: [],
  
  activeRun: null,
  runOutput: '',
  status: null,
  
  workflows: [],
  
  history: [],
  historyIndex: -1,
  
  setWorkflowId: (id) => set({ workflowId: id }),
  setWorkflowName: (name) => set({ workflowName: name, isDirty: true }),
  setDescription: (desc) => set({ description: desc, isDirty: true }),
  setIsDirty: (dirty) => set({ isDirty: dirty }),
  
  setNodes: (nodes) =>
    set((state) => {
      const newNodes =
        typeof nodes === 'function'
          ? nodes(state.nodes)
          : Array.isArray(nodes) && nodes[0] && 'type' in nodes[0] && !('data' in nodes[0])
            ? applyNodeChanges(nodes as NodeChange[], state.nodes)
            : (nodes as Node[])
      return { nodes: newNodes, isDirty: true }
    }),
  
  setEdges: (edges) =>
    set((state) => {
      const newEdges =
        typeof edges === 'function'
          ? edges(state.edges)
          : Array.isArray(edges) && edges[0] && 'type' in edges[0] && !('source' in edges[0])
            ? applyEdgeChanges(edges as EdgeChange[], state.edges)
            : (edges as Edge[])
      return { edges: newEdges, isDirty: true }
    }),
  
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  setSelectedNodeIds: (ids) => set({ selectedNodeIds: ids }),
  
  setActiveRun: (run) => set({ activeRun: run }),
  setRunOutput: (output) => set({ runOutput: output }),
  setStatus: (status) => set({ status }),
  
  setWorkflows: (workflows) => set({ workflows }),
  
  addToHistory: (nodes, edges) =>
    set((state) => {
      const newHistory = state.history.slice(0, state.historyIndex + 1)
      newHistory.push({ nodes: JSON.parse(JSON.stringify(nodes)), edges: JSON.parse(JSON.stringify(edges)) })
      if (newHistory.length > 50) newHistory.shift()
      return {
        history: newHistory,
        historyIndex: newHistory.length - 1,
      }
    }),
  
  undo: () =>
    set((state) => {
      if (state.historyIndex > 0) {
        const newIndex = state.historyIndex - 1
        const snapshot = state.history[newIndex]
        return {
          nodes: JSON.parse(JSON.stringify(snapshot.nodes)),
          edges: JSON.parse(JSON.stringify(snapshot.edges)),
          historyIndex: newIndex,
          isDirty: true,
        }
      }
      return state
    }),
  
  redo: () =>
    set((state) => {
      if (state.historyIndex < state.history.length - 1) {
        const newIndex = state.historyIndex + 1
        const snapshot = state.history[newIndex]
        return {
          nodes: JSON.parse(JSON.stringify(snapshot.nodes)),
          edges: JSON.parse(JSON.stringify(snapshot.edges)),
          historyIndex: newIndex,
          isDirty: true,
        }
      }
      return state
    }),
  
  canUndo: () => get().historyIndex > 0,
  canRedo: () => get().historyIndex < get().history.length - 1,
  
  reset: () =>
    set({
      workflowId: null,
      workflowName: 'Untitled workflow',
      description: '',
      isDirty: false,
      nodes: [],
      edges: [],
      selectedNodeId: null,
      selectedNodeIds: [],
      activeRun: null,
      runOutput: '',
      status: null,
      history: [],
      historyIndex: -1,
    }),
}))

