import { useState, useCallback, useRef, useEffect } from 'react'
import { useChatStore } from '../stores/chat'
import { useRightPanelStore } from '../stores/rightPanel'
import { useWorkflowSessionsStore } from '../stores/workflowSessions'
import { chatApi, type AgentEvent } from '../api'

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
  const setViewState = useWorkflowSessionsStore((state) => state.setViewState)
  const isStreaming = useChatStore((state) => state.isStreaming)
  
  const [error, setError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [])

  const connectToSSE = useCallback((sessionId: string) => {
    // Close existing connection
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
            setActiveRun(sessionId, {
              id: `file:${filePath || ''}`,
              workflow_id: `file:${filePath || ''}`,
              status: 'running',
              created_at: new Date().toISOString(),
              finished_at: null,
            })
            openOrFocusTab('workflow')
            return
          }
          if (phase === 'node_status') {
            const nodeId = typeof payload?.node_id === 'string' ? payload?.node_id : ''
            const status = typeof payload?.status === 'string' ? payload?.status : ''
            const outputs = typeof payload?.outputs === 'object' ? payload?.outputs : undefined
            if (nodeId && status) {
              setNodeStatus(sessionId, nodeId, status, outputs as Record<string, unknown> | undefined)
            }
            return
          }
          if (phase === 'run_end') {
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
            }
            return
          }
          if (phase === 'error') {
            const message = typeof payload?.message === 'string' ? payload.message : 'Workflow error'
            setWorkflowError(sessionId, message)
            setViewState(sessionId, 'error')
            return
          }
        }

        if (agentEvent.type === 'tool_end') {
          const name = typeof agentEvent.data?.name === 'string' ? agentEvent.data.name : ''
          if (name === 'create_workflow') {
            openOrFocusTab('workflow')
          }
        }

        pushEvent(agentEvent)

        if (agentEvent.type === 'agent_end' || agentEvent.type === 'error') {
          es.close()
          esRef.current = null
          stopStreaming()
          if (agentEvent.type === 'error') {
            setError(agentEvent.content || 'Unknown error')
          }
        }
      } catch (e) {
        console.error('SSE parse error', e)
      }
    }

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) return
      es.close()
      esRef.current = null
      stopStreaming()
      setError('Connection lost')
    }
  }, [
    setSandboxReady,
    notifyFilesChanged,
    openOrFocusTab,
    setWorkflowError,
    addWorkflowNode,
    addWorkflowEdge,
    clearWorkflow,
    clearValidated,
    setWorkflowDefinition,
    setNodeStatus,
    setRunStatus,
    setActiveRun,
    setRunOutput,
    setViewState,
    pushEvent,
    stopStreaming,
  ])

  const sendMessage = useCallback(async (text: string, datasourceIds?: string[], kbIds?: string[]) => {
    if (!text.trim()) return

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
    
    // Check if this is the first message (for title update)
    const isFirstMessage = messages.length === 0
    
    startStreaming()
    addUserMessage(text)

    try {
      // Send message with session_id from backend
      await chatApi.start({
        message: text,
        session_id: session_id,
        datasource_ids: datasourceIds,
        kb_ids: kbIds && kbIds.length > 0 ? kbIds : undefined,
      })

      // Update session title with first message content
      if (isFirstMessage) {
        const title = text.length > 50 ? text.substring(0, 47) + '...' : text
        await updateSessionTitle(session_id, title)
      }

      fetchSessions()
      connectToSSE(session_id)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to send')
      stopStreaming()
    }
  }, [currentSession, sessionId, messages.length, createSession, startStreaming, addUserMessage, updateSessionTitle, fetchSessions, stopStreaming, connectToSSE])

  return { sendMessage, error }
}
