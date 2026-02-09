import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../stores/chat'
import { useKnowledgeBasesStore } from '../stores/knowledgeBases'
import StepItem from './StepItem'
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
  const [csvFiles, setCsvFiles] = useState<File[]>([])
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    const canSend = (input.trim() || csvFiles.length > 0) && !isStreaming
    if (!canSend) return
    const query = input.trim() || 'Generate a comprehensive report.'
    const kbIds = extractKbIds(query)
    sendMessage(query, dataSourceIds, kbIds, csvFiles.length > 0 ? csvFiles : undefined)
    setInput('')
    setCsvFiles([])
    setShowMentions(false)
    setMentionQuery('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    if (fileInputRef.current) fileInputRef.current.value = ''
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

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages.length, messages[messages.length - 1]?.content])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
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
          <div className="max-w-4xl mx-auto">
            {messages.map((msg, index) => (
              <div key={`msg-${index}`} className={`message-bubble ${msg.role}`}>
                {/* Tool Steps */}
                {msg.steps && msg.steps.length > 0 && msg.role !== 'user' && (
                  <div className="space-y-2 mb-3">
                    {msg.steps.map((step, sIdx) => (
                      <StepItem key={`step-${sIdx}`} step={step} />
                    ))}
                  </div>
                )}

                {/* Message Content */}
                {(msg.content || msg.isStreaming) && (
                  <div className="message-content">
                    {msg.role === 'user' ? (
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    ) : (
                      <>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content || ''}
                        </ReactMarkdown>
                        {msg.isStreaming && <span className="typing-cursor">|</span>}
                      </>
                    )}
                  </div>
                )}

                {/* Thinking indicator */}
                {msg.role === 'assistant' && msg.isStreaming && !msg.content && (!msg.steps || msg.steps.length === 0) && (
                  <div className="thinking-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                )}
              </div>
            ))}

            {/* Error */}
            {error && (
              <div className="text-center text-red-400 text-sm py-2">
                {error}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="chat-input-container">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {csvFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2 items-center">
              <span className="text-xs text-[var(--main-text-muted)]">CSV for report:</span>
              {csvFiles.map((f, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded bg-[var(--sidebar-bg)] text-sm"
                >
                  {f.name}
                  <button
                    type="button"
                    onClick={() => setCsvFiles((prev) => prev.filter((_, j) => j !== i))}
                    className="hover:opacity-70"
                    aria-label="Remove file"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="chat-input-wrapper">
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              multiple
              className="hidden"
              onChange={(e) => {
                const list = e.target.files ? Array.from(e.target.files) : []
                setCsvFiles((prev) => [...prev, ...list].filter((f) => f.name.toLowerCase().endsWith('.csv')))
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded-lg hover:bg-white/10 text-[var(--main-text-muted)]"
              title="Upload CSV for report"
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
                } else {
                  setShowMentions(false)
                  setMentionQuery('')
                }
              }}
              onKeyDown={handleKeyDown}
              rows={1}
              className="chat-input"
              style={{ maxHeight: '200px' }}
              placeholder={csvFiles.length > 0 ? 'Describe what report you want (or send as-is)...' : 'Message DeepEye...'}
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
          </div>
          <p className="text-xs text-[var(--main-text-muted)] text-center mt-2 opacity-60">
            DeepEye can make mistakes. Consider checking important information.
          </p>
        </div>
      </div>
    </div>
  )
}
