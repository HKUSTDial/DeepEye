import { chatApi, type AgentEvent } from '../api'
import { extractVideoOutputParams } from '../api/video'
import {
  selectCurrentSessionId,
  useChatStore,
} from '../stores/chat'
import { useReportStore } from '../stores/report'
import { useRightPanelStore } from '../stores/rightPanel'
import { useWorkflowSessionsStore } from '../stores/workflowSessions'
import {
  buildWorkflowRunFromEvent,
  getWorkflowArtifacts,
  getWorkflowOutputs,
  matchesTrackedWorkflowEvent,
  parseWorkflowEvent,
} from '../features/workflow/events'
import {
  createArtifactPhase,
  createConnectionLostPhase,
  createGenericErrorPhase,
  createNodePhase,
  createPlanningPhase,
  createRunCompletionPhase,
  createRunStartPhase,
  createTokenPhase,
} from '../features/workflow/runPhase'
import { getDashboardProgressStage, isDashboardProgressMessage } from '../utils/dashboardProgress'
import { parseVideoProgressStep } from '../utils/videoProgress'
import {
  getArtifactError,
  getArtifactFileName,
  getArtifactHtml,
  getArtifactKind,
  getArtifactPreviewUrl,
  getArtifactSteps,
  getArtifactTaskId,
} from '../utils/artifactUtils'
import type { WorkflowArtifactPayload } from '../types'

type ErrorListener = (error: string | null) => void
type WorkflowHandleResult = 'handled' | 'ignored' | 'unparsed'

const RUN_SCOPED_PHASES = new Set([
  'run_start',
  'node_status',
  'run_end',
  'artifact_progress',
  'artifact_ready',
  'artifact_refresh',
  'artifact_failed',
  'error',
])

let currentEventSource: EventSource | null = null
let currentSessionId: string | null = null
let currentError: string | null = null
const errorListeners = new Set<ErrorListener>()

function emitError(error: string | null) {
  currentError = error
  for (const listener of errorListeners) {
    listener(error)
  }
}

function isCurrentSession(sessionId: string) {
  return selectCurrentSessionId(useChatStore.getState()) === sessionId
}

function openOrFocusTabIfCurrent(
  sessionId: string,
  pluginId: string,
  params?: Record<string, unknown>,
) {
  if (!isCurrentSession(sessionId)) return
  useRightPanelStore.getState().openOrFocusTab(pluginId, params)
}

function openOrFocusPluginTabIfCurrent(
  sessionId: string,
  pluginId: string,
  params?: Record<string, unknown>,
) {
  if (!isCurrentSession(sessionId)) return

  const rightPanel = useRightPanelStore.getState()
  for (const pane of rightPanel.panes) {
    const existing = pane.tabs.find((tab) => tab.pluginId === pluginId)
    if (existing) {
      rightPanel.setActiveTab(pane.id, existing.id)
      rightPanel.setActivePane(pane.id)
      rightPanel.setCollapsed(false)
      return
    }
  }

  rightPanel.openOrFocusTab(pluginId, params)
}

function setRightPanelRatioIfCurrent(sessionId: string, ratio: number) {
  if (!isCurrentSession(sessionId)) return
  useRightPanelStore.getState().setPanelRatio(ratio)
}

function pushChatEventIfCurrent(sessionId: string, event: AgentEvent) {
  if (!isCurrentSession(sessionId)) return
  useChatStore.getState().pushEvent(event)
}

function stopStreamingIfCurrent(sessionId: string) {
  if (!isCurrentSession(sessionId)) return
  useChatStore.getState().stopStreaming()
}

function handleWorkflowArtifactEvent(
  sessionId: string,
  phase: string,
  payload: Record<string, unknown>,
) {
  const artifact = typeof payload.artifact === 'object' && payload.artifact
    ? (payload.artifact as Record<string, unknown>)
    : null
  const typedArtifact = artifact as WorkflowArtifactPayload | null
  const kind = getArtifactKind(typedArtifact) ?? ''

  if (!typedArtifact || !kind) {
    return false
  }

  const workflowStore = useWorkflowSessionsStore.getState()
  workflowStore.recordArtifact(sessionId, typedArtifact)
  const artifactPhase = createArtifactPhase(
    phase as 'artifact_progress' | 'artifact_ready' | 'artifact_refresh' | 'artifact_failed',
    payload,
  )
  if (artifactPhase) {
    workflowStore.setRunPhase(sessionId, artifactPhase)
  }

  if (kind === 'report') {
    if (phase === 'artifact_progress') {
      const stepContent = typeof payload.message === 'string' ? payload.message : ''
      if (stepContent) {
        const reportStore = useReportStore.getState()
        const currentlyGenerating = !!reportStore.sessions[sessionId]?.isGenerating
        if (!currentlyGenerating) {
          reportStore.startGeneration(sessionId)
          openOrFocusPluginTabIfCurrent(sessionId, 'report')
          setRightPanelRatioIfCurrent(sessionId, 28)
        }
        reportStore.addReportStep(sessionId, stepContent)
      }
      return true
    }

    if (phase === 'artifact_ready' || phase === 'artifact_failed') {
      const steps = Array.isArray(payload.steps)
        ? payload.steps.filter((item): item is string => typeof item === 'string')
        : getArtifactSteps(typedArtifact)
      const reportHtml =
        typeof payload.report_html === 'string'
          ? payload.report_html
          : getArtifactHtml(typedArtifact)
      const reportFilename =
        typeof payload.report_filename === 'string'
          ? payload.report_filename
          : getArtifactFileName(typedArtifact, 'report')
      const error =
        typeof payload.error === 'string'
          ? payload.error
          : phase === 'artifact_failed'
            ? getArtifactError(typedArtifact) ?? 'Report generation failed'
            : getArtifactError(typedArtifact)
      const reportStore = useReportStore.getState()
      reportStore.setReportResult(sessionId, reportHtml, steps, reportFilename, error)
      reportStore.stopGeneration(sessionId)
      openOrFocusPluginTabIfCurrent(sessionId, 'report')
      setRightPanelRatioIfCurrent(sessionId, 28)
      return true
    }
  }

  if (kind === 'dashboard') {
    if (phase === 'artifact_ready') {
      workflowStore.setDashboardProgressPercent(sessionId, 100)
      workflowStore.setDashboardProgressVisible(sessionId, false)
      openOrFocusPluginTabIfCurrent(sessionId, 'dashboard')
      return true
    }
    if (phase === 'artifact_refresh') {
      workflowStore.setDashboardProgressVisible(sessionId, false)
      workflowStore.triggerDashboardRefresh(sessionId)
      openOrFocusPluginTabIfCurrent(sessionId, 'dashboard')
      return true
    }
  }

  if (kind === 'video') {
    const taskId = getArtifactTaskId(typedArtifact)
    const videoUrl = getArtifactPreviewUrl(typedArtifact)
    if (videoUrl) {
      useWorkflowSessionsStore.getState().setVideoPreviewUrl(sessionId, videoUrl)
    }
    if (phase === 'artifact_ready') {
      openOrFocusPluginTabIfCurrent(sessionId, 'video-preview', taskId ? { taskId } : {})
      return true
    }
  }

  return false
}

function shouldProcessRunScopedEvent(sessionId: string, event: NonNullable<ReturnType<typeof parseWorkflowEvent>>) {
  if (!RUN_SCOPED_PHASES.has(event.phase)) {
    return true
  }

  const session = useWorkflowSessionsStore.getState().sessions[sessionId]
  return matchesTrackedWorkflowEvent(session?.activeRun, session?.activeDraftId, event)
}

function handleWorkflowEvent(sessionId: string, agentEvent: AgentEvent): WorkflowHandleResult {
  const workflowEvent = parseWorkflowEvent(agentEvent)
  if (!workflowEvent) {
    return 'unparsed'
  }

  if (!shouldProcessRunScopedEvent(sessionId, workflowEvent)) {
    return 'ignored'
  }

  const workflowStore = useWorkflowSessionsStore.getState()
  const { filePath, phase, payload } = workflowEvent

  if (handleWorkflowArtifactEvent(sessionId, phase, payload)) {
    return 'handled'
  }

  const workflowSession = workflowStore.sessions[sessionId]
  const activeDraftId = workflowSession?.activeDraftId

  if (workflowEvent.draftId && activeDraftId && activeDraftId !== workflowEvent.draftId) {
    workflowStore.clearDraft(sessionId)
    workflowStore.clearValidated(sessionId)
    workflowStore.setActiveDraftId(sessionId, workflowEvent.draftId)
    if (filePath) {
      workflowStore.setActiveFilePath(sessionId, filePath)
    }
    workflowStore.setViewState(sessionId, 'switching')
  }

  if (phase === 'create_workflow' || phase === 'update_workflow') {
    const workflow = payload.workflow || payload.definition
    if (workflow && typeof workflow === 'object') {
      const root = (workflow as Record<string, unknown>).root as Record<string, unknown> | undefined
      const nodes = (root?.nodes as Record<string, unknown>) || {}
      const edges = (root?.edges as Record<string, unknown>) || {}
      const nodeList = Object.values(nodes)
      const edgeList = Object.values(edges)
      const stepDelayMs = 200

      workflowStore.clearDraft(sessionId)
      workflowStore.clearValidated(sessionId)
      if (workflowEvent.draftId) {
        workflowStore.setActiveDraftId(sessionId, workflowEvent.draftId)
      }
      workflowStore.setActiveFilePath(sessionId, filePath)
      workflowStore.setDefinition(sessionId, workflow as Record<string, unknown>)
      workflowStore.setViewState(sessionId, 'switching')
      workflowStore.setError(sessionId, null)
      workflowStore.setRunPhase(sessionId, createPlanningPhase(filePath))
      useChatStore.getState().notifyFilesChanged()
      openOrFocusTabIfCurrent(sessionId, 'workflow')

      nodeList.forEach((node, index) => {
        window.setTimeout(() => {
          workflowStore.addDraftNode(sessionId, node as Record<string, unknown>)
        }, index * stepDelayMs)
      })
      const edgeStart = nodeList.length * stepDelayMs
      edgeList.forEach((edge, index) => {
        window.setTimeout(() => {
          workflowStore.addDraftEdge(sessionId, edge as Record<string, unknown>)
        }, edgeStart + index * stepDelayMs)
      })
      window.setTimeout(() => {
        workflowStore.setViewState(sessionId, 'ready')
      }, (nodeList.length + edgeList.length) * stepDelayMs)
    }
    return 'handled'
  }

  if (phase === 'node') {
    const node = payload.node
    if (node && typeof node === 'object') {
      workflowStore.addDraftNode(sessionId, node as Record<string, unknown>)
      workflowStore.setError(sessionId, null)
      openOrFocusTabIfCurrent(sessionId, 'workflow')
    }
    return 'handled'
  }

  if (phase === 'edge') {
    const edge = payload.edge
    if (edge && typeof edge === 'object') {
      workflowStore.addDraftEdge(sessionId, edge as Record<string, unknown>)
      workflowStore.setError(sessionId, null)
      openOrFocusTabIfCurrent(sessionId, 'workflow')
    }
    return 'handled'
  }

  if (phase === 'run_start') {
    workflowStore.setRunStatus(sessionId, 'running', null)
    workflowStore.setViewState(sessionId, 'ready')
    workflowStore.setActiveRun(sessionId, buildWorkflowRunFromEvent(sessionId, workflowEvent, 'running'))
    workflowStore.setError(sessionId, null)
    workflowStore.setRunPhase(sessionId, createRunStartPhase(filePath))
    return 'handled'
  }

  if (phase === 'node_status') {
    const nodeId = typeof payload.node_id === 'string' ? payload.node_id : ''
    const status = typeof payload.status === 'string' ? payload.status : ''
    const outputs = typeof payload.outputs === 'object' ? payload.outputs : undefined
    if (nodeId && status) {
      const typedOutputs = outputs as Record<string, unknown> | undefined
      workflowStore.setNodeStatus(sessionId, nodeId, status, typedOutputs)
      const session = workflowStore.sessions[sessionId]
      const root = (session?.definition as Record<string, { nodes?: Record<string, { type?: string }> }> | null)?.root
      const validatedNodes = session?.validatedNodes ?? {}
      const nodesMap =
        Object.keys(validatedNodes).length > 0
          ? validatedNodes
          : root?.nodes ?? {}
      const nodeType = (nodesMap[nodeId] as { type?: string } | undefined)?.type
      const nodePhase = createNodePhase(nodeId, nodeType ?? null, status, payload)
      if (nodePhase) {
        workflowStore.setRunPhase(sessionId, nodePhase)
      }
      if (nodeType === 'report.generate' && status === 'running') {
        const reportStore = useReportStore.getState()
        const currentlyGenerating = !!reportStore.sessions[sessionId]?.isGenerating
        if (!currentlyGenerating) {
          reportStore.startGeneration(sessionId)
        }
        openOrFocusPluginTabIfCurrent(sessionId, 'report')
        setRightPanelRatioIfCurrent(sessionId, 28)
      }
      if (nodeType === 'data.generate_dashboard' && status === 'running') {
        workflowStore.setDashboardProgressVisible(sessionId, true)
        openOrFocusPluginTabIfCurrent(sessionId, 'dashboard')
      }
      if (nodeType === 'video.generator') {
        workflowStore.setVideoProgressVisible(sessionId, status === 'running')
        if (status === 'running') {
          openOrFocusPluginTabIfCurrent(sessionId, 'video-preview')
        }
      }
    }
    return 'handled'
  }

  if (phase === 'run_end') {
    const status = typeof payload.status === 'string' ? payload.status : 'failed'
    const error = typeof payload.error === 'string' ? payload.error : null
    workflowStore.setDashboardProgressVisible(sessionId, false)
    workflowStore.setVideoProgressVisible(sessionId, false)
    workflowStore.setRunStatus(sessionId, status, error)
    workflowStore.setActiveRun(sessionId, buildWorkflowRunFromEvent(sessionId, workflowEvent, status, { error }))
    workflowStore.setRunPhase(
      sessionId,
      createRunCompletionPhase(status, error, workflowStore.sessions[sessionId]?.runPhase ?? null),
    )

    const artifacts = getWorkflowArtifacts(payload)
    artifacts.forEach((artifact) => {
      handleWorkflowArtifactEvent(sessionId, 'artifact_ready', { artifact })
    })

    const outputs = getWorkflowOutputs(payload)
    if (outputs) {
      workflowStore.setRunOutput(sessionId, JSON.stringify(outputs, null, 2))
      const videoParams = extractVideoOutputParams(outputs)
      const taskIdToOpen = videoParams.taskId ?? null
      if (taskIdToOpen) {
        openOrFocusTabIfCurrent(sessionId, 'video-preview', { taskId: taskIdToOpen })
      }
    } else if (error) {
      workflowStore.setRunOutput(sessionId, error)
    }
    return 'handled'
  }

  if (phase === 'error') {
    const message = typeof payload.message === 'string' ? payload.message : 'Workflow error'
    workflowStore.setError(sessionId, message)
    workflowStore.setViewState(sessionId, 'error')
    workflowStore.setRunPhase(sessionId, createGenericErrorPhase(message))
    return 'handled'
  }

  return 'handled'
}

function handleWorkflowToken(sessionId: string, event: AgentEvent) {
  const data = (event.data || {}) as Record<string, unknown>
  if (data.source !== 'workflow' || typeof data.content !== 'string') {
    return
  }

  const workflowStore = useWorkflowSessionsStore.getState()
  if (isDashboardProgressMessage(data.content)) {
    const stage = getDashboardProgressStage(data.content)
    workflowStore.setDashboardProgressVisible(sessionId, true)
    workflowStore.appendDashboardProgressLog(sessionId, data.content)
    openOrFocusPluginTabIfCurrent(sessionId, 'dashboard')
    if (stage !== null) {
      workflowStore.setDashboardProgressStage(sessionId, stage)
    }
  }

  const phase = createTokenPhase(data.content)
  if (phase) {
    workflowStore.setRunPhase(sessionId, phase)
  }

  workflowStore.appendVideoProgressLog(sessionId, data.content)
  const taskIdMatch = data.content.match(/Task ID:\s*(\d{8}_\d{6})/i)
  if (taskIdMatch) {
    openOrFocusPluginTabIfCurrent(sessionId, 'video-preview', { taskId: taskIdMatch[1] })
  }

  const videoStep = parseVideoProgressStep(data.content)
  if (videoStep !== null) {
    workflowStore.setVideoProgressVisible(sessionId, true)
    openOrFocusPluginTabIfCurrent(sessionId, 'video-preview')
    workflowStore.setVideoProgressStep(sessionId, videoStep)
  }

  if (/Step\s*4\s*\/\s*4\s*Done|Video generation completed|🎉/.test(data.content)) {
    workflowStore.setVideoProgressPercent(sessionId, 100)
  }
}

function handleSessionEvent(sessionId: string, agentEvent: AgentEvent) {
  useWorkflowSessionsStore.getState().ensureSession(sessionId)

  if (agentEvent.type === 'sandbox_started') {
    if (isCurrentSession(sessionId)) {
      const chatStore = useChatStore.getState()
      chatStore.setSandboxReady(sessionId)
      openOrFocusTabIfCurrent(sessionId, 'files')
    }
    return
  }

  if (agentEvent.type === 'sandbox_files_changed') {
    if (isCurrentSession(sessionId)) {
      useChatStore.getState().notifyFilesChanged()
    }
    return
  }

  if (agentEvent.type === 'workflow_event') {
    handleWorkflowEvent(sessionId, agentEvent)
    return
  }

  if (agentEvent.type === 'tool_end') {
    const name = typeof agentEvent.data?.name === 'string' ? agentEvent.data.name : ''
    if (name === 'create_workflow') {
      openOrFocusTabIfCurrent(sessionId, 'workflow')
    }
  }

  if (agentEvent.type === 'token') {
    handleWorkflowToken(sessionId, agentEvent)
  }

  const tokenSource =
    typeof agentEvent.data?.source === 'string'
      ? agentEvent.data.source
      : typeof agentEvent.source === 'string'
        ? agentEvent.source
        : ''
  if (agentEvent.type === 'token' && tokenSource === 'workflow') {
    return
  }

  pushChatEventIfCurrent(sessionId, agentEvent)

  if (agentEvent.type === 'agent_end') {
    stopStreamingIfCurrent(sessionId)
    emitError(null)
    return
  }

  if (agentEvent.type === 'error') {
    if (useWorkflowSessionsStore.getState().sessions[sessionId]?.runStatus === 'running') {
      useWorkflowSessionsStore
        .getState()
        .setRunPhase(sessionId, createGenericErrorPhase(agentEvent.content || 'Unknown error'))
    }
    stopStreamingIfCurrent(sessionId)
    emitError(agentEvent.content || 'Unknown error')
    disconnectSessionEventStream({ clearError: false })
  }
}

function closeCurrentStream() {
  if (currentEventSource) {
    currentEventSource.close()
  }
  currentEventSource = null
  currentSessionId = null
}

export function subscribeSessionEventStreamError(listener: ErrorListener) {
  errorListeners.add(listener)
  listener(currentError)
  return () => {
    errorListeners.delete(listener)
  }
}

export function getConnectedSessionEventStreamSessionId() {
  return currentSessionId
}

export function disconnectSessionEventStream(options?: { clearError?: boolean }) {
  closeCurrentStream()
  if (options?.clearError !== false) {
    emitError(null)
  }
}

export function ensureSessionEventStream(sessionId: string) {
  if (
    currentEventSource &&
    currentSessionId === sessionId &&
    currentEventSource.readyState !== EventSource.CLOSED
  ) {
    return currentEventSource
  }

  disconnectSessionEventStream()
  emitError(null)

  const eventSource = chatApi.createEventSource(sessionId)
  currentEventSource = eventSource
  currentSessionId = sessionId

  eventSource.onmessage = (event) => {
    if (currentEventSource !== eventSource || currentSessionId !== sessionId) {
      return
    }

    try {
      const agentEvent = JSON.parse(event.data) as AgentEvent
      handleSessionEvent(sessionId, agentEvent)
    } catch (error) {
      console.error('Session event stream parse error', error)
    }
  }

  eventSource.onerror = () => {
    if (currentEventSource !== eventSource || currentSessionId !== sessionId) {
      return
    }

    closeCurrentStream()
    if (isCurrentSession(sessionId)) {
      stopStreamingIfCurrent(sessionId)
    }
    if (useWorkflowSessionsStore.getState().sessions[sessionId]?.runStatus === 'running') {
      useWorkflowSessionsStore.getState().setError(sessionId, 'Connection lost')
      useWorkflowSessionsStore.getState().setRunPhase(sessionId, createConnectionLostPhase())
    }
    emitError('Connection lost')
  }

  return eventSource
}
