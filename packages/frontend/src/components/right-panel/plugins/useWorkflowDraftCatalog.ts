import { useCallback, useEffect, useRef, useState } from 'react'

import { sessionApi } from '../../../api'
import type { WorkflowDraft, WorkflowRun } from '../../../types'
import type { WorkflowViewState } from '../../../stores/workflowSessions'
import type { NodeDef } from '../../../stores/workflowNodes'
import { deferEffectWork } from '../../../utils/effects'
import { validateGraph, type DefinitionEdge, type DefinitionNode } from './workflowPanelUtils'
import {
  buildWorkflowDraftFileList,
  hasTrackedWorkflowState,
  readWorkflowDraftGraph,
} from './workflowLiveControllerUtils'

export interface WorkflowSessionActions {
  ensureSession: (sessionId: string) => unknown
  setWorkflowError: (sessionId: string, error: string | null) => void
  setRunStatus: (sessionId: string, status: string | null, error?: string | null) => void
  setWorkflowDefinition: (sessionId: string, definition: Record<string, unknown> | null) => void
  clearWorkflow: (sessionId: string) => void
  addWorkflowNode: (sessionId: string, node: DefinitionNode) => void
  addWorkflowEdge: (sessionId: string, edge: DefinitionEdge) => void
  setActiveFilePath: (sessionId: string, path: string | null) => void
  setActiveDraftId: (sessionId: string, draftId: string | null) => void
  setActiveRun: (sessionId: string, run: WorkflowRun | null) => void
  setRunOutput: (sessionId: string, output: string) => void
  setViewState: (sessionId: string, state: WorkflowViewState) => void
  setFiles: (sessionId: string, files: string[]) => void
  setFileError: (sessionId: string, error: string | null) => void
  setValidatedGraph: (
    sessionId: string,
    nodes: Record<string, DefinitionNode>,
    edges: Record<string, DefinitionEdge>,
  ) => void
  clearValidated: (sessionId: string) => void
}

interface UseWorkflowDraftCatalogParams {
  sessionId: string | null
  sessionIdFromStore: string | null
  sessionMessagesCount: number
  filesChangedTrigger: number
  isStreaming: boolean
  nodeDefs: Record<string, NodeDef>
  definition: Record<string, unknown> | null
  activeRun: WorkflowRun | null
  activeFiles: string[]
  activeFilePath: string | null
  activeDraftId: string | null
  activeViewState: WorkflowViewState
  activeDraftNodes: Record<string, DefinitionNode>
  activeDraftEdges: Record<string, DefinitionEdge>
  activeValidatedNodes: Record<string, DefinitionNode>
  activeValidatedEdges: Record<string, DefinitionEdge>
  actions: WorkflowSessionActions
}

export function useWorkflowDraftCatalog({
  sessionId,
  sessionIdFromStore,
  sessionMessagesCount,
  filesChangedTrigger,
  isStreaming,
  nodeDefs,
  definition,
  activeRun,
  activeFiles,
  activeFilePath,
  activeDraftId,
  activeViewState,
  activeDraftNodes,
  activeDraftEdges,
  activeValidatedNodes,
  activeValidatedEdges,
  actions,
}: UseWorkflowDraftCatalogParams) {
  const [displaySessionId, setDisplaySessionId] = useState<string | null>(sessionId)
  const [isViewSwitching, setIsViewSwitching] = useState(false)
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const [availableDrafts, setAvailableDrafts] = useState<WorkflowDraft[]>([])
  const [isLoadingFile, setIsLoadingFile] = useState(false)

  const activeFilePathRef = useRef<string | null>(null)
  const activeDraftIdRef = useRef<string | null>(null)
  const availableDraftsRef = useRef<WorkflowDraft[]>([])
  const isLoadingFilesRef = useRef(false)

  const hasTrackedWorkspaceState = hasTrackedWorkflowState({
    definition,
    activeRun,
    activeDraftId,
    draftNodeCount: Object.keys(activeDraftNodes).length,
    draftEdgeCount: Object.keys(activeDraftEdges).length,
    validatedNodeCount: Object.keys(activeValidatedNodes).length,
    validatedEdgeCount: Object.keys(activeValidatedEdges).length,
  })

  useEffect(() => {
    if (sessionId) {
      actions.ensureSession(sessionId)
      actions.setViewState(sessionId, 'switching')
    }
  }, [sessionId, actions])

  useEffect(() => {
    return deferEffectWork(() => {
      if (!sessionId) {
        setDisplaySessionId(null)
        setIsViewSwitching(false)
        return
      }
      if (displaySessionId !== sessionId) {
        setIsViewSwitching(true)
      }
    })
  }, [sessionId, displaySessionId])

  useEffect(() => {
    if (!sessionId) return
    if (activeViewState === 'ready' || activeViewState === 'empty' || activeViewState === 'error') {
      return deferEffectWork(() => {
        setDisplaySessionId(sessionId)
        setIsViewSwitching(false)
      })
    }
  }, [sessionId, activeViewState])

  useEffect(() => {
    activeFilePathRef.current = activeFilePath
  }, [activeFilePath])

  useEffect(() => {
    activeDraftIdRef.current = activeDraftId
  }, [activeDraftId])

  useEffect(() => {
    availableDraftsRef.current = availableDrafts
  }, [availableDrafts])

  useEffect(() => {
    isLoadingFilesRef.current = isLoadingFiles
  }, [isLoadingFiles])

  const loadWorkflowDraft = useCallback(
    async (draftIdToLoad: string) => {
      if (!sessionId) return
      setIsLoadingFile(true)
      actions.setFileError(sessionId, null)
      try {
        const matchingDraft = availableDraftsRef.current.find((draft) => draft.id === draftIdToLoad) || null
        const parsed = readWorkflowDraftGraph(matchingDraft)
        actions.clearWorkflow(sessionId)
        Object.values(parsed.nodes).forEach((node) => actions.addWorkflowNode(sessionId, node))
        Object.values(parsed.edges).forEach((edge) => actions.addWorkflowEdge(sessionId, edge))
        actions.setWorkflowDefinition(sessionId, parsed.definition)
        actions.setActiveDraftId(sessionId, matchingDraft?.id ?? null)
        actions.setActiveFilePath(sessionId, matchingDraft?.file_path ?? null)
        const validationError = validateGraph(parsed.nodes, parsed.edges, nodeDefs)
        if (validationError) {
          actions.setWorkflowError(sessionId, validationError)
          actions.setViewState(sessionId, 'error')
          return
        }
        actions.setWorkflowError(sessionId, null)
        actions.setValidatedGraph(sessionId, parsed.nodes, parsed.edges)
        actions.setViewState(sessionId, 'ready')
      } catch (err) {
        actions.setFileError(
          sessionId,
          err instanceof Error ? err.message : 'Failed to load workflow file.',
        )
        actions.setViewState(sessionId, 'error')
      } finally {
        setIsLoadingFile(false)
      }
    },
    [sessionId, nodeDefs, actions],
  )

  const refreshDrafts = useCallback(
    async (shouldLoadFile: boolean) => {
      if (!sessionId || isLoadingFilesRef.current) return
      setIsLoadingFiles(true)
      actions.setFileError(sessionId, null)
      try {
        const drafts = await sessionApi.listWorkflowDrafts(sessionId)
        availableDraftsRef.current = drafts
        setAvailableDrafts(drafts)
        actions.setFiles(sessionId, buildWorkflowDraftFileList(drafts, activeFilePathRef.current))

        if (!shouldLoadFile || isStreaming) return
        if (drafts.length === 0) {
          actions.setActiveFilePath(sessionId, null)
          actions.setActiveDraftId(sessionId, null)
          actions.clearWorkflow(sessionId)
          actions.setWorkflowDefinition(sessionId, null)
          actions.setWorkflowError(sessionId, null)
          actions.setRunStatus(sessionId, null, null)
          actions.setActiveRun(sessionId, null)
          actions.setRunOutput(sessionId, '')
          actions.clearValidated(sessionId)
          actions.setViewState(sessionId, 'empty')
          return
        }

        const activeDraftExists =
          !!activeDraftIdRef.current && drafts.some((draft) => draft.id === activeDraftIdRef.current)
        if (!activeDraftExists) {
          await loadWorkflowDraft(drafts[0].id)
        }
        actions.setViewState(sessionId, 'ready')
      } catch (err) {
        availableDraftsRef.current = []
        actions.setFiles(sessionId, [])
        setAvailableDrafts([])
        actions.setFileError(
          sessionId,
          err instanceof Error ? err.message : 'Failed to list workflow drafts.',
        )
        actions.setViewState(sessionId, 'error')
      } finally {
        setIsLoadingFiles(false)
      }
    },
    [sessionId, isStreaming, loadWorkflowDraft, actions],
  )

  useEffect(() => {
    if (!sessionId) return
    return deferEffectWork(() => {
      void refreshDrafts(true)
    })
  }, [sessionId, refreshDrafts])

  useEffect(() => {
    if (!sessionId) return
    if (filesChangedTrigger === 0 || sessionIdFromStore !== sessionId) return
    return deferEffectWork(() => {
      void refreshDrafts(true)
    })
  }, [filesChangedTrigger, refreshDrafts, sessionId, sessionIdFromStore])

  useEffect(() => {
    if (!sessionId) return
    if (sessionIdFromStore !== sessionId) return
    if (sessionMessagesCount > 0 || hasTrackedWorkspaceState) return
    return deferEffectWork(() => {
      actions.setActiveFilePath(sessionId, null)
      actions.setWorkflowDefinition(sessionId, null)
      actions.clearValidated(sessionId)
      actions.setViewState(sessionId, 'empty')
      setDisplaySessionId(sessionId)
      setIsViewSwitching(false)
    })
  }, [
    sessionId,
    sessionIdFromStore,
    sessionMessagesCount,
    hasTrackedWorkspaceState,
    actions,
  ])

  useEffect(() => {
    if (!sessionId) return
    if (isLoadingFiles || isStreaming || activeFiles.length > 0 || hasTrackedWorkspaceState) return
    return deferEffectWork(() => {
      actions.setActiveFilePath(sessionId, null)
      actions.setWorkflowDefinition(sessionId, null)
      actions.clearValidated(sessionId)
      actions.setViewState(sessionId, 'empty')
      setDisplaySessionId(sessionId)
      setIsViewSwitching(false)
    })
  }, [
    sessionId,
    isLoadingFiles,
    isStreaming,
    activeFiles.length,
    hasTrackedWorkspaceState,
    actions,
  ])

  useEffect(() => {
    if (!sessionId) return
    if (activeFiles.length > 0 || hasTrackedWorkspaceState) return
    if (activeViewState === 'empty') {
      return deferEffectWork(() => {
        actions.clearValidated(sessionId)
        actions.setWorkflowDefinition(sessionId, null)
        setDisplaySessionId(sessionId)
        setIsViewSwitching(false)
      })
    }
    return deferEffectWork(() => {
      void refreshDrafts(true)
    })
  }, [
    sessionId,
    activeFiles.length,
    activeViewState,
    hasTrackedWorkspaceState,
    refreshDrafts,
    actions,
  ])

  return {
    availableDrafts,
    displaySessionId,
    isLoadingFile,
    isLoadingFiles,
    isViewSwitching,
    loadWorkflowDraft,
    setAvailableDrafts,
  }
}
