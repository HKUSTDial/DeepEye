import { useEffect, useState } from 'react'
import { datasourceApi, chatApi } from '../api'
import {
  selectCurrentMessages,
  selectCurrentSessionId,
  useChatStore,
} from '../stores/chat'
import { useDatasourceSyncStore } from '../stores/datasourceSync'
import {
  disconnectSessionEventStream,
  ensureSessionEventStream,
  getConnectedSessionEventStreamSessionId,
  subscribeSessionEventStreamError,
} from '../services/sessionEventStream'

/**
 * Chat hook - handles message sending and session-scoped SSE subscription.
 */
export function useChat() {
  const currentSession = useChatStore((state) => state.currentSession)
  const sessionId = useChatStore(selectCurrentSessionId)
  const messages = useChatStore(selectCurrentMessages)
  const createSession = useChatStore((state) => state.createSession)
  const startStreaming = useChatStore((state) => state.startStreaming)
  const stopStreaming = useChatStore((state) => state.stopStreaming)
  const addUserMessage = useChatStore((state) => state.addUserMessage)
  const updateSessionTitle = useChatStore((state) => state.updateSessionTitle)
  const fetchSessions = useChatStore((state) => state.fetchSessions)
  const notifyDatasourceUpdated = useDatasourceSyncStore((state) => state.notifyUpdated)

  const [requestError, setRequestError] = useState<string | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)

  useEffect(() => subscribeSessionEventStreamError(setStreamError), [])

  useEffect(() => {
    const connectedSessionId = getConnectedSessionEventStreamSessionId()
    if (!connectedSessionId) {
      return
    }
    if (!sessionId || sessionId === 'draft' || connectedSessionId !== sessionId) {
      disconnectSessionEventStream()
    }
  }, [sessionId])

  useEffect(() => {
    return () => {
      disconnectSessionEventStream()
    }
  }, [])

  const sendMessage = async (text: string, _datasourceIds?: string[], csvFiles?: File[]) => {
    if (!text.trim() && (!csvFiles || csvFiles.length === 0)) return

    setRequestError(null)

    let targetSessionId = sessionId
    if (!currentSession || currentSession.isDraft || !targetSessionId) {
      const created = await createSession()
      if (!created) {
        setRequestError('Failed to create session')
        return
      }
      targetSessionId = created.id
    }

    const isFirstMessage = messages.length === 0
    const query = text.trim() || 'Generate a comprehensive report.'
    startStreaming()
    addUserMessage(query)

    try {
      if (csvFiles && csvFiles.length > 0) {
        for (const file of csvFiles) {
          await datasourceApi.upload(file, targetSessionId)
        }
        notifyDatasourceUpdated()
      }

      ensureSessionEventStream(targetSessionId)
      await chatApi.start({
        message: query,
        session_id: targetSessionId,
      })

      if (isFirstMessage) {
        const title = query.length > 50 ? `${query.substring(0, 47)}...` : query
        await updateSessionTitle(targetSessionId, title)
      }

      void fetchSessions()
    } catch (error: unknown) {
      disconnectSessionEventStream({ clearError: false })
      stopStreaming()
      setRequestError(error instanceof Error ? error.message : 'Failed to send')
    }
  }

  const stopMessage = () => {
    disconnectSessionEventStream()
    stopStreaming()
    setRequestError(null)
  }

  return { sendMessage, stopMessage, error: requestError ?? streamError }
}
