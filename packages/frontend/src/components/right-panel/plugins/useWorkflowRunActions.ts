import { useCallback, useState, type Dispatch, type SetStateAction } from 'react'

import { sessionApi } from '../../../api'
import { ensureSessionEventStream } from '../../../services/sessionEventStream'
import type { WorkflowDraft } from '../../../types'
import type { NodeDef } from '../../../stores/workflowNodes'
import {
  buildOptimisticRun,
  dedupeFilePaths,
  toDefinition,
  type DefinitionEdge,
  type DefinitionNode,
  type WorkflowFlowEdge,
  type WorkflowFlowNode,
} from './workflowPanelUtils'
import type { WorkflowSessionActions } from './useWorkflowDraftCatalog'

const WORKFLOW_DIR = '/workspace/workflow'

interface UseWorkflowRunActionsParams {
  sessionId: string | null
  nodeDefs: Record<string, NodeDef>
  activeDraft: WorkflowDraft | null
  activeDraftId: string | null
  activeFiles: string[]
  activeFilePath: string | null
  notifyFilesChanged: () => void
  setAvailableDrafts: Dispatch<SetStateAction<WorkflowDraft[]>>
  actions: WorkflowSessionActions & {
    setVideoProgressVisible: (sessionId: string, visible: boolean) => void
  }
}

export function useWorkflowRunActions({
  sessionId,
  nodeDefs,
  activeDraft,
  activeDraftId,
  activeFiles,
  activeFilePath,
  notifyFilesChanged,
  setAvailableDrafts,
  actions,
}: UseWorkflowRunActionsParams) {
  const [isSaving, setIsSaving] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  const persistWorkflowDraft = useCallback(
    async (nodes: WorkflowFlowNode[], edges: WorkflowFlowEdge[]) => {
      if (!sessionId) return null
      if (Object.keys(nodeDefs).length === 0) {
        actions.setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
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
        actions.setFiles(sessionId, dedupeFilePaths([savedFilePath, ...activeFiles]))
        actions.setActiveDraftId(sessionId, saved.id)
        actions.setActiveFilePath(sessionId, savedFilePath)
        actions.setWorkflowDefinition(sessionId, definitionForSave)
        actions.setValidatedGraph(sessionId, nextNodes, nextEdges)
        actions.setWorkflowError(sessionId, null)
        actions.setViewState(sessionId, 'ready')
        notifyFilesChanged()
        return { draft: saved, definition: definitionForSave, filePath: savedFilePath }
      } catch (err) {
        actions.setWorkflowError(
          sessionId,
          err instanceof Error ? err.message : 'Failed to save workflow.',
        )
        return null
      }
    },
    [
      sessionId,
      nodeDefs,
      activeDraft,
      activeDraftId,
      activeFiles,
      notifyFilesChanged,
      setAvailableDrafts,
      actions,
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
          actions.setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
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
          actions.setWorkflowError(sessionId, null)
        }
      } finally {
        setIsExporting(false)
      }
    },
    [nodeDefs, sessionId, actions],
  )

  const handleRun = useCallback(
    async (nodes: WorkflowFlowNode[], edges: WorkflowFlowEdge[]) => {
      if (!sessionId) return
      setIsRunning(true)
      actions.setVideoProgressVisible(sessionId, false)
      try {
        const saved = await persistWorkflowDraft(nodes, edges)
        if (!saved) return
        const filePath = saved.filePath
        const draftIdForRun = saved.draft.id
        actions.setRunStatus(sessionId, 'running', null)
        actions.setActiveRun(
          sessionId,
          buildOptimisticRun(sessionId, filePath, 'running', { draftId: draftIdForRun }),
        )
        actions.setRunOutput(sessionId, '')
        ensureSessionEventStream(sessionId)
        const response = await sessionApi.runWorkflowDraft(sessionId, draftIdForRun)
        if (response.error) {
          actions.setRunStatus(sessionId, 'failed', response.error)
          actions.setWorkflowError(sessionId, response.error)
          actions.setActiveRun(
            sessionId,
            buildOptimisticRun(sessionId, filePath, 'failed', {
              error: response.error,
              draftId: draftIdForRun,
              runId: response.run_id ?? null,
            }),
          )
          actions.setRunOutput(sessionId, response.error)
          return
        }

        const nextStatus = response.status === 'queued' ? 'running' : response.status
        actions.setRunStatus(sessionId, nextStatus, null)
        actions.setWorkflowError(sessionId, null)
        actions.setActiveRun(
          sessionId,
          buildOptimisticRun(sessionId, filePath, nextStatus, {
            taskId: response.task_id ?? null,
            turnId: response.turn_id ?? null,
            draftId: response.draft_id ?? draftIdForRun,
            runId: response.run_id ?? null,
          }),
        )
        if (response.status && response.status !== 'queued') {
          actions.setRunOutput(sessionId, '')
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to run workflow.'
        actions.setRunStatus(sessionId, 'failed', message)
        actions.setWorkflowError(sessionId, message)
        actions.setActiveRun(
          sessionId,
          buildOptimisticRun(sessionId, activeFilePath, 'failed', {
            error: message,
            draftId: activeDraftId || null,
          }),
        )
        actions.setRunOutput(sessionId, message)
      } finally {
        setIsRunning(false)
      }
    },
    [sessionId, persistWorkflowDraft, activeFilePath, activeDraftId, actions],
  )

  return {
    handleExport,
    handleRun,
    handleSave,
    isExporting,
    isRunning,
    isSaving,
  }
}
