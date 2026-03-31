import { useEffect, useMemo } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { selectCurrentMessages, selectCurrentSessionId, selectIsStreaming, useChatStore } from '../../../stores/chat'
import { useWorkflowNodesStore } from '../../../stores/workflowNodes'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import {
  type DefinitionEdge,
  type DefinitionNode,
  validateGraph,
} from './workflowPanelUtils'
import { useWorkflowDraftCatalog } from './useWorkflowDraftCatalog'
import { useWorkflowRunActions } from './useWorkflowRunActions'

export function useWorkflowLiveController(sessionId: string | null) {
  const {
    activeSessionState,
    ensureSession,
    setWorkflowError,
    setRunStatus,
    setWorkflowDefinition,
    clearWorkflow,
    addWorkflowNode,
    addWorkflowEdge,
    updateWorkflowNodeParam,
    setActiveFilePath,
    setActiveDraftId,
    setActiveRun,
    setRunOutput,
    setViewState,
    setFiles,
    setFileError,
    setValidatedGraph,
    clearValidated,
    setVideoProgressVisible,
  } = useWorkflowSessionsStore(
    useShallow((state) => ({
      activeSessionState: sessionId ? state.sessions[sessionId] : undefined,
      ensureSession: state.ensureSession,
      setWorkflowError: state.setError,
      setRunStatus: state.setRunStatus,
      setWorkflowDefinition: state.setDefinition,
      clearWorkflow: state.clearDraft,
      addWorkflowNode: state.addDraftNode,
      addWorkflowEdge: state.addDraftEdge,
      updateWorkflowNodeParam: state.updateDraftNodeParam,
      setActiveFilePath: state.setActiveFilePath,
      setActiveDraftId: state.setActiveDraftId,
      setActiveRun: state.setActiveRun,
      setRunOutput: state.setRunOutput,
      setViewState: state.setViewState,
      setFiles: state.setFiles,
      setFileError: state.setFileError,
      setValidatedGraph: state.setValidatedGraph,
      clearValidated: state.clearValidated,
      setVideoProgressVisible: state.setVideoProgressVisible,
    })),
  )

  const {
    filesChangedTrigger,
    notifyFilesChanged,
    isStreaming,
    sessionIdFromStore,
    sessionMessages,
  } = useChatStore(
    useShallow((state) => ({
      filesChangedTrigger: state.filesChangedTrigger,
      notifyFilesChanged: state.notifyFilesChanged,
      isStreaming: selectIsStreaming(state),
      sessionIdFromStore: selectCurrentSessionId(state),
      sessionMessages: selectCurrentMessages(state),
    })),
  )

  const { nodeDefs, loadNodeDefs } = useWorkflowNodesStore(
    useShallow((state) => ({
      nodeDefs: state.nodeDefs,
      loadNodeDefs: state.loadNodeDefs,
    })),
  )

  const sessionActions = useMemo(
    () => ({
      ensureSession,
      setWorkflowError,
      setRunStatus,
      setWorkflowDefinition,
      clearWorkflow,
      addWorkflowNode,
      addWorkflowEdge,
      updateWorkflowNodeParam,
      setActiveFilePath,
      setActiveDraftId,
      setActiveRun,
      setRunOutput,
      setViewState,
      setFiles,
      setFileError,
      setValidatedGraph,
      clearValidated,
      setVideoProgressVisible,
    }),
    [
      ensureSession,
      setWorkflowError,
      setRunStatus,
      setWorkflowDefinition,
      clearWorkflow,
      addWorkflowNode,
      addWorkflowEdge,
      updateWorkflowNodeParam,
      setActiveFilePath,
      setActiveDraftId,
      setActiveRun,
      setRunOutput,
      setViewState,
      setFiles,
      setFileError,
      setValidatedGraph,
      clearValidated,
      setVideoProgressVisible,
    ],
  )

  const activeDraftNodes = useMemo(
    () => (activeSessionState?.draftNodes ?? {}) as Record<string, DefinitionNode>,
    [activeSessionState?.draftNodes],
  )
  const activeDraftEdges = useMemo(
    () => (activeSessionState?.draftEdges ?? {}) as Record<string, DefinitionEdge>,
    [activeSessionState?.draftEdges],
  )
  const activeFiles = useMemo(
    () => activeSessionState?.files ?? [],
    [activeSessionState?.files],
  )
  const activeDefinition = activeSessionState?.definition ?? null
  const activeFilePath = activeSessionState?.activeFilePath ?? null
  const activeDraftId = activeSessionState?.activeDraftId ?? null
  const activeViewState = activeSessionState?.viewState ?? 'idle'

  useEffect(() => {
    if (sessionId) {
      loadNodeDefs()
    }
  }, [sessionId, loadNodeDefs])

  const {
    availableDrafts,
    displaySessionId,
    isLoadingFile,
    isLoadingFiles,
    isViewSwitching,
    loadWorkflowDraft,
    setAvailableDrafts,
  } = useWorkflowDraftCatalog({
    sessionId,
    sessionIdFromStore,
    sessionMessagesCount: sessionMessages.length,
    filesChangedTrigger,
    isStreaming,
    nodeDefs,
    definition: activeDefinition,
    activeRun: activeSessionState?.activeRun ?? null,
    activeFiles,
    activeFilePath,
    activeDraftId,
    activeViewState,
    activeDraftNodes,
    activeDraftEdges,
    activeValidatedNodes: (activeSessionState?.validatedNodes ?? {}) as Record<string, DefinitionNode>,
    activeValidatedEdges: (activeSessionState?.validatedEdges ?? {}) as Record<string, DefinitionEdge>,
    actions: sessionActions,
  })

  const sessionState = useWorkflowSessionsStore((state) =>
    displaySessionId ? state.sessions[displaySessionId] : undefined,
  )
  const definition = sessionState?.definition ?? null
  const validatedNodes = useMemo(
    () => (sessionState?.validatedNodes ?? {}) as Record<string, DefinitionNode>,
    [sessionState?.validatedNodes],
  )
  const validatedEdges = useMemo(
    () => (sessionState?.validatedEdges ?? {}) as Record<string, DefinitionEdge>,
    [sessionState?.validatedEdges],
  )
  const nodeStatus = useMemo(
    () => sessionState?.nodeStatus ?? {},
    [sessionState?.nodeStatus],
  )
  const runStatus = sessionState?.runStatus ?? null
  const runError = sessionState?.runError ?? null
  const error = sessionState?.error ?? null
  const runPhase = sessionState?.runPhase ?? null
  const displayFileError = sessionState?.fileError ?? null
  const activeRun = sessionState?.activeRun ?? null
  const runOutput = sessionState?.runOutput ?? ''
  const lastUpdated = sessionState?.lastUpdated ?? null

  const activeDraft = useMemo(
    () => availableDrafts.find((draft) => draft.id === activeDraftId) ?? null,
    [availableDrafts, activeDraftId],
  )

  useEffect(() => {
    if (!sessionId) return
    if (Object.keys(activeDraftNodes).length === 0 && Object.keys(activeDraftEdges).length === 0) {
      return
    }
    const validationError = validateGraph(activeDraftNodes, activeDraftEdges, nodeDefs)
    if (validationError) {
      setWorkflowError(sessionId, validationError)
      return
    }
    setWorkflowError(sessionId, null)
    setValidatedGraph(sessionId, activeDraftNodes, activeDraftEdges)
    setViewState(sessionId, 'ready')
  }, [
    sessionId,
    activeDraftNodes,
    activeDraftEdges,
    nodeDefs,
    setWorkflowError,
    setValidatedGraph,
    setViewState,
  ])

  const { handleExport, handleRun, handleSave, isExporting, isRunning, isSaving } =
    useWorkflowRunActions({
      sessionId,
      nodeDefs,
      activeDraft,
      activeDraftId,
      activeFiles,
      activeFilePath,
      notifyFilesChanged,
      setAvailableDrafts,
      actions: sessionActions,
    })

  return {
    displaySessionId,
    isViewSwitching,
    isLoadingFiles,
    availableDrafts,
    isLoadingFile,
    isSaving,
    isRunning,
    isExporting,
    isStreaming,
    nodeDefs,
    definition,
    validatedNodes,
    validatedEdges,
    nodeStatus,
    runStatus,
    runError,
    error,
    runPhase,
    displayFileError,
    activeRun,
    runOutput,
    activeDraftNodes,
    activeDraftEdges,
    activeDraft,
    activeDraftId,
    activeViewState,
    activeFilePath,
    lastUpdated,
    loadWorkflowDraft,
    handleSave,
    handleExport,
    handleRun,
    updateWorkflowNodeParam,
  }
}
