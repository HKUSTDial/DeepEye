import { create } from 'zustand'
import type { WorkflowRun } from '../types'

export type WorkflowDefinition = Record<string, unknown> | null
export type WorkflowNode = Record<string, unknown>
export type WorkflowEdge = Record<string, unknown>

export type WorkflowViewState = 'idle' | 'switching' | 'ready' | 'empty' | 'error'

export interface VideoProgressLogEntry {
  id: string
  time: string
  message: string
}

export interface VideoProgressState {
  visible: boolean
  step: number
  percent: number
  logs: VideoProgressLogEntry[]
}

export interface WorkflowSessionState {
  files: string[]
  fileError: string | null
  viewState: WorkflowViewState
  activeFilePath: string | null
  definition: WorkflowDefinition
  draftNodes: Record<string, WorkflowNode>
  draftEdges: Record<string, WorkflowEdge>
  validatedNodes: Record<string, WorkflowNode>
  validatedEdges: Record<string, WorkflowEdge>
  nodeStatus: Record<string, { status: string; outputs?: Record<string, unknown> }>
  runStatus: string | null
  runError: string | null
  error: string | null
  activeRun: WorkflowRun | null
  runOutput: string
  videoProgress: VideoProgressState
  lastUpdated: number | null
}

interface WorkflowSessionsStore {
  sessions: Record<string, WorkflowSessionState>
  ensureSession: (sessionId: string) => WorkflowSessionState
  resetSession: (sessionId: string) => void
  setViewState: (sessionId: string, state: WorkflowViewState) => void
  setFiles: (sessionId: string, files: string[]) => void
  setFileError: (sessionId: string, error: string | null) => void
  setDefinition: (sessionId: string, definition: WorkflowDefinition) => void
  setActiveFilePath: (sessionId: string, path: string | null) => void
  clearDraft: (sessionId: string) => void
  addDraftNode: (sessionId: string, node: WorkflowNode) => void
  addDraftEdge: (sessionId: string, edge: WorkflowEdge) => void
  setValidatedGraph: (sessionId: string, nodes: Record<string, WorkflowNode>, edges: Record<string, WorkflowEdge>) => void
  clearValidated: (sessionId: string) => void
  updateDraftNodeParam: (sessionId: string, nodeId: string, key: string, value: string) => void
  setNodeStatus: (sessionId: string, nodeId: string, status: string, outputs?: Record<string, unknown>) => void
  setRunStatus: (sessionId: string, status: string | null, error?: string | null) => void
  setError: (sessionId: string, error: string | null) => void
  setActiveRun: (sessionId: string, run: WorkflowRun | null) => void
  setRunOutput: (sessionId: string, output: string) => void
  setVideoProgressVisible: (sessionId: string, visible: boolean) => void
  appendVideoProgressLog: (sessionId: string, message: string) => void
  setVideoProgressStep: (sessionId: string, step: number) => void
}

const initialVideoProgress: VideoProgressState = {
  visible: false,
  step: 0,
  percent: 0,
  logs: [],
}

const createEmptySession = (): WorkflowSessionState => ({
  files: [],
  fileError: null,
  viewState: 'idle',
  activeFilePath: null,
  definition: null,
  draftNodes: {},
  draftEdges: {},
  validatedNodes: {},
  validatedEdges: {},
  nodeStatus: {},
  runStatus: null,
  runError: null,
  error: null,
  activeRun: null,
  runOutput: '',
  videoProgress: { ...initialVideoProgress },
  lastUpdated: null,
})

const withSession = (state: WorkflowSessionsStore['sessions'], sessionId: string) =>
  state[sessionId] ?? createEmptySession()

export const useWorkflowSessionsStore = create<WorkflowSessionsStore>((set, get) => ({
  sessions: {},
  ensureSession: (sessionId) => {
    const existing = get().sessions[sessionId]
    if (existing) return existing
    const next = createEmptySession()
    set((state) => ({ sessions: { ...state.sessions, [sessionId]: next } }))
    return next
  },
  resetSession: (sessionId) =>
    set((state) => ({
      sessions: { ...state.sessions, [sessionId]: createEmptySession() },
    })),
  setViewState: (sessionId, viewState) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: { ...current, viewState, lastUpdated: Date.now() },
        },
      }
    }),
  setFiles: (sessionId, files) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: { ...current, files, lastUpdated: Date.now() },
        },
      }
    }),
  setFileError: (sessionId, fileError) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: { ...current, fileError, lastUpdated: Date.now() },
        },
      }
    }),
  setDefinition: (sessionId, definition) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: { ...current, definition, error: null, lastUpdated: Date.now() },
        },
      }
    }),
  setActiveFilePath: (sessionId, activeFilePath) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: { ...current, activeFilePath, lastUpdated: Date.now() },
        },
      }
    }),
  clearDraft: (sessionId) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            draftNodes: {},
            draftEdges: {},
            nodeStatus: {},
            runStatus: null,
            runError: null,
            error: null,
            activeRun: null,
            runOutput: '',
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  addDraftNode: (sessionId, node) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      const id =
        typeof node.id === 'string'
          ? node.id
          : `node-${Object.keys(current.draftNodes).length + 1}`
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            draftNodes: { ...current.draftNodes, [id]: node },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  addDraftEdge: (sessionId, edge) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      const id =
        typeof edge.id === 'string'
          ? edge.id
          : `edge-${Object.keys(current.draftEdges).length + 1}`
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            draftEdges: { ...current.draftEdges, [id]: edge },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setValidatedGraph: (sessionId, nodes, edges) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            validatedNodes: nodes,
            validatedEdges: edges,
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  clearValidated: (sessionId) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            validatedNodes: {},
            validatedEdges: {},
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  updateDraftNodeParam: (sessionId, nodeId, key, value) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      const existing = current.draftNodes[nodeId]
      if (!existing || typeof existing !== 'object') {
        return state
      }
      const params =
        typeof (existing as { params?: Record<string, unknown> }).params === 'object'
          ? (existing as { params?: Record<string, unknown> }).params || {}
          : {}
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            draftNodes: {
              ...current.draftNodes,
              [nodeId]: {
                ...existing,
                params: { ...params, [key]: value },
              },
            },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setNodeStatus: (sessionId, nodeId, status, outputs) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            nodeStatus: {
              ...current.nodeStatus,
              [nodeId]: { status, outputs },
            },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setRunStatus: (sessionId, status, error = null) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            runStatus: status,
            runError: error,
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setError: (sessionId, error) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            error,
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setActiveRun: (sessionId, activeRun) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            activeRun,
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setRunOutput: (sessionId, runOutput) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            runOutput,
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setVideoProgressVisible: (sessionId, visible) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            videoProgress: {
              visible,
              step: visible ? 0 : current.videoProgress?.step ?? 0,
              percent: visible ? 0 : current.videoProgress?.percent ?? 0,
              logs: visible ? [] : (current.videoProgress?.logs ?? []),
            },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  appendVideoProgressLog: (sessionId, message) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      const prev = current.videoProgress ?? initialVideoProgress
      const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      const entry: VideoProgressLogEntry = { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, time, message }
      const logs = [...prev.logs, entry].slice(-50)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            videoProgress: { ...prev, logs },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setVideoProgressStep: (sessionId, step) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      const prev = current.videoProgress ?? initialVideoProgress
      const percent = Math.min(100, Math.round(((step + 1) / 4) * 100))
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            videoProgress: { ...prev, step, percent },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
}))
