import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../stores/chat'
import { useKnowledgeBasesStore } from '../stores/knowledgeBases'
import StepItem from './StepItem'
import type { Message } from '../types'
import './ChatBox.css'

interface ChatBoxProps {
  dataSourceIds: string[]
}

export default function ChatBox({ dataSourceIds }: ChatBoxProps) {
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
  const [csvFiles, setCsvFiles] = useState<File[]>([])
  const [uploadNotice, setUploadNotice] = useState<string | null>(null)
  const [attachmentsExpanded, setAttachmentsExpanded] = useState(true)
  const [isNearBottom, setIsNearBottom] = useState(true)
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composingRef = useRef(false)
  const compositionEndedAtRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const mentionDropdownRef = useRef<HTMLDivElement>(null)
  const starterPrompts = [
    {
      label: 'Analyze This Data',
      description: 'Profile fields, data quality, and immediate risks.',
      prompt: 'Please analyze my selected data sources, highlight key fields, data quality issues, and the most practical next steps.',
    },
    {
      label: 'Suggest Visual Insights',
      description: 'Propose high-impact charts with business questions.',
      prompt: 'Recommend three high-value visualizations for this dataset and explain what business questions each chart answers.',
    },
    {
      label: 'Draft a Report',
      description: 'Create an executive summary with actions and follow-ups.',
      prompt: 'Generate a business report draft with summary, key findings, risks, and actionable recommendations.',
    },
  ]

  const isSupportedReportFile = (name: string) => {
    const n = name.toLowerCase()
    return n.endsWith('.csv') || n.endsWith('.json') || n.endsWith('.xlsx') || n.endsWith('.xls') || n.endsWith('.parquet')
  }

  useEffect(() => {
    loadBases()
  }, [loadBases])

  useEffect(() => {
    if (!uploadNotice) return
    const timer = window.setTimeout(() => {
      setUploadNotice(null)
    }, 3200)
    return () => window.clearTimeout(timer)
  }, [uploadNotice])

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
    const canSend = (input.trim() || csvFiles.length > 0) && !isStreaming
    if (!canSend) return
    const query = input.trim() || 'Generate a comprehensive report.'
    const kbIds = extractKbIds(query)
    sendMessage(query, dataSourceIds, kbIds, csvFiles.length > 0 ? csvFiles : undefined)
    setInput('')
    setCsvFiles([])
    setUploadNotice(null)
    setAttachmentsExpanded(false)
    setShowMentions(false)
    setMentionQuery('')
    setActiveMentionIndex(0)
    setIsNearBottom(true)
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    if (fileInputRef.current) fileInputRef.current.value = ''
    scrollToBottom()
  }

  const autoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
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
    if (textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
    }
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
  const sourceStatusText = dataSourceIds.length > 0 ? `${dataSourceIds.length} data source(s) ready` : 'No data source attached yet'
  const attachmentCount = csvFiles.length

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
    <div className="chat-container">
      {/* Messages Area */}
      <div ref={chatContainerRef} className="chat-messages">
        {/* Empty State */}
        {messages.length === 0 && (
          <div className="chat-empty">
            <svg className="chat-empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <h2 className="chat-empty-title">How can I help you today?</h2>
            <p className="chat-empty-subtitle">
              Ask me to analyze your data, write SQL queries, or create visualizations.
            </p>
            <div className="chat-empty-context">
              <span className={`chat-empty-context-chip ${dataSourceIds.length > 0 ? 'active' : ''}`}>{sourceStatusText}</span>
              <span className="chat-empty-context-chip">@knowledge-base mentions supported</span>
            </div>
            <div className="chat-empty-prompts">
              {starterPrompts.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className="chat-empty-prompt"
                  onClick={() => applyStarterPrompt(item.prompt)}
                >
                  <span className="chat-empty-prompt-title">{item.label}</span>
                  <span className="chat-empty-prompt-desc">{item.description}</span>
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
          {attachmentCount > 0 && (
            <div className="chat-attachments">
              <button
                type="button"
                className="chat-attachments-toggle"
                onClick={() => setAttachmentsExpanded((prev) => !prev)}
                aria-expanded={attachmentsExpanded}
              >
                <span className="chat-attachments-label">Files for workflow</span>
                <span className="chat-attachments-count">{attachmentCount}</span>
                <svg className={`chat-attachments-chevron ${attachmentsExpanded ? 'expanded' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {attachmentsExpanded && (
                <div className="chat-attachments-list">
                  {csvFiles.map((f, i) => (
                    <span key={i} className="chat-attachment-chip">
                      {f.name}
                      <button
                        type="button"
                        onClick={() =>
                          setCsvFiles((prev) => {
                            const next = prev.filter((_, j) => j !== i)
                            if (next.length === 0) {
                              setAttachmentsExpanded(false)
                            }
                            return next
                          })
                        }
                        className="chat-attachment-remove"
                        aria-label="Remove file"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
          <div className="chat-input-wrapper">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.json,.xlsx,.xls,.parquet"
              multiple
              className="hidden"
              onChange={(e) => {
                const list = e.target.files ? Array.from(e.target.files) : []
                const supported = list.filter((f) => isSupportedReportFile(f.name))
                const existing = new Set(csvFiles.map((f) => `${f.name}:${f.size}:${f.lastModified}`))
                const uniqueSupported = supported.filter((f) => {
                  const signature = `${f.name}:${f.size}:${f.lastModified}`
                  if (existing.has(signature)) return false
                  existing.add(signature)
                  return true
                })
                const unsupportedCount = list.length - supported.length
                const duplicateCount = supported.length - uniqueSupported.length
                const noticeParts: string[] = []
                if (unsupportedCount > 0) {
                  noticeParts.push(`${unsupportedCount} unsupported file(s) ignored`)
                }
                if (duplicateCount > 0) {
                  noticeParts.push(`${duplicateCount} duplicate file(s) skipped`)
                }
                setUploadNotice(noticeParts.length > 0 ? `${noticeParts.join('. ')}.` : null)
                setCsvFiles((prev) => [...prev, ...uniqueSupported])
                if (uniqueSupported.length > 0) {
                  setAttachmentsExpanded(true)
                }
                e.target.value = ''
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="chat-upload-btn"
              title="Upload data files"
              disabled={isStreaming}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </button>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                const value = e.target.value
                setInput(value)
                autoResize(e)
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
              placeholder={csvFiles.length > 0 ? 'Describe what report you want (or send as-is)...' : 'Message DeepEye...'}
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
                disabled={(!input.trim() && csvFiles.length === 0) || isStreaming}
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
          <div className="chat-input-meta">
            <p className="chat-input-hint">
              Enter to send, Shift+Enter for newline. DeepEye can make mistakes, please verify important results.
            </p>
            <span className="chat-input-ds-badge">
              {dataSourceIds.length > 0 ? `${dataSourceIds.length} source(s) attached` : 'No source attached'}
            </span>
          </div>
          {uploadNotice && (
            <p className="chat-upload-notice" role="status">
              {uploadNotice}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
