import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useShallow } from 'zustand/react/shallow'

import { sessionApi } from '../../../api'
import { ensureSessionEventStream } from '../../../services/sessionEventStream'
import { selectCurrentMessages, selectCurrentSessionId, selectIsStreaming, useChatStore } from '../../../stores/chat'
import { useWorkflowNodesStore } from '../../../stores/workflowNodes'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import type { WorkflowDraft } from '../../../types'
import {
  buildOptimisticRun,
  dedupeFilePaths,
  type DefinitionEdge,
  type DefinitionNode,
  type WorkflowFlowEdge,
  type WorkflowFlowNode,
  toDefinition,
  validateGraph,
} from './workflowPanelUtils'

const WORKFLOW_DIR = '/workspace/workflow'

export function useWorkflowLiveController(sessionId: string | null) {
  const [displaySessionId, setDisplaySessionId] = useState<string | null>(sessionId)
  const [isViewSwitching, setIsViewSwitching] = useState(false)
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const [availableDrafts, setAvailableDrafts] = useState<WorkflowDraft[]>([])
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const {
    sessionState,
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
      sessionState: displaySessionId ? state.sessions[displaySessionId] : undefined,
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

  const activeFilePathRef = useRef<string | null>(null)
  const activeDraftIdRef = useRef<string | null>(null)
  const isLoadingFilesRef = useRef(false)

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
  const displayFileError = sessionState?.fileError ?? null
  const activeRun = sessionState?.activeRun ?? null
  const runOutput = sessionState?.runOutput ?? ''
  const lastUpdated = sessionState?.lastUpdated ?? null

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
  const activeFilePath = activeSessionState?.activeFilePath ?? null
  const activeDraftId = activeSessionState?.activeDraftId ?? null
  const activeDraft = useMemo(
    () => availableDrafts.find((draft) => draft.id === activeDraftId) ?? null,
    [availableDrafts, activeDraftId],
  )
  const activeViewState = activeSessionState?.viewState ?? 'idle'
  const hasTrackedWorkspaceState =
    !!activeSessionState?.definition ||
    !!activeSessionState?.activeRun ||
    !!activeSessionState?.activeDraftId ||
    Object.keys(activeDraftNodes).length > 0 ||
    Object.keys(activeDraftEdges).length > 0 ||
    Object.keys(validatedNodes).length > 0 ||
    Object.keys(validatedEdges).length > 0

  useEffect(() => {
    if (sessionId) {
      ensureSession(sessionId)
      setViewState(sessionId, 'switching')
    }
  }, [sessionId, ensureSession, setViewState])

  useEffect(() => {
    if (!sessionId) {
      setDisplaySessionId(null)
      setIsViewSwitching(false)
      return
    }
    if (displaySessionId !== sessionId) {
      setIsViewSwitching(true)
    }
  }, [sessionId, displaySessionId])

  useEffect(() => {
    if (!sessionId) return
    if (activeViewState === 'ready' || activeViewState === 'empty' || activeViewState === 'error') {
      setDisplaySessionId(sessionId)
      setIsViewSwitching(false)
    }
  }, [sessionId, activeViewState])

  useEffect(() => {
    activeFilePathRef.current = activeFilePath
  }, [activeFilePath])

  useEffect(() => {
    activeDraftIdRef.current = activeDraftId
  }, [activeDraftId])

  useEffect(() => {
    isLoadingFilesRef.current = isLoadingFiles
  }, [isLoadingFiles])

  useEffect(() => {
    if (sessionId) {
      loadNodeDefs()
    }
  }, [sessionId, loadNodeDefs])

  const loadWorkflowDraft = useCallback(
    async (draftIdToLoad: string) => {
      if (!sessionId) return
      setIsLoadingFile(true)
      setFileError(sessionId, null)
      try {
        const matchingDraft = availableDrafts.find((draft) => draft.id === draftIdToLoad) || null
        if (!matchingDraft || typeof matchingDraft.definition !== 'object') {
          throw new Error('Workflow draft is not available.')
        }
        const parsed = matchingDraft.definition
        const root = (parsed.root as Record<string, unknown>) || parsed
        const nodes = (root.nodes as Record<string, DefinitionNode>) || {}
        const edges = (root.edges as Record<string, DefinitionEdge>) || {}
        clearWorkflow(sessionId)
        Object.values(nodes).forEach((node) => addWorkflowNode(sessionId, node))
        Object.values(edges).forEach((edge) => addWorkflowEdge(sessionId, edge))
        setWorkflowDefinition(sessionId, parsed)
        setActiveDraftId(sessionId, matchingDraft.id)
        setActiveFilePath(sessionId, matchingDraft.file_path ?? null)
        const validationError = validateGraph(nodes, edges, nodeDefs)
        if (validationError) {
          setWorkflowError(sessionId, validationError)
          setViewState(sessionId, 'error')
          return
        }
        setWorkflowError(sessionId, null)
        setValidatedGraph(sessionId, nodes, edges)
        setViewState(sessionId, 'ready')
      } catch (err) {
        setFileError(sessionId, err instanceof Error ? err.message : 'Failed to load workflow file.')
        setViewState(sessionId, 'error')
      } finally {
        setIsLoadingFile(false)
      }
    },
    [
      sessionId,
      clearWorkflow,
      addWorkflowNode,
      addWorkflowEdge,
      setWorkflowDefinition,
      setWorkflowError,
      setValidatedGraph,
      setViewState,
      setFileError,
      setActiveDraftId,
      setActiveFilePath,
      nodeDefs,
      availableDrafts,
    ],
  )

  const refreshDrafts = useCallback(
    async (shouldLoadFile: boolean) => {
      if (!sessionId) return
      if (isLoadingFilesRef.current) return
      setIsLoadingFiles(true)
      setFileError(sessionId, null)
      try {
        const drafts = await sessionApi.listWorkflowDrafts(sessionId)
        setAvailableDrafts(drafts)
        const draftPaths = dedupeFilePaths(drafts.map((draft) => draft.file_path))
        const currentActiveFilePath = activeFilePathRef.current
        let nextFiles = draftPaths
        if (currentActiveFilePath && !draftPaths.includes(currentActiveFilePath)) {
          nextFiles = [currentActiveFilePath, ...draftPaths]
        }
        setFiles(sessionId, nextFiles)
        if (!shouldLoadFile || isStreaming) return
        if (drafts.length === 0) {
          setActiveFilePath(sessionId, null)
          setActiveDraftId(sessionId, null)
          clearWorkflow(sessionId)
          setWorkflowDefinition(sessionId, null)
          setWorkflowError(sessionId, null)
          setRunStatus(sessionId, null, null)
          setActiveRun(sessionId, null)
          setRunOutput(sessionId, '')
          clearValidated(sessionId)
          setViewState(sessionId, 'empty')
          return
        }
        const activeDraftExists =
          !!activeDraftIdRef.current && drafts.some((draft) => draft.id === activeDraftIdRef.current)
        if (!activeDraftExists) {
          await loadWorkflowDraft(drafts[0].id)
        }
        setViewState(sessionId, 'ready')
      } catch (err) {
        setFiles(sessionId, [])
        setAvailableDrafts([])
        setFileError(sessionId, err instanceof Error ? err.message : 'Failed to list workflow drafts.')
        setViewState(sessionId, 'error')
      } finally {
        setIsLoadingFiles(false)
      }
    },
    [
      sessionId,
      loadWorkflowDraft,
      isStreaming,
      setActiveDraftId,
      clearWorkflow,
      setWorkflowDefinition,
      setWorkflowError,
      setRunStatus,
      setActiveRun,
      setRunOutput,
      setFiles,
      setFileError,
      setViewState,
      clearValidated,
      setActiveFilePath,
    ],
  )

  useEffect(() => {
    if (!sessionId) return
    void refreshDrafts(true)
  }, [sessionId, refreshDrafts])

  useEffect(() => {
    if (!sessionId) return
    if (filesChangedTrigger === 0) return
    if (sessionIdFromStore !== sessionId) return
    void refreshDrafts(true)
  }, [filesChangedTrigger, refreshDrafts, sessionId, sessionIdFromStore])

  useEffect(() => {
    if (!sessionId) return
    if (sessionIdFromStore !== sessionId) return
    if (sessionMessages.length > 0) return
    if (hasTrackedWorkspaceState) return
    setActiveFilePath(sessionId, null)
    setWorkflowDefinition(sessionId, null)
    clearValidated(sessionId)
    setViewState(sessionId, 'empty')
    setDisplaySessionId(sessionId)
    setIsViewSwitching(false)
  }, [
    sessionId,
    sessionIdFromStore,
    sessionMessages.length,
    hasTrackedWorkspaceState,
    setActiveFilePath,
    setWorkflowDefinition,
    clearValidated,
    setViewState,
  ])

  useEffect(() => {
    if (!sessionId) return
    if (isLoadingFiles || isStreaming) return
    if (activeFiles.length > 0) return
    if (hasTrackedWorkspaceState) return
    setActiveFilePath(sessionId, null)
    setWorkflowDefinition(sessionId, null)
    clearValidated(sessionId)
    setViewState(sessionId, 'empty')
    setDisplaySessionId(sessionId)
    setIsViewSwitching(false)
  }, [
    sessionId,
    isLoadingFiles,
    isStreaming,
    activeFiles.length,
    hasTrackedWorkspaceState,
    setActiveFilePath,
    setWorkflowDefinition,
    clearValidated,
    setViewState,
  ])

  useEffect(() => {
    if (!sessionId) return
    if (activeFiles.length > 0) return
    if (hasTrackedWorkspaceState) return
    if (activeViewState === 'empty') {
      clearValidated(sessionId)
      setWorkflowDefinition(sessionId, null)
      setDisplaySessionId(sessionId)
      setIsViewSwitching(false)
      return
    }
    void refreshDrafts(true)
  }, [
    sessionId,
    activeFiles.length,
    activeViewState,
    hasTrackedWorkspaceState,
    refreshDrafts,
    clearValidated,
    setWorkflowDefinition,
  ])

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

  const persistWorkflowDraft = useCallback(
    async (nodes: WorkflowFlowNode[], edges: WorkflowFlowEdge[]) => {
      if (!sessionId) return null
      if (Object.keys(nodeDefs).length === 0) {
        setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
        return null
      }

      try {
        const definitionForSave = toDefinition(nodes, edges, nodeDefs)
        const fallbackName = activeDraft?.display_name?.trim() || 'workflow'
        const saved = await sessionApi.saveWorkflowDraft(sessionId, {
          draft_id: activeDraftId || undefined,
          name: activeDraftId ? undefined : fallbackName,
          definition: definitionForSave,
        })
        const savedFilePath = saved.file_path || `${WORKFLOW_DIR}/${fallbackName}.json`
        const root = (definitionForSave.root as Record<string, unknown>) || definitionForSave
        const nextNodes = (root.nodes as Record<string, DefinitionNode>) || {}
        const nextEdges = (root.edges as Record<string, DefinitionEdge>) || {}

        setAvailableDrafts((prev) => [saved, ...prev.filter((draft) => draft.id !== saved.id)])
        setFiles(sessionId, dedupeFilePaths([savedFilePath, ...activeFiles]))
        setActiveDraftId(sessionId, saved.id)
        setActiveFilePath(sessionId, savedFilePath)
        setWorkflowDefinition(sessionId, definitionForSave)
        setValidatedGraph(sessionId, nextNodes, nextEdges)
        setWorkflowError(sessionId, null)
        setViewState(sessionId, 'ready')
        notifyFilesChanged()
        return { draft: saved, definition: definitionForSave, filePath: savedFilePath }
      } catch (err) {
        setWorkflowError(sessionId, err instanceof Error ? err.message : 'Failed to save workflow.')
        return null
      }
    },
    [
      sessionId,
      nodeDefs,
      activeDraft,
      activeDraftId,
      activeFiles,
      setFiles,
      setActiveDraftId,
      setActiveFilePath,
      setWorkflowDefinition,
      setValidatedGraph,
      setWorkflowError,
      setViewState,
      notifyFilesChanged,
    ],
  )

  const handleSave = useCallback(
    async (nodes: WorkflowFlowNode[], edges: WorkflowFlowEdge[]) => {
      if (!sessionId) return
      setIsSaving(true)
      try {
        await persistWorkflowDraft(nodes, edges)
      } finally {
        setIsSaving(false)
      }
    },
    [sessionId, persistWorkflowDraft],
  )

  const handleExport = useCallback(
    (filename: string, nodes: WorkflowFlowNode[], edges: WorkflowFlowEdge[]) => {
      if (Object.keys(nodeDefs).length === 0) {
        if (sessionId) {
          setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
        }
        return
      }
      setIsExporting(true)
      try {
        const definitionForExport = toDefinition(nodes, edges, nodeDefs)
        const json = JSON.stringify(definitionForExport, null, 2)
        const blob = new Blob([json], { type: 'application/json;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        if (sessionId) {
          setWorkflowError(sessionId, null)
        }
      } finally {
        setIsExporting(false)
      }
    },
    [nodeDefs, sessionId, setWorkflowError],
  )

  const handleRun = useCallback(
    async (nodes: WorkflowFlowNode[], edges: WorkflowFlowEdge[]) => {
      if (!sessionId) return
      setIsRunning(true)
      setVideoProgressVisible(sessionId, false)
      try {
        const saved = await persistWorkflowDraft(nodes, edges)
        if (!saved) return
        const filePath = saved.filePath
        const draftIdForRun = saved.draft.id
        setRunStatus(sessionId, 'running', null)
        setActiveRun(
          sessionId,
          buildOptimisticRun(sessionId, filePath, 'running', { draftId: draftIdForRun }),
        )
        setRunOutput(sessionId, '')
        ensureSessionEventStream(sessionId)
        const response = await sessionApi.runWorkflowDraft(sessionId, draftIdForRun)
        if (response.error) {
          setRunStatus(sessionId, 'failed', response.error)
          setWorkflowError(sessionId, response.error)
          setActiveRun(
            sessionId,
            buildOptimisticRun(sessionId, filePath, 'failed', {
              error: response.error,
              draftId: draftIdForRun,
              runId: response.run_id ?? null,
            }),
          )
          setRunOutput(sessionId, response.error)
          return
        }
        const nextStatus = response.status === 'queued' ? 'running' : response.status
        setRunStatus(sessionId, nextStatus, null)
        setWorkflowError(sessionId, null)
        setActiveRun(
          sessionId,
          buildOptimisticRun(sessionId, filePath, nextStatus, {
            taskId: response.task_id ?? null,
            turnId: response.turn_id ?? null,
            draftId: response.draft_id ?? draftIdForRun,
            runId: response.run_id ?? null,
          }),
        )
        if (response.status && response.status !== 'queued') {
          setRunOutput(sessionId, '')
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to run workflow.'
        setRunStatus(sessionId, 'failed', message)
        setWorkflowError(sessionId, message)
        setActiveRun(
          sessionId,
          buildOptimisticRun(sessionId, activeFilePath, 'failed', {
            error: message,
            draftId: activeDraftId || null,
          }),
        )
        setRunOutput(sessionId, message)
      } finally {
        setIsRunning(false)
      }
    },
    [
      sessionId,
      setVideoProgressVisible,
      persistWorkflowDraft,
      setRunStatus,
      setActiveRun,
      setRunOutput,
      setWorkflowError,
      activeFilePath,
      activeDraftId,
    ],
  )

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
