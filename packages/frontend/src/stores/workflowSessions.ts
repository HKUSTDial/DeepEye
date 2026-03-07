import { create } from 'zustand'
import type { WorkflowArtifact, WorkflowDraft, WorkflowRun, WorkspaceState } from '../types'

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
  dashboardRefreshKey: number
  videoProgress: VideoProgressState
  /** URL of a ready video-preview container (set when video_preview_ready event fires) */
  videoPreviewUrl: string | null
  lastUpdated: number | null
}

interface WorkflowSessionsStore {
  sessions: Record<string, WorkflowSessionState>
  ensureSession: (sessionId: string) => WorkflowSessionState
  resetSession: (sessionId: string) => void
  hydrateWorkspaceState: (sessionId: string, snapshot: WorkspaceState | null) => void
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
  triggerDashboardRefresh: (sessionId: string) => void
  setVideoProgressVisible: (sessionId: string, visible: boolean) => void
  appendVideoProgressLog: (sessionId: string, message: string) => void
  setVideoProgressStep: (sessionId: string, step: number) => void
  setVideoProgressPercent: (sessionId: string, percent: number) => void
  setVideoPreviewUrl: (sessionId: string, url: string | null) => void
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
  dashboardRefreshKey: 0,
  videoProgress: { ...initialVideoProgress },
  videoPreviewUrl: null,
  lastUpdated: null,
})

const withSession = (state: WorkflowSessionsStore['sessions'], sessionId: string) =>
  state[sessionId] ?? createEmptySession()

const asObjectRecord = (value: unknown): Record<string, unknown> | null =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null

const getDraftDefinition = (draft: WorkflowDraft | null): WorkflowDefinition => {
  if (!draft) return null
  return asObjectRecord(draft.definition)
}

const deriveNodeStatus = (run: WorkflowRun | null) => {
  const result = asObjectRecord(run?.result)
  const outputs = asObjectRecord(result?.outputs)
  if (!outputs) {
    return {}
  }

  return Object.fromEntries(
    Object.entries(outputs)
      .filter(([, value]) => !!asObjectRecord(value))
      .map(([nodeId, value]) => {
        const outputsForNode = asObjectRecord(value) || {}
        const nodeStatus =
          typeof outputsForNode.status === 'string' && outputsForNode.status
            ? outputsForNode.status
            : 'completed'
        return [nodeId, { status: nodeStatus, outputs: outputsForNode }]
      }),
  )
}

const deriveRunOutput = (run: WorkflowRun | null) => {
  const result = asObjectRecord(run?.result)
  const outputs = asObjectRecord(result?.outputs)
  if (outputs) {
    return JSON.stringify(outputs, null, 2)
  }
  if (result) {
    return JSON.stringify(result, null, 2)
  }
  return run?.error || ''
}

const deriveVideoPreviewUrl = (run: WorkflowRun | null, artifacts: WorkflowArtifact[]) => {
  const videoArtifact = [...artifacts]
    .reverse()
    .find((artifact) => artifact.kind === 'video' && typeof artifact.payload?.video_url === 'string')
  if (videoArtifact && typeof videoArtifact.payload.video_url === 'string') {
    return videoArtifact.payload.video_url
  }

  const outputs = asObjectRecord(asObjectRecord(run?.result)?.outputs)
  if (!outputs) {
    return null
  }

  for (const value of Object.values(outputs)) {
    const nodeOutputs = asObjectRecord(value)
    if (typeof nodeOutputs?.video_url === 'string' && nodeOutputs.video_url) {
      return nodeOutputs.video_url
    }
  }

  return null
}

const deriveViewState = (definition: WorkflowDefinition, run: WorkflowRun | null): WorkflowViewState => {
  if (definition || run) {
    return 'ready'
  }
  return 'empty'
}

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
  hydrateWorkspaceState: (sessionId, snapshot) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      if (!snapshot?.turn) {
        return {
          sessions: {
            ...state.sessions,
            [sessionId]: {
              ...createEmptySession(),
              files: current.files,
              fileError: current.fileError,
              dashboardRefreshKey: current.dashboardRefreshKey,
              viewState: 'empty',
              lastUpdated: Date.now(),
            },
          },
        }
      }

      const draft = snapshot.draft ?? null
      const run = snapshot.run ?? null
      const artifacts = Array.isArray(snapshot.artifacts) ? snapshot.artifacts : []
      const definition = getDraftDefinition(draft)

      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...createEmptySession(),
            files: current.files,
            fileError: current.fileError,
            dashboardRefreshKey: current.dashboardRefreshKey,
            viewState: deriveViewState(definition, run),
            activeFilePath: draft?.file_path ?? run?.file_path ?? null,
            definition,
            nodeStatus: deriveNodeStatus(run),
            runStatus: run?.status ?? null,
            runError: run?.error ?? null,
            error: run?.status === 'failed' ? run?.error ?? null : null,
            activeRun: run,
            runOutput: deriveRunOutput(run),
            videoPreviewUrl: deriveVideoPreviewUrl(run, artifacts),
            lastUpdated: Date.now(),
          },
        },
      }
    }),
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
  triggerDashboardRefresh: (sessionId) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            dashboardRefreshKey: current.dashboardRefreshKey + 1,
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
      // 步骤 0..3 对应 0%, 25%, 50%, 75%；100% 仅在完成时由 setVideoProgressPercent 设置
      const percent = Math.min(99, Math.round((step / 4) * 100))
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
  setVideoProgressPercent: (sessionId, percent) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      const prev = current.videoProgress ?? initialVideoProgress
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            videoProgress: { ...prev, percent: Math.min(100, Math.max(0, percent)) },
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setVideoPreviewUrl: (sessionId, url) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      return {
        sessions: {
          ...state.sessions,
          [sessionId]: {
            ...current,
            videoPreviewUrl: url,
            lastUpdated: Date.now(),
          },
        },
      }
    }),
}))
