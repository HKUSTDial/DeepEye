import { useState, useRef, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../stores/chat'
import { useKnowledgeBasesStore } from '../stores/knowledgeBases'
import DataSourceManager from './DataSourceManager'
import StepItem from './StepItem'
import type { Message } from '../types'
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
  const messages = useChatStore((state) => state.messages)
  const isStreaming = useChatStore((state) => state.isStreaming)
  const kbBases = useKnowledgeBasesStore((state) => state.bases)
  const loadBases = useKnowledgeBasesStore((state) => state.loadBases)
  
  const [input, setInput] = useState('')
  const [showMentions, setShowMentions] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const [activeMentionIndex, setActiveMentionIndex] = useState(0)
  const [showDataSourceManager, setShowDataSourceManager] = useState(false)
  const [isNearBottom, setIsNearBottom] = useState(true)
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composingRef = useRef(false)
  const compositionEndedAtRef = useRef(0)
  const mentionDropdownRef = useRef<HTMLDivElement>(null)
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
    loadBases()
  }, [loadBases])

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

  useEffect(() => {
    const onMouseDown = (event: MouseEvent) => {
      if (!showMentions) return
      const target = event.target as Node
      if (mentionDropdownRef.current?.contains(target)) return
      if (textareaRef.current?.contains(target)) return
      setShowMentions(false)
      setMentionQuery('')
      setActiveMentionIndex(0)
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [showMentions])

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [])

  useEffect(() => {
    resizeTextarea()
  }, [input, resizeTextarea])

  const extractKbIds = (text: string) => {
    const ids: string[] = []
    kbBases.forEach((kb) => {
      if (text.includes(`@${kb.name}`)) {
        ids.push(kb.id)
      }
    })
    return ids
  }

  const handleSend = () => {
    const canSend = Boolean(input.trim()) && !isStreaming
    if (!canSend) return
    const query = input.trim()
    const kbIds = extractKbIds(query)
    sendMessage(query, dataSourceIds, kbIds)
    setInput('')
    setShowMentions(false)
    setMentionQuery('')
    setActiveMentionIndex(0)
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
  const lastMessageContent = messages.length > 0 ? messages[messages.length - 1]?.content ?? '' : ''

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
  }, [messages.length, lastMessageContent, isNearBottom])

  const handleCompositionStart = () => {
    composingRef.current = true
  }

  const handleCompositionEnd = (e: React.CompositionEvent<HTMLTextAreaElement>) => {
    composingRef.current = false
    compositionEndedAtRef.current = e.timeStamp
  }

  const mentionMatches = showMentions
    ? kbBases.filter((kb) => kb.name.toLowerCase().includes(mentionQuery.toLowerCase()))
    : []
  const effectiveMentionIndex =
    mentionMatches.length > 0 ? Math.min(activeMentionIndex, mentionMatches.length - 1) : 0

  useEffect(() => {
    if (!showMentions || mentionMatches.length === 0 || !mentionDropdownRef.current) return
    const active = mentionDropdownRef.current.querySelector<HTMLButtonElement>('.mention-item.active')
    active?.scrollIntoView({ block: 'nearest' })
  }, [showMentions, mentionMatches.length, effectiveMentionIndex])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const native = e.nativeEvent
    const keyCode = native.keyCode || native.which || 0
    const composingOrSelecting =
      composingRef.current ||
      native.isComposing ||
      keyCode === 229 ||
      native.timeStamp - compositionEndedAtRef.current < 30

    if (showMentions) {
      if (e.key === 'ArrowDown' && mentionMatches.length > 0) {
        e.preventDefault()
        setActiveMentionIndex((current) => (current + 1) % mentionMatches.length)
        return
      }
      if (e.key === 'ArrowUp' && mentionMatches.length > 0) {
        e.preventDefault()
        setActiveMentionIndex((current) => (current - 1 + mentionMatches.length) % mentionMatches.length)
        return
      }
      if ((e.key === 'Enter' || e.key === 'Tab') && mentionMatches.length > 0 && !composingOrSelecting) {
        e.preventDefault()
        handleMentionSelect(mentionMatches[effectiveMentionIndex].name)
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowMentions(false)
        setMentionQuery('')
        setActiveMentionIndex(0)
        return
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      // IME composing state: do not send message on Enter while user is selecting candidates.
      if (composingOrSelecting) {
        return
      }
      e.preventDefault()
      handleSend()
    }
  }

  const handleMentionSelect = (name: string) => {
    const next = input.replace(/@([^\s@]*)$/, `@${name} `)
    setInput(next)
    setShowMentions(false)
    setMentionQuery('')
    setActiveMentionIndex(0)
    if (textareaRef.current) {
      textareaRef.current.focus()
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
  const hasText = (value?: string) => Boolean(value && value.trim().length > 0)
  const showJumpButton = messages.length > 0 && !isNearBottom
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

  const renderAssistantMessage = (msg: Message) => {
    const timeline = msg.timeline && msg.timeline.length > 0 ? msg.timeline : null

    if (timeline) {
      return (
        <div className="assistant-timeline">
          {timeline.map((item, idx) => {
            if (item.kind === 'step') {
              return <StepItem key={`timeline-step-${idx}`} step={item.step} />
            }
            if (item.kind === 'report_step') {
              return (
                <div key={`timeline-report-${idx}`} className="report-step-line">
                  <span className="report-step-badge">Step {item.stepIndex}/{item.totalSteps}</span>
                  <span className="report-step-label">{item.label}</span>
                </div>
              )
            }
            return (
              <div key={`timeline-text-${idx}`} className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {item.content || ''}
                </ReactMarkdown>
                {item.isStreaming && hasText(item.content) && renderStreamingIndicator()}
              </div>
            )
          })}
        </div>
      )
    }

    return (
      <>
        {msg.steps && msg.steps.length > 0 && (
          <div className="space-y-2 mb-3">
            {msg.steps.map((step, sIdx) => (
              <StepItem key={`step-${sIdx}`} step={step} />
            ))}
          </div>
        )}
        {(msg.content || msg.isStreaming) && (
          <div className="message-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content || ''}
            </ReactMarkdown>
            {msg.isStreaming && hasText(msg.content) && renderStreamingIndicator()}
          </div>
        )}
      </>
    )
  }

  return (
    <div className={`chat-container ${compact ? 'compact' : ''}`}>
      {/* Messages Area */}
      <div ref={chatContainerRef} className="chat-messages">
        {/* Empty State */}
        {messages.length === 0 && (
          <div className="chat-empty">
            <svg className="chat-empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <h2 className="chat-empty-title">{emptyTitle}</h2>
            <p className="chat-empty-subtitle">{emptySubtitle}</p>
            <div className={`chat-empty-status ${dataSourceIds.length > 0 ? 'is-active' : ''}`}>
              <span className="chat-empty-status-dot" aria-hidden="true"></span>
              <span>{sourceStatusText}</span>
            </div>
            <div className="chat-empty-context">
              <span className={`chat-empty-context-chip ${dataSourceIds.length > 0 ? 'active' : ''}`}>Files and databases join automatically</span>
              <span className="chat-empty-context-chip">Use @ to reference a knowledge base</span>
            </div>
            <div className="chat-empty-prompts">
              {starterPrompts.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className="chat-empty-prompt"
                  onClick={() => applyStarterPrompt(item.prompt)}
                >
                  <span className="chat-empty-prompt-copy">
                    <span className="chat-empty-prompt-title">{item.label}</span>
                    <span className="chat-empty-prompt-desc">{item.description}</span>
                  </span>
                  <span className="chat-empty-prompt-arrow" aria-hidden="true">
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7 17 17 7M9 7h8v8" />
                    </svg>
                  </span>
                </button>
              ))}
            </div>
          </div>
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
                      renderAssistantMessage(msg)
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
              onChange={(e) => {
                const value = e.target.value
                setInput(value)
                const match = value.match(/@([^\s@]*)$/)
                if (match) {
                  setShowMentions(true)
                  setMentionQuery(match[1])
                  setActiveMentionIndex(0)
                } else {
                  setShowMentions(false)
                  setMentionQuery('')
                  setActiveMentionIndex(0)
                }
              }}
              onKeyDown={handleKeyDown}
              onCompositionStart={handleCompositionStart}
              onCompositionEnd={handleCompositionEnd}
              rows={1}
              className="chat-input"
              style={{ maxHeight: '200px' }}
              placeholder={dataSourceIds.length > 0 ? 'Ask DeepEye about your attached data...' : 'Attach data, then message DeepEye...'}
              disabled={isStreaming}
            />
            {showMentions && (
              <div className="mention-dropdown" ref={mentionDropdownRef}>
                <div className="mention-header">Knowledge Bases</div>
                {mentionMatches.length > 0 ? (
                  <div className="mention-list">
                    {mentionMatches.map((kb, idx) => (
                      <button
                        key={kb.id}
                        type="button"
                        onClick={() => handleMentionSelect(kb.name)}
                        onMouseEnter={() => setActiveMentionIndex(idx)}
                        className={`mention-item ${idx === effectiveMentionIndex ? 'active' : ''}`}
                        aria-selected={idx === effectiveMentionIndex}
                      >
                        @{kb.name}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="mention-empty">
                    No knowledge base matched @{mentionQuery || '...'}
                  </div>
                )}
              </div>
            )}
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
