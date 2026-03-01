import { useMemo, useEffect, useState, useCallback, useRef } from 'react'
import { BackgroundVariant } from 'reactflow'
import { Workflow as WorkflowIcon } from 'lucide-react'
import 'reactflow/dist/style.css'
import WorkflowNode from '../../workflow/WorkflowNode'
import { WorkflowGraph } from '../../workflow/WorkflowGraph'
import { chatApi } from '../../../api'
import { saveVideoConfig, extractVideoOutputParams } from '../../../api/video'
import { workflowFilesApi } from '../../../api/workflowFiles'
import { workflowsApi } from '../../../api/workflows'
import { sandboxApi } from '../../../api/sandbox'
import { WorkflowInspector } from '../../workflow/WorkflowInspector'
import { useChatStore } from '../../../stores/chat'
import { useWorkflowNodesStore } from '../../../stores/workflowNodes'
import { useWorkflowSessionsStore } from '../../../stores/workflowSessions'
import { useRightPanelStore } from '../../../stores/rightPanel'
import { useTheme } from '../../../hooks/useTheme'

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

function typeToLabel(type: string) {
  return type
    .replace(/[._]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function validateGraph(
  nodesMap: Record<string, DefinitionNode>,
  edgesMap: Record<string, DefinitionEdge>,
  nodeDefs: Record<string, any>,
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

function toFlow(definition: Record<string, unknown>, nodeDefs: Record<string, any>) {
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
      style: { stroke: '#6366f1', strokeWidth: 2 },
    }))

  return { nodes, edges }
}

function toDefinition(nodes: any[], edges: any[], nodeDefs: Record<string, any>) {
  const nodeMap: Record<string, any> = {}
  nodes.forEach((node) => {
    const def = nodeDefs[node.data.type]
    if (!def) return
    nodeMap[node.id] = {
      id: node.id,
      type: node.data.type,
      inputs: Object.fromEntries(
        def.inputs.map((p: any) => [p.id, { schema: p.schema, required: !!p.required, multiple: p.multiple }]),
      ),
      outputs: Object.fromEntries(def.outputs.map((p: any) => [p.id, { schema: p.schema }])),
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
  const setNodeStatus = useWorkflowSessionsStore((state) => state.setNodeStatus)
  const setRunStatus = useWorkflowSessionsStore((state) => state.setRunStatus)
  const setWorkflowDefinition = useWorkflowSessionsStore((state) => state.setDefinition)
  const clearWorkflow = useWorkflowSessionsStore((state) => state.clearDraft)
  const addWorkflowNode = useWorkflowSessionsStore((state) => state.addDraftNode)
  const addWorkflowEdge = useWorkflowSessionsStore((state) => state.addDraftEdge)
  const updateWorkflowNodeParam = useWorkflowSessionsStore((state) => state.updateDraftNodeParam)
  const setActiveFilePath = useWorkflowSessionsStore((state) => state.setActiveFilePath)
  const setActiveRun = useWorkflowSessionsStore((state) => state.setActiveRun)
  const setRunOutput = useWorkflowSessionsStore((state) => state.setRunOutput)
  const setViewState = useWorkflowSessionsStore((state) => state.setViewState)
  const setFiles = useWorkflowSessionsStore((state) => state.setFiles)
  const setFileError = useWorkflowSessionsStore((state) => state.setFileError)
  const setValidatedGraph = useWorkflowSessionsStore((state) => state.setValidatedGraph)
  const clearValidated = useWorkflowSessionsStore((state) => state.clearValidated)
  const setVideoProgressVisible = useWorkflowSessionsStore((state) => state.setVideoProgressVisible)
  const appendVideoProgressLog = useWorkflowSessionsStore((state) => state.appendVideoProgressLog)
  const setVideoProgressStep = useWorkflowSessionsStore((state) => state.setVideoProgressStep)
  const openOrFocusTab = useRightPanelStore((state) => state.openOrFocusTab)

  const notifyFilesChanged = useChatStore((state) => state.notifyFilesChanged)
  const isStreaming = useChatStore((state) => state.isStreaming)
  const sandboxReadySessionId = useChatStore((state) => state.sandboxReadySessionId)
  const sessionIdFromStore = useChatStore((state) => state.sessionId)
  const sessionMessages = useChatStore((state) => state.messages)

  const nodeDefs = useWorkflowNodesStore((state) => state.nodeDefs)
  const loadNodeDefs = useWorkflowNodesStore((state) => state.loadNodeDefs)

  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const [isLoadingFiles, setIsLoadingFiles] = useState(false)
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [newNodeIds, setNewNodeIds] = useState<Set<string>>(new Set())
  const [newEdgeIds, setNewEdgeIds] = useState<Set<string>>(new Set())
  const [isSaving, setIsSaving] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const runEventSourceRef = useRef<EventSource | null>(null)

  const activeFilePathRef = useRef<string | null>(null)
  const isLoadingFilesRef = useRef(false)
  const prevNodeIdsRef = useRef<Set<string>>(new Set())
  const prevEdgeIdsRef = useRef<Set<string>>(new Set())

  const definition = sessionState?.definition ?? null
  const validatedNodes = sessionState?.validatedNodes ?? {}
  const validatedEdges = sessionState?.validatedEdges ?? {}
  const nodeStatus = sessionState?.nodeStatus ?? {}
  const runStatus = sessionState?.runStatus ?? null
  const runError = sessionState?.runError ?? null
  const error = sessionState?.error ?? null
  const displayFileError = sessionState?.fileError ?? null
  const activeRun = sessionState?.activeRun ?? null
  const runOutput = sessionState?.runOutput ?? ''

  const activeDraftNodes = activeSessionState?.draftNodes ?? {}
  const activeDraftEdges = activeSessionState?.draftEdges ?? {}
  const activeFiles = activeSessionState?.files ?? []
  const activeFilePathForControls = activeSessionState?.activeFilePath ?? null
  const activeViewState = activeSessionState?.viewState ?? 'idle'

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
    isLoadingFilesRef.current = isLoadingFiles
  }, [isLoadingFiles])

  useEffect(() => {
    return () => {
      if (runEventSourceRef.current) {
        runEventSourceRef.current.close()
        runEventSourceRef.current = null
      }
    }
  }, [])

  const ensureRunEventStream = useCallback(() => {
    if (!sessionId || isStreaming || runEventSourceRef.current) {
      return
    }
    const es = chatApi.createEventSource(sessionId)
    runEventSourceRef.current = es
    es.onmessage = (event) => {
      try {
        const agentEvent = JSON.parse(event.data) as { type?: string; data?: Record<string, unknown> }
        if (agentEvent.type === 'token') {
          const data = agentEvent.data || {}
          if (data.source === 'workflow' && typeof data.content === 'string') {
            appendVideoProgressLog(sessionId, data.content)
            const stepMatch = data.content.match(/Step\s*(\d)\s*\/\s*4/)
            if (stepMatch) {
              setVideoProgressVisible(sessionId, true)
              const stepIndex = parseInt(stepMatch[1], 10) - 1
              if (stepIndex >= 0 && stepIndex <= 3) setVideoProgressStep(sessionId, stepIndex)
            }
          }
          return
        }
        if (agentEvent.type !== 'workflow_event') {
          return
        }
        const data = agentEvent.data || {}
        const filePath = typeof data.file_path === 'string' ? data.file_path : null
        const phase = typeof data.phase === 'string' ? data.phase : ''
        const payload = (data.payload as Record<string, unknown>) || {}
        if (filePath && activeFilePathRef.current && activeFilePathRef.current !== filePath) {
          return
        }
        if (phase === 'run_start') {
          setVideoProgressVisible(sessionId, true)
          openOrFocusTab('video-preview', {})
          return
        }
        if (phase === 'node_status') {
          const nodeId = typeof payload?.node_id === 'string' ? payload?.node_id : ''
          const status = typeof payload?.status === 'string' ? payload?.status : ''
          const outputs = typeof payload?.outputs === 'object' ? payload?.outputs : undefined
          if (nodeId && status) {
            setNodeStatus(sessionId, nodeId, status, outputs as Record<string, unknown> | undefined)
            const session = useWorkflowSessionsStore.getState().sessions[sessionId]
            const root = (session?.definition as Record<string, { nodes?: Record<string, { type?: string }> }> | null)?.root
            const nodesMap = session?.validatedNodes ?? root?.nodes ?? {}
            const nodeType = (nodesMap[nodeId] as { type?: string } | undefined)?.type
            if (nodeType === 'video.generator') {
              setVideoProgressVisible(sessionId, status === 'running')
            }
          }
          return
        }
        if (phase === 'create_workflow' || phase === 'update_workflow') {
          const workflow = payload?.workflow || payload?.definition
          if (workflow && typeof workflow === 'object') {
            const root = (workflow as Record<string, unknown>).root as Record<string, unknown> | undefined
            const nodes = (root?.nodes as Record<string, unknown>) || {}
            const edges = (root?.edges as Record<string, unknown>) || {}
            const nodeList = Object.values(nodes)
            const edgeList = Object.values(edges)
            const stepDelayMs = 50

            clearWorkflow(sessionId)
            clearValidated(sessionId)
            if (filePath) {
              setActiveFilePath(sessionId, filePath)
            }
            setWorkflowDefinition(sessionId, workflow as Record<string, unknown>)
            setViewState(sessionId, 'switching')
            setWorkflowError(sessionId, null)

            nodeList.forEach((node, index) => {
              setTimeout(() => addWorkflowNode(sessionId, node as Record<string, unknown>), index * stepDelayMs)
            })
            const edgeStart = nodeList.length * stepDelayMs
            edgeList.forEach((edge, index) => {
              setTimeout(
                () => addWorkflowEdge(sessionId, edge as Record<string, unknown>),
                edgeStart + index * stepDelayMs,
              )
            })
            const totalDelay = (nodeList.length + edgeList.length) * stepDelayMs
            setTimeout(() => setViewState(sessionId, 'ready'), totalDelay)
          }
          return
        }
        if (phase === 'run_end') {
          setVideoProgressVisible(sessionId, false)
          const status = typeof payload?.status === 'string' ? payload?.status : 'failed'
          const error = typeof payload?.error === 'string' ? payload?.error : null
          setRunStatus(sessionId, status, error)
          setActiveRun(sessionId, {
            id: `file:${filePath || ''}`,
            workflow_id: `file:${filePath || ''}`,
            status,
            error: error || undefined,
            created_at: new Date().toISOString(),
            finished_at: new Date().toISOString(),
          })
          if (payload?.outputs && typeof payload.outputs === 'object') {
            setRunOutput(sessionId, JSON.stringify(payload.outputs, null, 2))
            console.log('🎬 WorkflowLivePanel: run_end phase, checking for video output...')
            console.log('📊 WorkflowLivePanel: Full outputs object:', JSON.stringify(payload.outputs, null, 2))
            console.log('📊 WorkflowLivePanel: Output keys:', Object.keys(payload.outputs))
            const videoParams = extractVideoOutputParams(payload.outputs as Record<string, unknown>)
            console.log('🎬 WorkflowLivePanel: Extracted video params:', videoParams)
            if (!videoParams.taskId && !videoParams.configPath) {
              console.warn('⚠️ WorkflowLivePanel: No video output detected. Output structure:', {
                nodeIds: Object.keys(payload.outputs),
                firstNodeOutput: payload.outputs[Object.keys(payload.outputs)[0]],
              })
            }
            if (videoParams.taskId || videoParams.configPath) {
              console.log('🎬 WorkflowLivePanel: Video output detected, opening preview panel...', {
                taskId: videoParams.taskId,
                configPath: videoParams.configPath,
                hasConfig: !!videoParams.config,
              })
              if (videoParams.taskId && videoParams.config && Object.keys(videoParams.config).length > 0) {
                console.log('🎬 WorkflowLivePanel: Saving video config first...')
                saveVideoConfig(videoParams.taskId, videoParams.config as any)
                  .then(() => {
                    console.log('✅ WorkflowLivePanel: Config saved, opening preview panel')
                    openOrFocusTab('video-preview', videoParams)
                  })
                  .catch((e) => {
                    console.error('❌ WorkflowLivePanel: saveVideoConfig failed', e)
                    console.log('🎬 WorkflowLivePanel: Opening preview panel anyway...')
                    openOrFocusTab('video-preview', videoParams)
                  })
              } else {
                console.log('🎬 WorkflowLivePanel: Opening preview panel directly (no config to save)')
                openOrFocusTab('video-preview', videoParams)
              }
            } else {
              console.log('⚠️ WorkflowLivePanel: No video output detected in payload.outputs')
            }
          } else if (error) {
            setRunOutput(sessionId, error)
          }
          es.close()
          runEventSourceRef.current = null
        }
      } catch {
        // ignore parse errors
      }
    }
    es.onerror = () => {
      es.close()
      runEventSourceRef.current = null
    }
  }, [
    sessionId,
    isStreaming,
    setNodeStatus,
    setRunStatus,
    setActiveRun,
    setRunOutput,
    setVideoProgressVisible,
    appendVideoProgressLog,
    setVideoProgressStep,
    clearWorkflow,
    clearValidated,
    setActiveFilePath,
    setWorkflowDefinition,
    setViewState,
    setWorkflowError,
    addWorkflowNode,
    addWorkflowEdge,
    openOrFocusTab,
  ])

  useEffect(() => {
    if (sessionId) {
      loadNodeDefs()
    }
  }, [sessionId, loadNodeDefs])

  const loadWorkflowFile = useCallback(
    async (path: string) => {
      if (!sessionId) return
      setIsLoadingFile(true)
      setFileError(sessionId, null)
      try {
        const response = await sandboxApi.getFileContent(sessionId, path)
        const parsed = JSON.parse(response.content) as Record<string, unknown>
        const root = (parsed.root as Record<string, unknown>) || parsed
        const nodes = (root.nodes as Record<string, any>) || {}
        const edges = (root.edges as Record<string, any>) || {}
        clearWorkflow(sessionId)
        Object.values(nodes).forEach((node) => addWorkflowNode(sessionId, node))
        Object.values(edges).forEach((edge) => addWorkflowEdge(sessionId, edge))
        setWorkflowDefinition(sessionId, parsed)
        setActiveFilePath(sessionId, path)
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
      setActiveFilePath,
      setWorkflowError,
      setValidatedGraph,
      setViewState,
      nodeDefs,
    ],
  )

  const refreshFiles = useCallback(
    async (shouldLoadFile: boolean) => {
      if (!sessionId || sandboxReadySessionId !== sessionId) return
      if (isLoadingFilesRef.current) return
      setIsLoadingFiles(true)
      setFileError(sessionId, null)
      try {
        const response = await sandboxApi.listFiles(sessionId, WORKFLOW_DIR)
        const jsonFiles = response.files
          .filter((file) => file.type === 'file' && file.name.endsWith('.json'))
          .map((file) => file.path)
          .sort((a, b) => a.localeCompare(b))
        const currentActiveFilePath = activeFilePathRef.current
        let nextFiles = jsonFiles
        if (currentActiveFilePath && !jsonFiles.includes(currentActiveFilePath)) {
          nextFiles = [currentActiveFilePath, ...jsonFiles]
        }
        setFiles(sessionId, nextFiles)
        if (!shouldLoadFile || isStreaming) return
        if (jsonFiles.length === 0) {
          setActiveFilePath(sessionId, null)
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
        if (!currentActiveFilePath || !jsonFiles.includes(currentActiveFilePath)) {
          await loadWorkflowFile(jsonFiles[0])
        }
        setViewState(sessionId, 'ready')
      } catch (err) {
        setFiles(sessionId, [])
        setFileError(sessionId, err instanceof Error ? err.message : 'Failed to list workflow files.')
        setViewState(sessionId, 'error')
      } finally {
        setIsLoadingFiles(false)
      }
    },
    [
      sessionId,
      loadWorkflowFile,
      setActiveFilePath,
      isStreaming,
      sandboxReadySessionId,
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
    if (sandboxReadySessionId !== sessionId) return
    refreshFiles(true)
  }, [sessionId, sandboxReadySessionId, refreshFiles])

  useEffect(() => {
    if (!sessionId) return
    if (sessionIdFromStore !== sessionId) return
    if (sessionMessages.length > 0) return
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
    setActiveFilePath,
    setWorkflowDefinition,
    clearValidated,
    setViewState,
  ])

  useEffect(() => {
    if (!sessionId) return
    if (sandboxReadySessionId !== sessionId) return
    if (isLoadingFiles || isStreaming) return
    if (activeFiles.length > 0) return
    setActiveFilePath(sessionId, null)
    setWorkflowDefinition(sessionId, null)
    clearValidated(sessionId)
    setViewState(sessionId, 'empty')
    setDisplaySessionId(sessionId)
    setIsViewSwitching(false)
  }, [
    sessionId,
    sandboxReadySessionId,
    isLoadingFiles,
    isStreaming,
    activeFiles.length,
    setActiveFilePath,
    setWorkflowDefinition,
    clearValidated,
    setViewState,
  ])

  useEffect(() => {
    if (!sessionId) return
    if (sandboxReadySessionId !== sessionId) return
    if (activeFiles.length > 0) return
    if (activeViewState === 'empty') {
      clearValidated(sessionId)
      setWorkflowDefinition(sessionId, null)
      setDisplaySessionId(sessionId)
      setIsViewSwitching(false)
      return
    }
    refreshFiles(true)
  }, [sessionId, sandboxReadySessionId, activeFiles.length, activeViewState, refreshFiles])

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

  const nodeTypes = useMemo(() => NODE_TYPES, [])

  if (
    !definition &&
    Object.keys(validatedNodes).length === 0 &&
    Object.keys(validatedEdges).length === 0
  ) {
    const hasDataSources = dataSourceIds.length > 0
    return (
      <div className={`h-full w-full flex flex-col items-center justify-center p-8 text-center ${
        isDark ? 'bg-slate-950' : 'bg-slate-50'
      }`}>
        <div className={`mb-6 rounded-2xl p-4 ring-1 ${
          isDark ? 'bg-slate-900/50 ring-slate-800' : 'bg-white ring-slate-200'
        }`}>
          <WorkflowIcon className={`h-8 w-8 ${isDark ? 'text-indigo-400' : 'text-indigo-600'}`} />
        </div>
        <h3 className={`mb-2 text-lg font-medium ${isDark ? 'text-slate-200' : 'text-slate-900'}`}>
          {hasDataSources ? 'Ready to Analyze' : 'Select Data Source'}
        </h3>
        <p className={`max-w-xs text-sm leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
          {hasDataSources 
            ? `You have ${dataSourceIds.length} data source(s) selected. Ask DeepEye to analyze them, and the workflow will appear here.`
            : 'Please select a database or upload a file from the sidebar to start your data exploration.'}
        </p>
        
        {hasDataSources && (
          <div className="mt-8 flex flex-col gap-2 w-full max-w-xs">
            <div className={`text-[10px] font-semibold uppercase tracking-wider mb-1 ${
              isDark ? 'text-slate-500' : 'text-slate-400'
            }`}>Suggested prompts</div>
            {[
              'Show me a summary of the data',
              'Analyze trends over time',
              'Visualize the distribution of key metrics'
            ].map((suggestion) => (
              <div 
                key={suggestion}
                className={`rounded-lg border px-3 py-2 text-xs text-left transition-colors cursor-default ${
                  isDark 
                    ? 'border-slate-800 bg-slate-900/30 text-slate-400 hover:bg-slate-800 hover:text-slate-200' 
                    : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                "{suggestion}"
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`h-full w-full flex flex-col ${isDark ? 'bg-slate-950' : 'bg-white'}`}>
      <div className={`flex items-center justify-between border-b px-3 py-2 text-xs ${
        isDark ? 'border-slate-800 bg-slate-900/60' : 'border-slate-200 bg-slate-50'
      }`}>
        <div className={`flex items-center gap-2 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
          <span className="font-semibold">Workflow</span>
          {isViewSwitching && <span className="text-slate-500">· Switching session...</span>}
          {runStatus && <span className={isDark ? 'text-slate-400' : 'text-slate-500'}>· {runStatus}</span>}
          {runError && <span className="text-rose-300">· {runError}</span>}
          {error && <span className="text-rose-300">· {error}</span>}
          {displayFileError && <span className="text-rose-300">· {displayFileError}</span>}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={activeFilePathForControls || ''}
            disabled={!sessionId || isLoadingFiles || activeFiles.length === 0 || isStreaming}
            onChange={(event) => loadWorkflowFile(event.target.value)}
            className={`rounded-md border px-2 py-1 text-xs ${
              isDark 
                ? 'border-slate-700 bg-slate-950 text-slate-200' 
                : 'border-slate-300 bg-white text-slate-700'
            }`}
          >
            {activeFiles.length === 0 ? (
              <option value="">No workflow files</option>
            ) : (
              activeFiles.map((file) => (
                <option key={file} value={file}>
                  {file.replace(`${WORKFLOW_DIR}/`, '')}
                </option>
              ))
            )}
          </select>
          <button
            type="button"
            disabled={!sessionId || !activeFilePathForControls || isLoadingFile || isStreaming || isSaving}
            onClick={async () => {
              if (!sessionId || !activeFilePathForControls) return
              if (Object.keys(nodeDefs).length === 0) {
                setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
                return
              }
              setIsSaving(true)
              try {
                const definition = toDefinition(flow.nodes, flow.edges, nodeDefs)
                await sandboxApi.writeFile(sessionId, activeFilePathForControls, JSON.stringify(definition, null, 2))
                notifyFilesChanged()
                setWorkflowDefinition(sessionId, definition)
                clearWorkflow(sessionId)
                Object.values(definition.root.nodes || {}).forEach((node) => addWorkflowNode(sessionId, node))
                Object.values(definition.root.edges || {}).forEach((edge) => addWorkflowEdge(sessionId, edge))
                setWorkflowError(sessionId, null)
              } catch (err) {
                setWorkflowError(sessionId, err instanceof Error ? err.message : 'Failed to save workflow.')
              } finally {
                setIsSaving(false)
              }
            }}
            className={`rounded-md border px-2 py-1 text-xs transition-colors ${
              isDark 
                ? 'border-slate-700 text-slate-200 hover:bg-slate-800' 
                : 'border-slate-300 text-slate-700 hover:bg-slate-100'
            } disabled:opacity-40`}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            disabled={
              !sessionId ||
              !activeFilePathForControls ||
              Object.keys(nodeDefs).length === 0 ||
              isStreaming ||
              isUploading
            }
            onClick={async () => {
              if (!sessionId || !activeFilePathForControls) return
              if (Object.keys(nodeDefs).length === 0) {
                setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
                return
              }
              setIsUploading(true)
              try {
                const definition = toDefinition(flow.nodes, flow.edges, nodeDefs)
                const filename = activeFilePathForControls.split('/').pop() || 'workflow.json'
                const name = filename.replace(/\.json$/i, '') || 'Untitled workflow'
                await workflowsApi.create({ name, description: '', definition } as any)
                setWorkflowError(sessionId, null)
              } catch (err) {
                setWorkflowError(sessionId, err instanceof Error ? err.message : 'Failed to upload workflow.')
              } finally {
                setIsUploading(false)
              }
            }}
            className={`rounded-md border px-2 py-1 text-xs transition-colors ${
              isDark 
                ? 'border-slate-700 text-slate-200 hover:bg-slate-800' 
                : 'border-slate-300 text-slate-700 hover:bg-slate-100'
            } disabled:opacity-40`}
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </button>
          <button
            type="button"
            disabled={
              !activeFilePathForControls ||
              Object.keys(nodeDefs).length === 0 ||
              isStreaming ||
              isExporting
            }
            onClick={() => {
              if (!activeFilePathForControls) return
              if (Object.keys(nodeDefs).length === 0) {
                if (sessionId) {
                  setWorkflowError(sessionId, 'Node definitions are not loaded yet.')
                }
                return
              }
              setIsExporting(true)
              try {
                const definition = toDefinition(flow.nodes, flow.edges, nodeDefs)
                const filename = activeFilePathForControls.split('/').pop() || 'workflow.json'
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
            className={`rounded-md border px-2 py-1 text-xs transition-colors ${
              isDark 
                ? 'border-slate-700 text-slate-200 hover:bg-slate-800' 
                : 'border-slate-300 text-slate-700 hover:bg-slate-100'
            } disabled:opacity-40`}
          >
            {isExporting ? 'Exporting...' : 'Export'}
          </button>
          <button
            type="button"
            disabled={!sessionId || !activeFilePathForControls || isStreaming || isRunning}
            onClick={async () => {
              if (sessionId && activeFilePathForControls) {
                setIsRunning(true)
                setVideoProgressVisible(sessionId, false)
                setRunStatus(sessionId, 'running', null)
                setActiveRun(sessionId, {
                  id: `file:${activeFilePathForControls}`,
                  workflow_id: `file:${activeFilePathForControls}`,
                  status: 'running',
                  created_at: new Date().toISOString(),
                  finished_at: null,
                })
                setRunOutput(sessionId, '')
                try {
                  ensureRunEventStream()
                  const response = await workflowFilesApi.run(sessionId, activeFilePathForControls)
                  if (response.error) {
                    setRunStatus(sessionId, 'failed', response.error)
                    setWorkflowError(sessionId, response.error)
                    setActiveRun(sessionId, {
                      id: `file:${activeFilePathForControls}`,
                      workflow_id: `file:${activeFilePathForControls}`,
                      status: 'failed',
                      error: response.error,
                      created_at: new Date().toISOString(),
                      finished_at: new Date().toISOString(),
                    })
                    setRunOutput(sessionId, response.error)
                  } else {
                    const nextStatus = response.status === 'queued' ? 'running' : response.status
                    setRunStatus(sessionId, nextStatus, null)
                    setWorkflowError(sessionId, null)
                    setActiveRun(sessionId, {
                      id: `file:${activeFilePathForControls}`,
                      workflow_id: `file:${activeFilePathForControls}`,
                      status: nextStatus,
                      created_at: new Date().toISOString(),
                      finished_at: response.status === 'queued' ? null : new Date().toISOString(),
                    })
                    if (response.outputs) {
                      setRunOutput(sessionId, JSON.stringify(response.outputs, null, 2))
                      const videoParams = extractVideoOutputParams(response.outputs as Record<string, unknown>)
                      if (videoParams.taskId || videoParams.configPath) {
                        if (videoParams.taskId && videoParams.config && Object.keys(videoParams.config).length > 0) {
                          try {
                            await saveVideoConfig(videoParams.taskId!, videoParams.config as any)
                          } catch (e) {
                            console.error('saveVideoConfig failed', e)
                          }
                        }
                        openOrFocusTab('video-preview', videoParams)
                      }
                    } else if (response.status && response.status !== 'queued') {
                      setRunOutput(sessionId, '')
                    }
                  }
                } catch (err) {
                  const message = err instanceof Error ? err.message : 'Failed to run workflow.'
                  setRunStatus(sessionId, 'failed', message)
                  setWorkflowError(sessionId, message)
                  setActiveRun(sessionId, {
                    id: `file:${activeFilePathForControls}`,
                    workflow_id: `file:${activeFilePathForControls}`,
                    status: 'failed',
                    error: message,
                    created_at: new Date().toISOString(),
                    finished_at: new Date().toISOString(),
                  })
                  setRunOutput(sessionId, message)
                } finally {
                  setIsRunning(false)
                }
              }
            }}
            className={`rounded-md border px-2 py-1 text-xs transition-colors ${
              isDark 
                ? 'border-slate-700 text-slate-200 hover:bg-slate-800' 
                : 'border-slate-300 text-slate-700 hover:bg-slate-100'
            } disabled:opacity-40`}
          >
            {isRunning ? 'Running...' : 'Run'}
          </button>
        </div>
      </div>
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
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
            fitViewOptions={{ padding: 0.2 }}
            className={isDark ? 'bg-slate-950' : 'bg-slate-50'}
            backgroundVariant={BackgroundVariant.Dots}
            backgroundGap={20}
            backgroundSize={1}
            backgroundColor={isDark ? '#334155' : '#cbd5e1'}
            showControls
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
