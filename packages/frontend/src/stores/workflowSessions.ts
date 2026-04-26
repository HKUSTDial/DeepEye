import { create } from 'zustand'
import type {
  WorkflowArtifactPayload,
  WorkflowRun,
  WorkspaceState,
} from '../types'
import type { WorkflowRunPhaseState } from '../features/workflow/runPhase'
import { deriveRunPhaseFromSnapshot } from '../features/workflow/runPhase'
import {
  appendCappedLogEntry,
  artifactKey,
  clampPercent,
  createProgressLogEntry,
  deriveArtifactPayloads,
  deriveDashboardStageState,
  deriveNodeStatus,
  deriveRunOutput,
  deriveVideoPreviewUrl,
  deriveVideoStepPercent,
  deriveViewState,
  getDraftDefinition,
} from './workflowSessionUtils'

export type WorkflowDefinition = Record<string, unknown> | null
export type WorkflowNode = Record<string, unknown>
export type WorkflowEdge = Record<string, unknown>

export type WorkflowViewState = 'idle' | 'switching' | 'ready' | 'empty' | 'error'

export interface VideoProgressLogEntry {
  id: string
  time: string
  message: string
}

export interface DashboardProgressState {
  visible: boolean
  stage: number
  percent: number
  logs: VideoProgressLogEntry[]
}

export interface VideoProgressState {
  visible: boolean
  step: number
  percent: number
  logs: VideoProgressLogEntry[]
}

export interface WorkflowSessionState {
  artifacts: WorkflowArtifactPayload[]
  files: string[]
  fileError: string | null
  viewState: WorkflowViewState
  activeFilePath: string | null
  activeDraftId: string | null
  definition: WorkflowDefinition
  draftNodes: Record<string, WorkflowNode>
  draftEdges: Record<string, WorkflowEdge>
  validatedNodes: Record<string, WorkflowNode>
  validatedEdges: Record<string, WorkflowEdge>
  nodeStatus: Record<string, { status: string; outputs?: Record<string, unknown> }>
  runStatus: string | null
  runError: string | null
  error: string | null
  runPhase: WorkflowRunPhaseState | null
  activeRun: WorkflowRun | null
  runOutput: string
  dashboardRefreshKey: number
  dashboardProgress: DashboardProgressState
  videoProgress: VideoProgressState
  /** URL of a ready video-preview container (set from video artifacts or snapshot restore) */
  videoPreviewUrl: string | null
  lastUpdated: number | null
}

interface WorkflowSessionsStore {
  sessions: Record<string, WorkflowSessionState>
  ensureSession: (sessionId: string) => WorkflowSessionState
  resetSession: (sessionId: string) => void
  hydrateWorkspaceState: (sessionId: string, snapshot: WorkspaceState | null) => void
  recordArtifact: (sessionId: string, artifact: WorkflowArtifactPayload) => void
  setViewState: (sessionId: string, state: WorkflowViewState) => void
  setFiles: (sessionId: string, files: string[]) => void
  setFileError: (sessionId: string, error: string | null) => void
  setDefinition: (sessionId: string, definition: WorkflowDefinition) => void
  setActiveFilePath: (sessionId: string, path: string | null) => void
  setActiveDraftId: (sessionId: string, draftId: string | null) => void
  clearDraft: (sessionId: string) => void
  addDraftNode: (sessionId: string, node: WorkflowNode) => void
  addDraftEdge: (sessionId: string, edge: WorkflowEdge) => void
  setValidatedGraph: (sessionId: string, nodes: Record<string, WorkflowNode>, edges: Record<string, WorkflowEdge>) => void
  clearValidated: (sessionId: string) => void
  updateDraftNodeParam: (sessionId: string, nodeId: string, key: string, value: string) => void
  setNodeStatus: (sessionId: string, nodeId: string, status: string, outputs?: Record<string, unknown>) => void
  setRunStatus: (sessionId: string, status: string | null, error?: string | null) => void
  setError: (sessionId: string, error: string | null) => void
  setRunPhase: (sessionId: string, phase: WorkflowRunPhaseState | null) => void
  setActiveRun: (sessionId: string, run: WorkflowRun | null) => void
  setRunOutput: (sessionId: string, output: string) => void
  triggerDashboardRefresh: (sessionId: string) => void
  setDashboardProgressVisible: (sessionId: string, visible: boolean) => void
  appendDashboardProgressLog: (sessionId: string, message: string) => void
  setDashboardProgressStage: (sessionId: string, stage: number) => void
  setDashboardProgressPercent: (sessionId: string, percent: number) => void
  setVideoProgressVisible: (sessionId: string, visible: boolean) => void
  appendVideoProgressLog: (sessionId: string, message: string) => void
  setVideoProgressStep: (sessionId: string, step: number) => void
  setVideoProgressPercent: (sessionId: string, percent: number) => void
  setVideoPreviewUrl: (sessionId: string, url: string | null) => void
}

const initialDashboardProgress: DashboardProgressState = {
  visible: false,
  stage: 0,
  percent: 0,
  logs: [],
}

const initialVideoProgress: VideoProgressState = {
  visible: false,
  step: 0,
  percent: 0,
  logs: [],
}

const createEmptySession = (): WorkflowSessionState => ({
  artifacts: [],
  files: [],
  fileError: null,
  viewState: 'idle',
  activeFilePath: null,
  activeDraftId: null,
  definition: null,
  draftNodes: {},
  draftEdges: {},
  validatedNodes: {},
  validatedEdges: {},
  nodeStatus: {},
  runStatus: null,
  runError: null,
  error: null,
  runPhase: null,
  activeRun: null,
  runOutput: '',
  dashboardRefreshKey: 0,
  dashboardProgress: { ...initialDashboardProgress },
  videoProgress: { ...initialVideoProgress },
  videoPreviewUrl: null,
  lastUpdated: null,
})

const withSession = (state: WorkflowSessionsStore['sessions'], sessionId: string) =>
  state[sessionId] ?? createEmptySession()

const patchSessionState = (
  sessions: WorkflowSessionsStore['sessions'],
  sessionId: string,
  patch:
    | Partial<WorkflowSessionState>
    | ((current: WorkflowSessionState) => Partial<WorkflowSessionState>),
) => {
  const current = withSession(sessions, sessionId)
  const nextPatch = typeof patch === 'function' ? patch(current) : patch
  return {
    ...sessions,
    [sessionId]: {
      ...current,
      ...nextPatch,
      lastUpdated: Date.now(),
    },
  }
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
  recordArtifact: (sessionId, artifact) =>
    set((state) => {
      return {
        sessions: patchSessionState(state.sessions, sessionId, (current) => {
          const key = artifactKey(artifact)
          return {
            artifacts: [
              ...current.artifacts.filter((item) => artifactKey(item) !== key),
              artifact,
            ],
          }
        }),
      }
    }),
  hydrateWorkspaceState: (sessionId, snapshot) =>
    set((state) => {
      const current = withSession(state.sessions, sessionId)
      const hasTrackedState = !!snapshot?.turn || !!snapshot?.draft || !!snapshot?.run || !!snapshot?.artifacts?.length
      if (!hasTrackedState) {
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
      const artifactPayloads = deriveArtifactPayloads(artifacts)
      const definition = getDraftDefinition(draft)

      return {
        sessions: {
          ...state.sessions,
            [sessionId]: {
              ...createEmptySession(),
              artifacts: artifactPayloads,
              files: current.files,
              fileError: current.fileError,
              dashboardRefreshKey: current.dashboardRefreshKey,
            viewState: deriveViewState(definition, run),
            activeFilePath: draft?.file_path ?? run?.file_path ?? null,
            activeDraftId: draft?.id ?? run?.draft_id ?? null,
            definition,
            nodeStatus: deriveNodeStatus(run),
            runStatus: run?.status ?? null,
            runError: run?.error ?? null,
            error: run?.status === 'failed' ? run?.error ?? null : null,
            runPhase: deriveRunPhaseFromSnapshot(run, artifacts),
            activeRun: run,
            runOutput: deriveRunOutput(run),
            dashboardProgress: { ...initialDashboardProgress },
            videoPreviewUrl: deriveVideoPreviewUrl(artifacts),
            lastUpdated: Date.now(),
          },
        },
      }
    }),
  setViewState: (sessionId, viewState) =>
    set((state) => ({ sessions: patchSessionState(state.sessions, sessionId, { viewState }) })),
  setFiles: (sessionId, files) =>
    set((state) => ({ sessions: patchSessionState(state.sessions, sessionId, { files }) })),
  setFileError: (sessionId, fileError) =>
    set((state) => ({ sessions: patchSessionState(state.sessions, sessionId, { fileError }) })),
  setDefinition: (sessionId, definition) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, { definition, error: null }),
    })),
  setActiveFilePath: (sessionId, activeFilePath) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, { activeFilePath }),
    })),
  setActiveDraftId: (sessionId, activeDraftId) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, { activeDraftId }),
    })),
  clearDraft: (sessionId) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, {
        activeDraftId: null,
        draftNodes: {},
        draftEdges: {},
        nodeStatus: {},
        runStatus: null,
        runError: null,
        error: null,
        runPhase: null,
        activeRun: null,
        runOutput: '',
      }),
    })),
  addDraftNode: (sessionId, node) =>
    set((state) => {
      return {
        sessions: patchSessionState(state.sessions, sessionId, (current) => {
          const id =
            typeof node.id === 'string'
              ? node.id
              : `node-${Object.keys(current.draftNodes).length + 1}`
          return {
            draftNodes: { ...current.draftNodes, [id]: node },
          }
        }),
      }
    }),
  addDraftEdge: (sessionId, edge) =>
    set((state) => {
      return {
        sessions: patchSessionState(state.sessions, sessionId, (current) => {
          const id =
            typeof edge.id === 'string'
              ? edge.id
              : `edge-${Object.keys(current.draftEdges).length + 1}`
          return {
            draftEdges: { ...current.draftEdges, [id]: edge },
          }
        }),
      }
    }),
  setValidatedGraph: (sessionId, nodes, edges) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, {
        validatedNodes: nodes,
        validatedEdges: edges,
      }),
    })),
  clearValidated: (sessionId) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, {
        validatedNodes: {},
        validatedEdges: {},
      }),
    })),
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
        sessions: patchSessionState(state.sessions, sessionId, {
          draftNodes: {
              ...current.draftNodes,
              [nodeId]: {
                ...existing,
                params: { ...params, [key]: value },
              },
          },
        }),
      }
    }),
  setNodeStatus: (sessionId, nodeId, status, outputs) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => ({
        nodeStatus: {
          ...current.nodeStatus,
          [nodeId]: { status, outputs },
        },
      })),
    })),
  setRunStatus: (sessionId, status, error = null) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, {
        runStatus: status,
        runError: error,
      }),
    })),
  setError: (sessionId, error) =>
    set((state) => ({ sessions: patchSessionState(state.sessions, sessionId, { error }) })),
  setRunPhase: (sessionId, runPhase) =>
    set((state) => ({ sessions: patchSessionState(state.sessions, sessionId, { runPhase }) })),
  setActiveRun: (sessionId, activeRun) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => ({
        activeDraftId: activeRun?.draft_id ?? current.activeDraftId,
        activeRun,
      })),
    })),
  setRunOutput: (sessionId, runOutput) =>
    set((state) => ({ sessions: patchSessionState(state.sessions, sessionId, { runOutput }) })),
  triggerDashboardRefresh: (sessionId) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => ({
        dashboardRefreshKey: current.dashboardRefreshKey + 1,
      })),
    })),
  setDashboardProgressVisible: (sessionId, visible) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => {
        const previous = current.dashboardProgress ?? initialDashboardProgress
        return {
          dashboardProgress: visible
            ? previous.visible
              ? { ...previous, visible: true }
              : { ...initialDashboardProgress, visible: true }
            : { ...previous, visible: false },
        }
      }),
    })),
  appendDashboardProgressLog: (sessionId, message) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => {
        const prev = current.dashboardProgress ?? initialDashboardProgress
        const entry = createProgressLogEntry(message)
        return {
          dashboardProgress: {
            ...prev,
            visible: true,
            logs: appendCappedLogEntry(prev.logs, entry),
          },
        }
      }),
    })),
  setDashboardProgressStage: (sessionId, stage) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => {
        const prev = current.dashboardProgress ?? initialDashboardProgress
        const next = deriveDashboardStageState(stage, prev.stage, prev.percent)
        return {
          dashboardProgress: {
            ...prev,
            visible: true,
            stage: next.stage,
            percent: next.percent,
          },
        }
      }),
    })),
  setDashboardProgressPercent: (sessionId, percent) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => {
        const prev = current.dashboardProgress ?? initialDashboardProgress
        return {
          dashboardProgress: {
            ...prev,
            visible: true,
            percent: clampPercent(percent),
          },
        }
      }),
    })),
  setVideoProgressVisible: (sessionId, visible) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => ({
        videoProgress: {
          visible,
          step: visible ? 0 : current.videoProgress?.step ?? 0,
          percent: visible ? 0 : current.videoProgress?.percent ?? 0,
          logs: visible ? [] : (current.videoProgress?.logs ?? []),
        },
      })),
    })),
  appendVideoProgressLog: (sessionId, message) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => {
        const prev = current.videoProgress ?? initialVideoProgress
        const entry = createProgressLogEntry(message)
        return {
          videoProgress: {
            ...prev,
            logs: appendCappedLogEntry(prev.logs, entry),
          },
        }
      }),
    })),
  setVideoProgressStep: (sessionId, step) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => {
        const prev = current.videoProgress ?? initialVideoProgress
        return {
          videoProgress: {
            ...prev,
            step,
            percent: deriveVideoStepPercent(step),
          },
        }
      }),
    })),
  setVideoProgressPercent: (sessionId, percent) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, (current) => {
        const prev = current.videoProgress ?? initialVideoProgress
        return {
          videoProgress: { ...prev, percent: clampPercent(percent) },
        }
      }),
    })),
  setVideoPreviewUrl: (sessionId, url) =>
    set((state) => ({
      sessions: patchSessionState(state.sessions, sessionId, { videoPreviewUrl: url }),
    })),
}))
