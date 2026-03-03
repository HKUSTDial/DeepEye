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
  const { sendMessage, error } = useChat()
  // 每个属性单独订阅 - 最简单可靠的方式
  const messages = useChatStore((state) => state.messages)
  const isStreaming = useChatStore((state) => state.isStreaming)
  const kbBases = useKnowledgeBasesStore((state) => state.bases)
  const loadBases = useKnowledgeBasesStore((state) => state.loadBases)
  
  const [input, setInput] = useState('')
  const [showMentions, setShowMentions] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composingRef = useRef(false)
  const compositionEndedAtRef = useRef(0)

  useEffect(() => {
    loadBases()
  }, [loadBases])

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
    if (input.trim() && !isStreaming) {
      const kbIds = extractKbIds(input)
      sendMessage(input.trim(), dataSourceIds, kbIds)
      setInput('')
      setShowMentions(false)
      setMentionQuery('')
      if (textareaRef.current) textareaRef.current.style.height = 'auto'
    }
  }

  const autoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }

  const scrollToBottom = () => {
    setTimeout(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTo({
          top: chatContainerRef.current.scrollHeight,
          behavior: 'smooth'
        })
      }
    }, 0)
  }
  const lastMessageContent = messages.length > 0 ? messages[messages.length - 1]?.content ?? '' : ''

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages.length, lastMessageContent])

  const handleCompositionStart = () => {
    composingRef.current = true
  }

  const handleCompositionEnd = () => {
    composingRef.current = false
    compositionEndedAtRef.current = Date.now()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      const native = e.nativeEvent
      const keyCode = native.keyCode || native.which || 0
      const composingOrSelecting =
        composingRef.current ||
        native.isComposing ||
        keyCode === 229 ||
        Date.now() - compositionEndedAtRef.current < 30
      // IME composing state: do not send message on Enter while user is selecting candidates.
      if (composingOrSelecting) {
        return
      }
      e.preventDefault()
      handleSend()
    }
  }

  const mentionMatches = showMentions
    ? kbBases.filter((kb) => kb.name.toLowerCase().includes(mentionQuery.toLowerCase()))
    : []

  const handleMentionSelect = (name: string) => {
    const next = input.replace(/@([^\s@]*)$/, `@${name} `)
    setInput(next)
    setShowMentions(false)
    setMentionQuery('')
    if (textareaRef.current) {
      textareaRef.current.focus()
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

  const renderAssistantMessage = (msg: Message) => {
    const timeline = msg.timeline && msg.timeline.length > 0 ? msg.timeline : null

    if (timeline) {
      return (
        <div className="assistant-timeline">
          {timeline.map((item, idx) => {
            if (item.kind === 'step') {
              return <StepItem key={`timeline-step-${idx}`} step={item.step} />
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
                  <div className="message-role-label">
                    {msg.role === 'user' ? 'You' : 'DeepEye'}
                  </div>
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

      {/* Input Area */}
      <div className="chat-input-container">
        <div className="chat-input-shell">
          <div className="chat-input-wrapper">
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
                } else {
                  setShowMentions(false)
                  setMentionQuery('')
                }
              }}
              onKeyDown={handleKeyDown}
              onCompositionStart={handleCompositionStart}
              onCompositionEnd={handleCompositionEnd}
              rows={1}
              className="chat-input"
              style={{ maxHeight: '200px' }}
              placeholder="Message DeepEye..."
              disabled={isStreaming}
            />
            {showMentions && mentionMatches.length > 0 && (
              <div className="mention-dropdown">
                <div className="mention-header">Knowledge Bases</div>
                <div className="mention-list">
                  {mentionMatches.map((kb) => (
                    <button
                      key={kb.id}
                      type="button"
                      onClick={() => handleMentionSelect(kb.name)}
                      className="mention-item"
                    >
                      @{kb.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
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
          </div>
          <p className="chat-input-hint">
            DeepEye can make mistakes. Consider checking important information.
          </p>
        </div>
      </div>
    </div>
  )
}
