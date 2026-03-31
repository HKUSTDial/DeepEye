import { useState, useRef, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useChat } from '../hooks/useChat'
import {
  selectCurrentMessages,
  selectCurrentSessionId,
  selectIsStreaming,
  useChatStore,
} from '../stores/chat'
import { useWorkflowSessionsStore } from '../stores/workflowSessions'
import { type ChatProgressLine } from '../utils/chatProgress'
import DataSourceManager from './DataSourceManager'
import { AssistantMessageBody } from './AssistantMessageBody'
import { ChatEmptyState } from './ChatEmptyState'
import { buildMessageActivityKey, hasText } from './chatBoxUtils'
import { WorkflowRunPhaseBanner } from './workflow/WorkflowRunPhaseBanner'
import './ChatBox.css'

interface ChatBoxProps {
  dataSourceIds: string[]
  onDataSourceIdsChange?: (ids: string[]) => void
  compact?: boolean
}

export default function ChatBox({
  dataSourceIds,
  onDataSourceIdsChange,
  compact = false,
}: ChatBoxProps) {
  const { sendMessage, stopMessage, error } = useChat()
  // 每个属性单独订阅 - 最简单可靠的方式
  const messages = useChatStore(selectCurrentMessages)
  const currentSessionId = useChatStore(selectCurrentSessionId)
  const isStreaming = useChatStore(selectIsStreaming)
  const runPhase = useWorkflowSessionsStore((state) =>
    currentSessionId ? state.sessions[currentSessionId]?.runPhase ?? null : null,
  )
  const runStatus = useWorkflowSessionsStore((state) =>
    currentSessionId ? state.sessions[currentSessionId]?.runStatus ?? null : null,
  )
  
  const [input, setInput] = useState('')
  const [showDataSourceManager, setShowDataSourceManager] = useState(false)
  const [isNearBottom, setIsNearBottom] = useState(true)
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composingRef = useRef(false)
  const compositionEndedAtRef = useRef(0)
  const starterPrompts = [
    {
      label: 'Profile the data',
      description: 'Check fields, structure, data quality, and immediate issues.',
      prompt: 'Please analyze my attached data sources, highlight key fields, data quality issues, and the most practical next steps.',
    },
    {
      label: 'Recommend charts',
      description: 'Suggest the highest-signal visuals and what each one answers.',
      prompt: 'Recommend three high-value visualizations for this dataset and explain what business questions each chart answers.',
    },
    {
      label: 'Outline a report',
      description: 'Draft a concise report with findings, risks, and actions.',
      prompt: 'Generate a business report draft with summary, key findings, risks, and actionable recommendations.',
    },
  ]

  useEffect(() => {
    if (!showDataSourceManager) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowDataSourceManager(false)
      }
    }

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [showDataSourceManager])

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [])

  useEffect(() => {
    resizeTextarea()
  }, [input, resizeTextarea])

  const handleSend = () => {
    const canSend = Boolean(input.trim()) && !isStreaming
    if (!canSend) return
    const query = input.trim()
    sendMessage(query, dataSourceIds)
    setInput('')
    setIsNearBottom(true)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    scrollToBottom()
  }

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    setTimeout(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTo({
          top: chatContainerRef.current.scrollHeight,
          behavior,
        })
      }
    }, 0)
  }
  const lastMessageActivityKey =
    messages.length > 0 ? buildMessageActivityKey(messages[messages.length - 1]) : ''

  useEffect(() => {
    const container = chatContainerRef.current
    if (!container) return
    const threshold = 96
    const updateScrollState = () => {
      const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight
      const nearBottom = distanceToBottom <= threshold
      setIsNearBottom(nearBottom)
    }
    updateScrollState()
    container.addEventListener('scroll', updateScrollState)
    return () => container.removeEventListener('scroll', updateScrollState)
  }, [])

  // Auto-scroll when messages change
  useEffect(() => {
    if (messages.length === 0) return
    if (isNearBottom) {
      scrollToBottom('smooth')
    }
  }, [messages.length, lastMessageActivityKey, isNearBottom])

  const handleCompositionStart = () => {
    composingRef.current = true
  }

  const handleCompositionEnd = (e: React.CompositionEvent<HTMLTextAreaElement>) => {
    composingRef.current = false
    compositionEndedAtRef.current = e.timeStamp
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const native = e.nativeEvent
    const keyCode = native.keyCode || native.which || 0
    const composingOrSelecting =
      composingRef.current ||
      native.isComposing ||
      keyCode === 229 ||
      native.timeStamp - compositionEndedAtRef.current < 30

    if (e.key === 'Enter' && !e.shiftKey) {
      // IME composing state: do not send message on Enter while user is selecting candidates.
      if (composingOrSelecting) {
        return
      }
      e.preventDefault()
      handleSend()
    }
  }

  const applyStarterPrompt = (prompt: string) => {
    setInput(prompt)
    requestAnimationFrame(() => {
      if (!textareaRef.current) return
      textareaRef.current.focus()
      const caret = prompt.length
      textareaRef.current.setSelectionRange(caret, caret)
      resizeTextarea()
    })
  }

  const copyMessageContent = async (content: string, index: number) => {
    if (!content.trim()) return
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessageIndex(index)
      window.setTimeout(() => {
        setCopiedMessageIndex((current) => (current === index ? null : current))
      }, 1400)
    } catch {
      setCopiedMessageIndex(null)
    }
  }

  const renderStreamingIndicator = () => (
    <span className="streaming-indicator" aria-hidden="true">
      <span className="streaming-indicator-dot"></span>
      <span className="streaming-indicator-dot"></span>
      <span className="streaming-indicator-dot"></span>
    </span>
  )
  const renderProgressLine = (progress: ChatProgressLine, key: string) => (
    <div key={key} className={`chat-progress-line chat-progress-line--${progress.tone} chat-progress-line--${progress.status}`}>
      <span className="chat-progress-badge">{progress.badge}</span>
      <span className="chat-progress-copy">
        <span className="chat-progress-label">{progress.label}</span>
        {progress.detail ? <span className="chat-progress-detail">{progress.detail}</span> : null}
      </span>
      <span className={`chat-progress-state chat-progress-state--${progress.status}`}>{progress.status}</span>
    </div>
  )
  const showJumpButton = messages.length > 0 && !isNearBottom
  const showRunPhaseBanner = !!runPhase && (runPhase.status === 'running' || runPhase.status === 'error' || runStatus === 'running')
  const sourceStatusText = dataSourceIds.length > 0
    ? `${dataSourceIds.length} attached data source${dataSourceIds.length > 1 ? 's' : ''}`
    : 'No attached data yet'
  const composerHelperText = dataSourceIds.length > 0
    ? 'All attached data is used automatically.'
    : 'Attach a file or connect a database from Attached data.'
  const emptyTitle = dataSourceIds.length > 0 ? 'Ask about the workspace' : 'Attach data to begin'
  const emptySubtitle = dataSourceIds.length > 0
    ? 'Use the assistant to inspect attached data, explain outputs, write SQL, or draft next steps.'
    : 'Use + to add files or databases. Once attached, they are available automatically in this thread.'

  return (
    <div className={`chat-container ${compact ? 'compact' : ''}`}>
      {/* Messages Area */}
      <div ref={chatContainerRef} className="chat-messages">
        {showRunPhaseBanner && runPhase ? (
          <div className={`mx-auto mb-4 ${messages.length === 0 ? 'w-full max-w-[760px]' : 'w-full max-w-[960px]'}`}>
            <WorkflowRunPhaseBanner phase={runPhase} compact={compact} />
          </div>
        ) : null}
        {/* Empty State */}
        {messages.length === 0 && (
          <ChatEmptyState
            dataSourceCount={dataSourceIds.length}
            emptyTitle={emptyTitle}
            emptySubtitle={emptySubtitle}
            sourceStatusText={sourceStatusText}
            starterPrompts={starterPrompts}
            onApplyStarterPrompt={applyStarterPrompt}
          />
        )}

        {/* Messages */}
        {messages.length > 0 && (
          <div className="chat-thread">
            {messages.map((msg, index) => (
              <div key={`msg-${index}`} className={`chat-message-row ${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div className="message-avatar assistant" aria-hidden="true">
                    AI
                  </div>
                )}

                <div className="chat-message-main">
                  <div className={`message-bubble ${msg.role}`}>
                    {msg.role === 'user' ? (
                      <div className="message-content">
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    ) : (
                      <AssistantMessageBody
                        message={msg}
                        renderProgressLine={renderProgressLine}
                        renderStreamingIndicator={renderStreamingIndicator}
                      />
                    )}

                    {/* Thinking indicator */}
                    {msg.role === 'assistant' &&
                      msg.isStreaming &&
                      !hasText(msg.content) &&
                      (!msg.steps || msg.steps.length === 0) && (
                        <div className="thinking-dots">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      )}
                  </div>
                  {msg.role === 'assistant' && hasText(msg.content) && !msg.isStreaming && (
                    <div className="message-actions">
                      <button
                        type="button"
                        className="message-action-btn"
                        onClick={() => copyMessageContent(msg.content, index)}
                      >
                        {copiedMessageIndex === index ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="message-avatar user" aria-hidden="true">
                    You
                  </div>
                )}
              </div>
            ))}

            {/* Error */}
            {error && (
              <div className="chat-error">
                {error}
              </div>
            )}
          </div>
        )}
      </div>
      {showJumpButton && (
        <button
          type="button"
          className="chat-jump-latest-btn"
          onClick={() => {
            setIsNearBottom(true)
            scrollToBottom('smooth')
          }}
        >
          Jump to latest
        </button>
      )}

      {/* Input Area */}
      <div className="chat-input-container">
        <div className="chat-input-shell">
          <div className="chat-input-wrapper">
            <button
              type="button"
              className={`chat-upload-btn ${showDataSourceManager ? 'is-active' : ''}`}
              onClick={() => setShowDataSourceManager((current) => !current)}
              title={dataSourceIds.length > 0 ? `${dataSourceIds.length} attached data source${dataSourceIds.length > 1 ? 's' : ''}` : 'Attach data'}
              aria-label={dataSourceIds.length > 0 ? `Manage ${dataSourceIds.length} attached data source${dataSourceIds.length > 1 ? 's' : ''}` : 'Attach data'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.9">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14" />
              </svg>
              {dataSourceIds.length > 0 && (
                <span className="chat-upload-count">{dataSourceIds.length}</span>
              )}
            </button>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onCompositionStart={handleCompositionStart}
              onCompositionEnd={handleCompositionEnd}
              rows={1}
              className="chat-input"
              style={{ maxHeight: '200px' }}
              placeholder={dataSourceIds.length > 0 ? 'Ask DeepEye about your attached data...' : 'Attach data, then message DeepEye...'}
              disabled={isStreaming}
            />
            {isStreaming ? (
              <button type="button" onClick={stopMessage} className="chat-stop-btn" title="Stop generation">
                Stop
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="chat-send-btn"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="w-5 h-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="m5 12 7-7 7 7" />
                  <path d="M12 19V5" />
                </svg>
              </button>
            )}
          </div>
          {!compact && (
            <div className="chat-input-meta">
              <p className="chat-input-hint">
                {composerHelperText} Enter to send. Shift+Enter for newline. Verify critical results.
              </p>
              <span className={`chat-input-ds-badge ${dataSourceIds.length > 0 ? 'is-active' : ''}`}>
                {dataSourceIds.length > 0 ? `${dataSourceIds.length} data attached` : 'Use + to add data'}
              </span>
            </div>
          )}
          {compact && (
            <div className="chat-input-meta">
              <span className={`chat-input-ds-badge ${dataSourceIds.length > 0 ? 'is-active' : ''}`}>
                {dataSourceIds.length > 0 ? `${dataSourceIds.length} data attached` : 'Use + to add data'}
              </span>
            </div>
          )}
        </div>
      </div>
      {showDataSourceManager &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            className="chat-datasource-modal-overlay"
            onClick={() => setShowDataSourceManager(false)}
          >
            <div
              className="chat-datasource-modal"
              onClick={(event) => event.stopPropagation()}
            >
              <button
                type="button"
                className="chat-datasource-modal-close"
                onClick={() => setShowDataSourceManager(false)}
                aria-label="Close attached data dialog"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
              <DataSourceManager
                variant="modal"
                onDataSourcesChange={(sources) =>
                  onDataSourceIdsChange?.(sources.map((source) => source.id))
                }
              />
            </div>
          </div>,
          document.body,
        )}
    </div>
  )
}
