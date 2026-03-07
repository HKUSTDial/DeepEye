import { useState, useRef, useEffect } from 'react'
import { useChatStore } from '../stores/chat'
import { useRightPanelStore } from '../stores/rightPanel'
import { useReportStore } from '../stores/report'
import { useWorkflowSessionsStore } from '../stores/workflowSessions'
import { chatApi, datasourceApi, type AgentEvent } from '../api'
import { extractVideoOutputParams } from '../api/video'
import type { WorkflowRun } from '../types'

/**
 * Chat hook - handles SSE connection and message sending.
 * All events flow through store.pushEvent() which uses the same
 * reduceEvents() pure function as history replay.
 */
export function useChat() {
  // 每个属性单独订阅 - 最简单可靠的方式
  const currentSession = useChatStore((state) => state.currentSession)
  const sessionId = useChatStore((state) => state.sessionId)
  const messages = useChatStore((state) => state.messages)
  const createSession = useChatStore((state) => state.createSession)
  const startStreaming = useChatStore((state) => state.startStreaming)
  const stopStreaming = useChatStore((state) => state.stopStreaming)
  const addUserMessage = useChatStore((state) => state.addUserMessage)
  const pushEvent = useChatStore((state) => state.pushEvent)
  const updateSessionTitle = useChatStore((state) => state.updateSessionTitle)
  const fetchSessions = useChatStore((state) => state.fetchSessions)
  const setSandboxReady = useChatStore((state) => state.setSandboxReady)
  const notifyFilesChanged = useChatStore((state) => state.notifyFilesChanged)
  const openOrFocusTab = useRightPanelStore((state) => state.openOrFocusTab)
  const setRightPanelRatio = useRightPanelStore((state) => state.setPanelRatio)
  const ensureWorkflowSession = useWorkflowSessionsStore((state) => state.ensureSession)
  const setWorkflowError = useWorkflowSessionsStore((state) => state.setError)
  const addWorkflowNode = useWorkflowSessionsStore((state) => state.addDraftNode)
  const addWorkflowEdge = useWorkflowSessionsStore((state) => state.addDraftEdge)
  const clearWorkflow = useWorkflowSessionsStore((state) => state.clearDraft)
  const clearValidated = useWorkflowSessionsStore((state) => state.clearValidated)
  const setWorkflowDefinition = useWorkflowSessionsStore((state) => state.setDefinition)
  const setNodeStatus = useWorkflowSessionsStore((state) => state.setNodeStatus)
  const setRunStatus = useWorkflowSessionsStore((state) => state.setRunStatus)
  const setActiveWorkflowFile = useWorkflowSessionsStore((state) => state.setActiveFilePath)
  const setActiveRun = useWorkflowSessionsStore((state) => state.setActiveRun)
  const setRunOutput = useWorkflowSessionsStore((state) => state.setRunOutput)
  const setVideoPreviewUrl = useWorkflowSessionsStore((state) => state.setVideoPreviewUrl)
  const triggerDashboardRefresh = useWorkflowSessionsStore((state) => state.triggerDashboardRefresh)
  const setViewState = useWorkflowSessionsStore((state) => state.setViewState)
  const setReportResult = useReportStore((state) => state.setReportResult)
  const addReportStep = useReportStore((state) => state.addReportStep)
  const startReportGeneration = useReportStore((state) => state.startGeneration)
  const stopReportGeneration = useReportStore((state) => state.stopGeneration)

  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)
  const closedNormallyRef = useRef(false)

  const buildWorkflowRunFromEvent = (
    sessionId: string,
    data: Record<string, unknown> | undefined,
    status: string,
    error: string | null = null,
  ): WorkflowRun => ({
    id: typeof data?.run_id === 'string' ? data.run_id : `workflow-event:${sessionId}`,
    workflow_id: null,
    session_id: sessionId,
    turn_id: typeof data?.turn_id === 'string' ? data.turn_id : null,
    draft_id: typeof data?.draft_id === 'string' ? data.draft_id : null,
    source: 'chat_workflow',
    file_path: typeof data?.file_path === 'string' ? data.file_path : null,
    status,
    error: error || undefined,
    created_at: new Date().toISOString(),
    finished_at: status === 'running' ? null : new Date().toISOString(),
  })

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [])

  const handleWorkflowArtifactEvent = (
    sessionId: string,
    phase: string,
    payload: Record<string, unknown>,
  ) => {
    const artifact = typeof payload.artifact === 'object' && payload.artifact
      ? (payload.artifact as Record<string, unknown>)
      : null
    const kind = typeof artifact?.kind === 'string' ? artifact.kind : ''

    if (!kind) {
      return false
    }

    if (kind === 'report') {
      if (phase === 'artifact_progress') {
        const stepContent = typeof payload.message === 'string' ? payload.message : ''
        if (stepContent) {
          const currentlyGenerating = !!useReportStore.getState().sessions[sessionId]?.isGenerating
          if (!currentlyGenerating) {
            startReportGeneration(sessionId)
            openOrFocusTab('report')
            setRightPanelRatio(28)
          }
          addReportStep(sessionId, stepContent)
        }
        return true
      }

      if (phase === 'artifact_ready' || phase === 'artifact_failed') {
        const steps = Array.isArray(payload.steps)
          ? payload.steps.filter((item): item is string => typeof item === 'string')
          : []
        const reportHtml =
          typeof payload.report_html === 'string'
            ? payload.report_html
            : typeof artifact?.report_html === 'string'
              ? artifact.report_html
              : null
        const reportFilename =
          typeof payload.report_filename === 'string'
            ? payload.report_filename
            : typeof artifact?.report_filename === 'string'
              ? artifact.report_filename
              : null
        const error =
          typeof payload.error === 'string'
            ? payload.error
            : phase === 'artifact_failed'
              ? 'Report generation failed'
              : null
        setReportResult(sessionId, reportHtml, steps, reportFilename, error)
        openOrFocusTab('report')
        setRightPanelRatio(28)
        stopReportGeneration(sessionId)
        return true
      }
    }

    if (kind === 'dashboard') {
      if (phase === 'artifact_ready') {
        openOrFocusTab('dashboard')
        return true
      }
      if (phase === 'artifact_refresh') {
        triggerDashboardRefresh(sessionId)
        openOrFocusTab('dashboard')
        return true
      }
    }

    if (kind === 'video') {
      const taskId = typeof artifact?.task_id === 'string' ? artifact.task_id : null
      const videoUrl = typeof artifact?.video_url === 'string' ? artifact.video_url : null
      if (videoUrl) {
        setVideoPreviewUrl(sessionId, videoUrl)
      }
      if (phase === 'artifact_ready') {
        openOrFocusTab('video-preview', taskId ? { taskId } : {})
        return true
      }
    }

    return false
  }

  const connectToSSE = (sessionId: string) => {
    closedNormallyRef.current = false
    if (esRef.current) {
      esRef.current.close()
    }

    const es = chatApi.createEventSource(sessionId)
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const agentEvent: AgentEvent = JSON.parse(event.data)
        ensureWorkflowSession(sessionId)
        
        // Handle sandbox events
        if (agentEvent.type === 'sandbox_started') {
          setSandboxReady(sessionId)
          openOrFocusTab('files')
          return
        }
        if (agentEvent.type === 'sandbox_files_changed') {
          notifyFilesChanged()
          return
        }

        if (agentEvent.type === 'workflow_event') {
          const data = agentEvent.data as Record<string, unknown> | undefined
          const filePath = typeof data?.file_path === 'string' ? data?.file_path : null
          const phase = typeof data?.phase === 'string' ? data?.phase : ''
          const payload = (data?.payload as Record<string, unknown>) || {}

          if (handleWorkflowArtifactEvent(sessionId, phase, payload)) {
            pushEvent(agentEvent)
            return
          }

          const activeWorkflowFile = useWorkflowSessionsStore.getState().sessions[sessionId]?.activeFilePath
          if (filePath && activeWorkflowFile && activeWorkflowFile !== filePath) {
            clearWorkflow(sessionId)
            clearValidated(sessionId)
            setActiveWorkflowFile(sessionId, filePath)
            setViewState(sessionId, 'switching')
          }
          if (phase === 'create_file') {
            clearWorkflow(sessionId)
            clearValidated(sessionId)
            setActiveWorkflowFile(sessionId, filePath)
            setViewState(sessionId, 'switching')
            notifyFilesChanged()
            openOrFocusTab('workflow')
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
              const stepDelayMs = 200

              // Clear draft and validated graph
              clearWorkflow(sessionId)
              clearValidated(sessionId)
              setActiveWorkflowFile(sessionId, filePath)
              setWorkflowDefinition(sessionId, workflow as Record<string, unknown>)
              setViewState(sessionId, 'switching')
              setWorkflowError(sessionId, null)
              notifyFilesChanged()
              openOrFocusTab('workflow')

              // Add nodes and edges with animation
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
          if (phase === 'node') {
            const node = payload?.node
            if (node && typeof node === 'object') {
              addWorkflowNode(sessionId, node as Record<string, unknown>)
              setWorkflowError(sessionId, null)
              openOrFocusTab('workflow')
            }
            return
          }
          if (phase === 'edge') {
            const edge = payload?.edge
            if (edge && typeof edge === 'object') {
              addWorkflowEdge(sessionId, edge as Record<string, unknown>)
              setWorkflowError(sessionId, null)
              openOrFocusTab('workflow')
            }
            return
          }
          if (phase === 'run_start') {
            setRunStatus(sessionId, 'running', null)
            setViewState(sessionId, 'ready')
            setActiveRun(sessionId, buildWorkflowRunFromEvent(sessionId, data, 'running'))
            return
          }
          if (phase === 'node_status') {
            const nodeId = typeof payload?.node_id === 'string' ? payload?.node_id : ''
            const status = typeof payload?.status === 'string' ? payload?.status : ''
            const outputs = typeof payload?.outputs === 'object' ? payload?.outputs : undefined
            if (nodeId && status) {
              const typedOutputs = outputs as Record<string, unknown> | undefined
              setNodeStatus(sessionId, nodeId, status, typedOutputs)
              if (typedOutputs?.dashboard_url) {
                openOrFocusTab('dashboard')
              }
            }
            return
          }
          if (phase === 'run_end') {
            const status = typeof payload?.status === 'string' ? payload?.status : 'failed'
            const error = typeof payload?.error === 'string' ? payload?.error : null
            useWorkflowSessionsStore.getState().setVideoProgressVisible(sessionId, false)

            setRunStatus(sessionId, status, error)
            setActiveRun(sessionId, buildWorkflowRunFromEvent(sessionId, data, status, error))

            const artifacts = Array.isArray(payload?.artifacts)
              ? payload.artifacts.filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
              : []
            artifacts.forEach((artifact) => {
              handleWorkflowArtifactEvent(sessionId, 'artifact_ready', { artifact })
            })

            if (payload?.outputs && typeof payload.outputs === 'object') {
              setRunOutput(sessionId, JSON.stringify(payload.outputs, null, 2))
              const videoParams = extractVideoOutputParams(payload.outputs as Record<string, unknown>)
              const taskIdToOpen = videoParams.taskId ?? null
              if (taskIdToOpen) {
                openOrFocusTab('video-preview', { taskId: taskIdToOpen })
              } else {
                const lastMessage = messages[messages.length - 1]
                if (lastMessage?.role === 'assistant' && lastMessage.content) {
                  const taskIdMatch = String(lastMessage.content).match(/Task ID:\s*(\d{8}_\d{6})/i)
                  if (taskIdMatch) {
                    const extractedTaskId = taskIdMatch[1]
                    const currentRunOutput = useWorkflowSessionsStore.getState().sessions[sessionId]?.runOutput || ''
                    setRunOutput(sessionId, currentRunOutput + `\nTask ID: ${extractedTaskId}`)
                    openOrFocusTab('video-preview', { taskId: extractedTaskId })
                  }
                }
              }
            }
            return
          }
          if (phase === 'error') {
            const message = typeof payload?.message === 'string' ? payload.message : 'Workflow error'
            setWorkflowError(sessionId, message)
            setViewState(sessionId, 'error')
            return
          }
          if (phase === 'video_preview_ready') {
            const videoUrl = typeof payload?.video_url === 'string' ? payload.video_url : null
            if (videoUrl) {
              setVideoPreviewUrl(sessionId, videoUrl)
              openOrFocusTab('video-preview', {})
            }
            return
          }
          if (phase === 'refresh') {
            triggerDashboardRefresh(sessionId)
            return
          }
        }

        if (agentEvent.type === 'tool_end') {
          const name = typeof agentEvent.data?.name === 'string' ? agentEvent.data.name : ''
          if (name === 'create_workflow') {
            openOrFocusTab('workflow')
          }
        }

        // Legacy fallback for report runtime before unified artifact events.
        if (agentEvent.type === 'report_step') {
          const stepContent = agentEvent.content ?? ''
          if (stepContent) {
            // Read latest store state here to avoid stale closure resetting progress steps.
            const currentlyGenerating = !!useReportStore.getState().sessions[sessionId]?.isGenerating
            if (!currentlyGenerating) {
              startReportGeneration(sessionId)
              openOrFocusTab('report')
              setRightPanelRatio(28)
            }
            addReportStep(sessionId, stepContent)
          }
        }

        if (agentEvent.type === 'agent_start' && agentEvent.source === 'report') {
          startReportGeneration(sessionId)
          openOrFocusTab('report')
          setRightPanelRatio(28)
        }

        if (agentEvent.type === 'agent_end' && agentEvent.source === 'report') {
          stopReportGeneration(sessionId)
        }

        if (agentEvent.type === 'report_done') {
          const data = agentEvent.data as { report_html?: string; steps?: string[]; report_filename?: string; error?: string } | undefined
          setReportResult(sessionId, data?.report_html ?? null, data?.steps ?? [], data?.report_filename ?? null, data?.error ?? null)
          // Open the Report panel and enlarge the right panel for better reading
          openOrFocusTab('report')
          setRightPanelRatio(28)
        }

        if (agentEvent.type === 'token') {
          const data = (agentEvent.data || {}) as Record<string, unknown>
          if (data.source === 'workflow' && typeof data.content === 'string') {
            const store = useWorkflowSessionsStore.getState()
            store.appendVideoProgressLog(sessionId, data.content)
            // task_id 后端在 Step 2 开始时就生成并推送，一收到就打开预览并传入，无需等 run_end
            const taskIdMatch = data.content.match(/Task ID:\s*(\d{8}_\d{6})/i)
            if (taskIdMatch) {
              openOrFocusTab('video-preview', { taskId: taskIdMatch[1] })
            }
            const stepMatch = data.content.match(/Step\s*(\d)\s*\/\s*4/)
            if (stepMatch?.[1]) {
              store.setVideoProgressVisible(sessionId, true)
              const stepIndex = parseInt(stepMatch[1], 10) - 1
              if (stepIndex >= 0 && stepIndex <= 3) store.setVideoProgressStep(sessionId, stepIndex)
            }
            // 仅在完成时把进度设为 100%，避免 Step 4 一开始就显示 100%
            if (/Step\s*4\s*\/\s*4\s*Done|Video generation completed|🎉/.test(data.content)) {
              store.setVideoProgressPercent(sessionId, 100)
            }
          }
        }

        pushEvent(agentEvent)

        if (agentEvent.type === 'agent_end' || agentEvent.type === 'error') {
          closedNormallyRef.current = agentEvent.type === 'agent_end'
          es.close()
          esRef.current = null
          stopStreaming()
          if (agentEvent.type === 'agent_end') {
            setError(null)
          } else {
            setError(agentEvent.content || 'Unknown error')
          }
        }
      } catch (e) {
        console.error('SSE parse error', e)
      }
    }

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return
      if (closedNormallyRef.current) {
        closedNormallyRef.current = false
        es.close()
        esRef.current = null
        stopStreaming()
        return
      }
      es.close()
      esRef.current = null
      stopStreaming()
      setError('Connection lost')
    }
  }

  const sendMessage = async (text: string, _datasourceIds?: string[], kbIds?: string[], csvFiles?: File[]) => {
    if (!text.trim() && (!csvFiles || csvFiles.length === 0)) return

    setError(null)

    // Ensure we have a session (create if needed)
    let session_id = sessionId
    if (!currentSession || currentSession.isDraft || !session_id) {
      const created = await createSession()
      if (!created) {
        setError('Failed to create session')
        return
      }
      session_id = created.id
    }

    const isFirstMessage = messages.length === 0
    const query = text.trim() || 'Generate a comprehensive report.'
    startStreaming()
    addUserMessage(query)

    try {
      if (csvFiles && csvFiles.length > 0) {
        for (const file of csvFiles) {
          await datasourceApi.upload(file, session_id)
        }
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('datasources:updated'))
        }
      }

      connectToSSE(session_id)
      await chatApi.start({
        message: query,
        session_id: session_id,
        kb_ids: kbIds && kbIds.length > 0 ? kbIds : undefined,
      })

      if (isFirstMessage) {
        const title = query.length > 50 ? query.substring(0, 47) + '...' : query
        await updateSessionTitle(session_id, title)
      }

      fetchSessions()
    } catch (e: unknown) {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
      setError(e instanceof Error ? e.message : 'Failed to send')
      stopStreaming()
    }
  }

  const stopMessage = () => {
    closedNormallyRef.current = true
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    stopStreaming()
    setError(null)
  }

  return { sendMessage, stopMessage, error }
}
