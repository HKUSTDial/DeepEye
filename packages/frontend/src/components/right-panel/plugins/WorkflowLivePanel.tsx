import { useMemo, useEffect, useState, useCallback, useRef, type CSSProperties } from 'react'
import { BackgroundVariant, type Edge, type Node, type ReactFlowInstance } from 'reactflow'
import { ArrowUpRight, Loader2, Workflow as WorkflowIcon } from 'lucide-react'
import 'reactflow/dist/style.css'
import WorkflowNode from '../../workflow/WorkflowNode'
import { WorkflowGraph } from '../../workflow/WorkflowGraph'
import { sessionApi } from '../../../api'
import { WorkflowInspector } from '../../workflow/WorkflowInspector'
import { useChatStore } from '../../../stores/chat'
import { useWorkflowNodesStore, type NodeDef } from '../../../stores/workflowNodes'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { useTheme } from '../../../hooks/useTheme'
import { ensureSessionEventStream } from '../../../services/sessionEventStream'
import type { WorkflowDraft, WorkflowRun } from '../../../types'

const NODE_TYPES = { workflowNode: WorkflowNode }
const WORKFLOW_DIR = '/workspace/workflow'

type DefinitionNode = {
  id: string
  type: string
  position?: { x?: number; y?: number }
  params?: Record<string, unknown>
  metadata?: { position?: { x?: number; y?: number } }
}

type DefinitionEdge = {
  id: string
  source: { node_id: string; port_id?: string }
  target: { node_id: string; port_id?: string }
}

type WorkflowNodeData = {
  type: string
  label: string
  inputs: Array<{ id: string; label: string }>
  outputs: Array<{ id: string; label: string }>
  params?: Record<string, unknown>
  runStatus?: string
  isNew?: boolean
}

type WorkflowFlowNode = Node<WorkflowNodeData>
type WorkflowFlowEdge = Edge

function buildOptimisticRun(
  sessionId: string,
  filePath: string | null,
  status: string,
  options?: {
    error?: string | null
    taskId?: string | null
    turnId?: string | null
    draftId?: string | null
    runId?: string | null
  },
): WorkflowRun {
  return {
    id: options?.runId || options?.taskId || `pending:${sessionId}:${Date.now()}`,
    workflow_id: null,
    session_id: sessionId,
    turn_id: options?.turnId || null,
    draft_id: options?.draftId || null,
    file_path: filePath ?? null,
    source: 'workflow_editor',
    status,
    error: options?.error || undefined,
    created_at: new Date().toISOString(),
    finished_at: status === 'running' ? null : new Date().toISOString(),
  }
}

function typeToLabel(type: unknown) {
  if (typeof type !== 'string' || !type.trim()) {
    return 'Unknown Node'
  }
  return type
    .replace(/[._]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function dedupeFilePaths(paths: Array<string | null | undefined>) {
  return [...new Set(paths.filter((path): path is string => typeof path === 'string' && path.length > 0))]
}

function getDraftDisplayName(draft: WorkflowDraft) {
  if (draft.display_name?.trim()) return draft.display_name.trim()
  const fileName = draft.file_path?.split('/').pop()?.replace(/\.json$/i, '')
  if (fileName) return fileName
  return `draft-${draft.id.slice(0, 8)}`
}

function validateGraph(
  nodesMap: Record<string, DefinitionNode>,
  edgesMap: Record<string, DefinitionEdge>,
  nodeDefs: Record<string, NodeDef>,
) {
  if (Object.keys(nodeDefs).length === 0) {
    return null
  }
  for (const node of Object.values(nodesMap)) {
    if (!node || typeof node.type !== 'string') {
      return 'Invalid node definition.'
    }
    if (!nodeDefs[node.type]) {
      return `Unknown node type: ${node.type}`
    }
  }
  for (const edge of Object.values(edgesMap)) {
    if (!edge?.source?.node_id || !edge?.target?.node_id) {
      return 'Invalid edge definition.'
    }
    if (!nodesMap[edge.source.node_id] || !nodesMap[edge.target.node_id]) {
      return 'Edge references missing node.'
    }
  }
  return null
}

function toFlow(definition: Record<string, unknown>, nodeDefs: Record<string, NodeDef>) {
  const root = (definition.root as Record<string, unknown>) || definition
  const nodesMap = (root.nodes as Record<string, DefinitionNode>) || {}
  const edgesMap = (root.edges as Record<string, DefinitionEdge>) || {}

  const nodes = Object.values(nodesMap).map((node) => {
    const def = nodeDefs[node.type]
    const xRaw = node.metadata?.position?.x ?? node.position?.x
    const yRaw = node.metadata?.position?.y ?? node.position?.y
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

  const edges = Object.values(edgesMap)
    .filter((edge) => edge?.source?.node_id && edge?.target?.node_id)
    .map((edge) => ({
      id: edge.id,
      source: edge.source.node_id,
      target: edge.target.node_id,
      sourceHandle: edge.source.port_id,
      targetHandle: edge.target.port_id,
      animated: false,
      style: { stroke: 'var(--workflow-link)', strokeWidth: 2.25 },
    }))

  return { nodes, edges }
}

function toDefinition(
  nodes: WorkflowFlowNode[],
  edges: WorkflowFlowEdge[],
  nodeDefs: Record<string, NodeDef>,
) {
  const nodeMap: Record<string, Record<string, unknown>> = {}
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

  const edgeMap: Record<string, Record<string, unknown>> = {}
  edges.forEach((edge) => {
    const id = edge.id || `${edge.source}-${edge.sourceHandle}-${edge.target}-${edge.targetHandle}`
    edgeMap[id] = {
      id,
      source: { node_id: edge.source, port_id: edge.sourceHandle || 'rows' },
      target: { node_id: edge.target, port_id: edge.targetHandle || 'rows' },
    }
  })

  return { root: { nodes: nodeMap, edges: edgeMap } }
}

export function WorkflowLivePanel({ 
  sessionId, 
  dataSourceIds = [] 
}: { 
  sessionId: string | null,
  dataSourceIds?: string[]
}) {
  const [displaySessionId, setDisplaySessionId] = useState<string | null>(sessionId)
  const [isViewSwitching, setIsViewSwitching] = useState(false)
  const sessionState = useWorkflowSessionsStore((state) =>
    displaySessionId ? state.sessions[displaySessionId] : undefined,
  )
  const activeSessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )
  const ensureSession = useWorkflowSessionsStore((state) => state.ensureSession)
  const setWorkflowError = useWorkflowSessionsStore((state) => state.setError)
  const setRunStatus = useWorkflowSessionsStore((state) => state.setRunStatus)
  const setWorkflowDefinition = useWorkflowSessionsStore((state) => state.setDefinition)
  const clearWorkflow = useWorkflowSessionsStore((state) => state.clearDraft)
  const addWorkflowNode = useWorkflowSessionsStore((state) => state.addDraftNode)
  const addWorkflowEdge = useWorkflowSessionsStore((state) => state.addDraftEdge)
  const updateWorkflowNodeParam = useWorkflowSessionsStore((state) => state.updateDraftNodeParam)
  const setActiveFilePath = useWorkflowSessionsStore((state) => state.setActiveFilePath)
  const setActiveDraftId = useWorkflowSessionsStore((state) => state.setActiveDraftId)
  const setActiveRun = useWorkflowSessionsStore((state) => state.setActiveRun)
  const setRunOutput = useWorkflowSessionsStore((state) => state.setRunOutput)
  const setViewState = useWorkflowSessionsStore((state) => state.setViewState)
  const setFiles = useWorkflowSessionsStore((state) => state.setFiles)
  const setFileError = useWorkflowSessionsStore((state) => state.setFileError)
  const setValidatedGraph = useWorkflowSessionsStore((state) => state.setValidatedGraph)
  const clearValidated = useWorkflowSessionsStore((state) => state.clearValidated)
  const setVideoProgressVisible = useWorkflowSessionsStore((state) => state.setVideoProgressVisible)
  const filesChangedTrigger = useChatStore((state) => state.filesChangedTrigger)
  const notifyFilesChanged = useChatStore((state) => state.notifyFilesChanged)
  const isStreaming = useChatStore((state) => state.isStreaming)
  const sessionIdFromStore = useChatStore((state) => state.sessionId)
  const sessionMessages = useChatStore((state) => state.messages)

  const nodeDefs = useWorkflowNodesStore((state) => state.nodeDefs)
  const loadNodeDefs = useWorkflowNodesStore((state) => state.loadNodeDefs)

  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const [availableDrafts, setAvailableDrafts] = useState<WorkflowDraft[]>([])
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [newNodeIds, setNewNodeIds] = useState<Set<string>>(new Set())
  const [newEdgeIds, setNewEdgeIds] = useState<Set<string>>(new Set())
  const [isSaving, setIsSaving] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const reactFlowRef = useRef<ReactFlowInstance | null>(null)
  const graphHostRef = useRef<HTMLDivElement | null>(null)

  const activeFilePathRef = useRef<string | null>(null)
  const activeDraftIdRef = useRef<string | null>(null)
  const isLoadingFilesRef = useRef(false)
  const prevNodeIdsRef = useRef<Set<string>>(new Set())
  const prevEdgeIdsRef = useRef<Set<string>>(new Set())

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
  const activeFilePathForControls = activeSessionState?.activeFilePath ?? null
  const activeDraftIdForSession = activeSessionState?.activeDraftId ?? null
  const activeDraftForSession = useMemo(
    () => availableDrafts.find((draft) => draft.id === activeDraftIdForSession) ?? null,
    [availableDrafts, activeDraftIdForSession],
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
    activeFilePathRef.current = activeFilePathForControls
  }, [activeFilePathForControls])

  useEffect(() => {
    activeDraftIdRef.current = activeDraftIdForSession
  }, [activeDraftIdForSession])

  useEffect(() => {
    isLoadingFilesRef.current = isLoadingFiles
  }, [isLoadingFiles])

  useEffect(() => {
    if (sessionId) {
      loadNodeDefs()
    }
  }, [sessionId, loadNodeDefs])

  const loadWorkflowDraft = useCallback(
    async (draftId: string) => {
      if (!sessionId) return
      setIsLoadingFile(true)
      setFileError(sessionId, null)
      try {
        const matchingDraft = availableDrafts.find((draft) => draft.id === draftId) || null
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
        setSelectedNodeId(null)
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
        const activeDraftExists = !!activeDraftIdRef.current && drafts.some((draft) => draft.id === activeDraftIdRef.current)
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
      setAvailableDrafts,
      setActiveFilePath,
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
    ],
  )

  useEffect(() => {
    if (!sessionId) return
    refreshDrafts(true)
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
    refreshDrafts(true)
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
    activeFilePathForControls,
    nodeDefs,
    setWorkflowError,
    setValidatedGraph,
    setViewState,
  ])

  useEffect(() => {
    const currentNodeIds = new Set(Object.keys(activeDraftNodes))
    const currentEdgeIds = new Set(Object.keys(activeDraftEdges))

    const newNodes = Array.from(currentNodeIds).filter((id) => !prevNodeIdsRef.current.has(id))
    const newEdges = Array.from(currentEdgeIds).filter((id) => !prevEdgeIdsRef.current.has(id))

    if (newNodes.length > 0) {
      setNewNodeIds((prev) => {
        const next = new Set(prev)
        newNodes.forEach((id) => next.add(id))
        return next
      })
      newNodes.forEach((id) => {
        setTimeout(() => {
          setNewNodeIds((prev) => {
            const next = new Set(prev)
            next.delete(id)
            return next
          })
        }, 900)
      })
    }

    if (newEdges.length > 0) {
      setNewEdgeIds((prev) => {
        const next = new Set(prev)
        newEdges.forEach((id) => next.add(id))
        return next
      })
      newEdges.forEach((id) => {
        setTimeout(() => {
          setNewEdgeIds((prev) => {
            const next = new Set(prev)
            next.delete(id)
            return next
          })
        }, 900)
      })
    }

    prevNodeIdsRef.current = currentNodeIds
    prevEdgeIdsRef.current = currentEdgeIds
  }, [activeDraftNodes, activeDraftEdges])

  const flow = useMemo(() => {
    if (Object.keys(validatedNodes).length > 0 || Object.keys(validatedEdges).length > 0) {
      return toFlow({ root: { nodes: validatedNodes, edges: validatedEdges } }, nodeDefs)
    }
    if (!definition) return { nodes: [], edges: [] }
    if (typeof definition !== 'object' || definition === null) return { nodes: [], edges: [] }
    return toFlow(definition as Record<string, unknown>, nodeDefs)
  }, [definition, validatedNodes, validatedEdges, nodeDefs])

  const flowWithStatus = useMemo(() => {
    if (flow.nodes.length === 0) return flow
    return {
      nodes: flow.nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          runStatus: nodeStatus[node.id]?.status,
          isNew: newNodeIds.has(node.id),
        },
      })),
      edges: flow.edges.map((edge) => ({
        ...edge,
        animated: false,
        className: newEdgeIds.has(edge.id) ? 'workflow-edge--new' : '',
      })),
    }
  }, [flow, nodeStatus, newNodeIds, newEdgeIds])

  const persistWorkflowDraft = useCallback(async () => {
    if (!sessionId) return null
    if (Object.keys(nodeDefs).length === 0) {
      setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
      return null
    }

    try {
      const definition = toDefinition(flow.nodes, flow.edges, nodeDefs)
      const fallbackName = activeDraftForSession?.display_name?.trim() || 'workflow'
      const saved = await sessionApi.saveWorkflowDraft(sessionId, {
        draft_id: activeDraftIdForSession || undefined,
        name: activeDraftIdForSession ? undefined : fallbackName,
        definition,
      })
      const savedFilePath = saved.file_path || `${WORKFLOW_DIR}/${fallbackName}.json`
      const root = (definition.root as Record<string, unknown>) || definition
      const nodes = (root.nodes as Record<string, DefinitionNode>) || {}
      const edges = (root.edges as Record<string, DefinitionEdge>) || {}

      setAvailableDrafts((prev) => [saved, ...prev.filter((draft) => draft.id !== saved.id)])
      setFiles(sessionId, dedupeFilePaths([savedFilePath, ...activeFiles]))
      setActiveDraftId(sessionId, saved.id)
      setActiveFilePath(sessionId, savedFilePath)
      setWorkflowDefinition(sessionId, definition)
      setValidatedGraph(sessionId, nodes, edges)
      setWorkflowError(sessionId, null)
      setViewState(sessionId, 'ready')
      notifyFilesChanged()
      return { draft: saved, definition, filePath: savedFilePath }
    } catch (err) {
      setWorkflowError(sessionId, err instanceof Error ? err.message : 'Failed to save workflow.')
      return null
    }
  }, [
    sessionId,
    nodeDefs,
    flow.nodes,
    flow.edges,
    activeDraftForSession,
    activeDraftIdForSession,
    activeFiles,
    setFiles,
    setActiveDraftId,
    setActiveFilePath,
    setWorkflowDefinition,
    setValidatedGraph,
    setWorkflowError,
    setViewState,
    notifyFilesChanged,
  ])

  const nodeTypes = useMemo(() => NODE_TYPES, [])
  const workflowToneStyle = useMemo(
    () =>
      ({
        '--workflow-link': isDark ? '#49b6a6' : '#0f766e',
        '--workflow-link-active': isDark ? '#7ed9ca' : '#115e59',
        '--workflow-link-soft': isDark ? 'rgba(73, 182, 166, 0.18)' : 'rgba(15, 118, 110, 0.16)',
        '--workflow-port-input': isDark ? '#49b6a6' : '#0f766e',
        '--workflow-port-output': isDark ? '#f3b560' : '#c27a1a',
        '--workflow-grid': isDark ? '#29403d' : '#b7cfc8',
      }) as CSSProperties,
    [isDark],
  )
  const fitWorkflowView = useCallback(
    (duration = 260) => {
      if (!reactFlowRef.current || flowWithStatus.nodes.length === 0) return
      window.requestAnimationFrame(() => {
        reactFlowRef.current?.fitView({
          padding: 0.22,
          minZoom: 0.55,
          maxZoom: 1.08,
          duration,
        })
      })
    },
    [flowWithStatus.nodes.length],
  )

  useEffect(() => {
    if (flowWithStatus.nodes.length === 0) return
    fitWorkflowView(flowWithStatus.nodes.length > 12 ? 340 : 260)
  }, [
    fitWorkflowView,
    flowWithStatus.nodes.length,
    flowWithStatus.edges.length,
    displaySessionId,
    activeViewState,
    sessionState?.lastUpdated,
  ])

  useEffect(() => {
    const host = graphHostRef.current
    if (!host || flowWithStatus.nodes.length === 0) return
    let timeoutId: number | null = null
    const observer = new ResizeObserver(() => {
      if (timeoutId) {
        window.clearTimeout(timeoutId)
      }
      timeoutId = window.setTimeout(() => fitWorkflowView(180), 90)
    })
    observer.observe(host)
    return () => {
      observer.disconnect()
      if (timeoutId) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [fitWorkflowView, flowWithStatus.nodes.length])

  if (
    !definition &&
    Object.keys(validatedNodes).length === 0 &&
    Object.keys(validatedEdges).length === 0
  ) {
    const hasDataSources = dataSourceIds.length > 0
    return (
      <div className="right-panel-empty">
        <div className="right-panel-empty-kicker">Workflow</div>
        <WorkflowIcon className="right-panel-empty-icon" />
        <h3 className="right-panel-empty-title">
          {hasDataSources ? 'Ready to analyze' : 'Attach data to begin'}
        </h3>
        <p className="right-panel-empty-subtitle">
          {hasDataSources 
            ? `You have ${dataSourceIds.length} attached data source(s). Ask DeepEye to analyze them and the workflow graph will open here.`
            : 'Upload a file or connect a database from the composer to start your first analysis workflow.'}
        </p>
        
        {hasDataSources && (
          <div className="panel-empty-suggestions">
            {[
              'Show me a summary of the data',
              'Analyze trends over time',
              'Visualize the distribution of key metrics'
            ].map((suggestion) => (
              <div
                key={suggestion}
                className="panel-empty-suggestion"
              >
                <span className="panel-empty-suggestion-label">"{suggestion}"</span>
                <span className="panel-empty-suggestion-arrow">
                  <ArrowUpRight size={13} />
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className={`workflow-live-panel workflow-live-panel--${isDark ? 'dark' : 'light'} panel-view`}
      style={workflowToneStyle}
    >
      <div className="panel-toolbar">
        <div className="panel-toolbar-main">
          <div className="panel-toolbar-icon">
            <WorkflowIcon />
          </div>
          <div className="panel-toolbar-copy">
            <div className="panel-toolbar-label">Workflow</div>
            <div className="panel-toolbar-title">Live graph</div>
            <div className="panel-toolbar-meta">
              {isViewSwitching && (
                <span className="panel-toolbar-status">
                  <Loader2 className="animate-spin" />
                  Switching session...
                </span>
              )}
              {runStatus && <span>Run: {runStatus}</span>}
              {runError && <span className="panel-toolbar-error">{runError}</span>}
              {error && <span className="panel-toolbar-error">{error}</span>}
              {displayFileError && <span className="panel-toolbar-error">{displayFileError}</span>}
            </div>
          </div>
        </div>
        <div className="panel-toolbar-actions">
          <select
            value={activeDraftIdForSession || ''}
            disabled={!sessionId || isLoadingFiles || availableDrafts.length === 0 || isStreaming}
            onChange={(event) => loadWorkflowDraft(event.target.value)}
            className="panel-toolbar-select"
          >
            {availableDrafts.length === 0 ? (
              <option value="">No workflow drafts</option>
            ) : (
              availableDrafts.map((draft) => (
                <option key={draft.id} value={draft.id}>
                  {getDraftDisplayName(draft)}
                </option>
              ))
            )}
          </select>
          <button
            type="button"
            disabled={!sessionId || isLoadingFile || isStreaming || isSaving}
            onClick={async () => {
              if (!sessionId) return
              setIsSaving(true)
              try {
                await persistWorkflowDraft()
              } finally {
                setIsSaving(false)
              }
            }}
            className="panel-toolbar-btn"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            disabled={
              Object.keys(nodeDefs).length === 0 ||
              isStreaming ||
              isExporting
            }
            onClick={() => {
              if (Object.keys(nodeDefs).length === 0) {
                if (sessionId) {
                  setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
                }
                return
              }
              setIsExporting(true)
              try {
                const definition = toDefinition(flow.nodes, flow.edges, nodeDefs)
                const filename =
                  (activeDraftForSession?.display_name ? `${activeDraftForSession.display_name}.json` : null) ||
                  (activeDraftIdForSession ? `draft-${activeDraftIdForSession.slice(0, 8)}.json` : 'workflow.json')
                const json = JSON.stringify(definition, null, 2)
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
            }}
            className="panel-toolbar-btn"
          >
            {isExporting ? 'Exporting...' : 'Export'}
          </button>
          <button
            type="button"
            disabled={!sessionId || isStreaming || isRunning || flow.nodes.length === 0}
            onClick={async () => {
              if (sessionId) {
                setIsRunning(true)
                setVideoProgressVisible(sessionId, false)
                try {
                  const saved = await persistWorkflowDraft()
                  if (!saved) return
                  const filePath = saved.filePath
                  const draftId = saved.draft.id
                  setRunStatus(sessionId, 'running', null)
                  setActiveRun(
                    sessionId,
                    buildOptimisticRun(sessionId, filePath, 'running', { draftId }),
                  )
                  setRunOutput(sessionId, '')
                  ensureSessionEventStream(sessionId)
                  const response = await sessionApi.runWorkflowDraft(sessionId, draftId)
                  if (response.error) {
                    setRunStatus(sessionId, 'failed', response.error)
                    setWorkflowError(sessionId, response.error)
                    setActiveRun(
                      sessionId,
                      buildOptimisticRun(sessionId, filePath, 'failed', {
                        error: response.error,
                        draftId,
                        runId: response.run_id ?? null,
                      }),
                    )
                    setRunOutput(sessionId, response.error)
                  } else {
                    const nextStatus = response.status === 'queued' ? 'running' : response.status
                    setRunStatus(sessionId, nextStatus, null)
                    setWorkflowError(sessionId, null)
                    setActiveRun(
                      sessionId,
                      buildOptimisticRun(sessionId, filePath, nextStatus, {
                        taskId: response.task_id ?? null,
                        turnId: response.turn_id ?? null,
                        draftId: response.draft_id ?? draftId,
                        runId: response.run_id ?? null,
                      }),
                    )
                    if (response.status && response.status !== 'queued') {
                      setRunOutput(sessionId, '')
                    }
                  }
                } catch (err) {
                  const message = err instanceof Error ? err.message : 'Failed to run workflow.'
                  setRunStatus(sessionId, 'failed', message)
                  setWorkflowError(sessionId, message)
                  setActiveRun(
                    sessionId,
                    buildOptimisticRun(sessionId, activeFilePathForControls, 'failed', {
                      error: message,
                      draftId: activeDraftIdForSession || null,
                    }),
                  )
                  setRunOutput(sessionId, message)
                } finally {
                  setIsRunning(false)
                }
              }
            }}
            className="panel-toolbar-btn panel-toolbar-btn--primary"
          >
            {isRunning ? 'Running...' : 'Run'}
          </button>
        </div>
      </div>
      <div className="flex min-h-0 flex-1">
        <div ref={graphHostRef} className="min-w-0 flex-1">
          <WorkflowGraph
            nodes={flowWithStatus.nodes}
            edges={flowWithStatus.edges}
            nodeTypes={nodeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            panOnScroll
            fitView
            fitViewOptions={{ padding: 0.22, minZoom: 0.55, maxZoom: 1.08 }}
            onInit={(instance) => {
              reactFlowRef.current = instance
              fitWorkflowView(0)
            }}
            className="workflow-canvas workflow-canvas--panel"
            defaultEdgeOptions={{
              style: { stroke: 'var(--workflow-link)', strokeWidth: 2.25 },
              animated: false,
            }}
            backgroundVariant={BackgroundVariant.Dots}
            backgroundGap={20}
            backgroundSize={1.1}
            backgroundColor="var(--workflow-grid)"
            showControls
            showMiniMap
            miniMapNodeColor={(node) => {
              switch (node.data.runStatus) {
                case 'running':
                  return isDark ? '#7ed9ca' : '#0f766e'
                case 'success':
                  return isDark ? '#4ade80' : '#15803d'
                case 'failed':
                  return '#ef4444'
                case 'pending':
                  return isDark ? '#f3b560' : '#c27a1a'
                default:
                  return isDark ? '#385250' : '#7aa59b'
              }
            }}
          />
        </div>
        <WorkflowInspector
          selectedNodeId={selectedNodeId}
          nodeDefs={nodeDefs}
          nodes={flow.nodes}
          activeRun={activeRun}
          runOutput={runOutput}
          onUpdateParam={(nodeId, key, value) => {
            if (!sessionId) return
            updateWorkflowNodeParam(sessionId, nodeId, key, value)
          }}
        />
      </div>
    </div>
  )
}
