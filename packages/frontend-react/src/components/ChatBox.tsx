import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../stores/chat'
import { useKnowledgeBasesStore } from '../stores/knowledgeBases'
import StepItem from './StepItem'

interface ChatBoxProps {
  dataSourceId: string
}

export default function ChatBox({ dataSourceId }: ChatBoxProps) {
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
      sendMessage(input.trim(), dataSourceId, kbIds)
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
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto scroll-smooth">
        {/* Empty State */}
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center px-4 animate-fade-in">
            <h2 className="text-2xl font-semibold mb-2">How can I help you today?</h2>
            <p className="text-[var(--main-text-muted)] text-center max-w-md">
              Ask me to analyze your data, write SQL queries, or create visualizations.
            </p>
          </div>
        )}

        {/* Messages */}
        {messages.length > 0 && (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
            {messages.map((msg, index) => (
              <div
                key={`msg-${index}`}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                style={{ animation: 'msgIn 0.4s var(--ease-out-expo) both' }}
              >
                {/* AI Avatar */}
                {msg.role !== 'user' && (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-[var(--accent)] text-white text-sm font-medium">
                    D
                  </div>
                )}

                {/* Message Content */}
                <div className={`flex-1 max-w-[80%] space-y-2 ${msg.role === 'user' ? 'flex flex-col items-end' : ''}`}>
                  {/* Tool Steps */}
                  {msg.steps && msg.steps.length > 0 && msg.role !== 'user' && (
                    <div className="space-y-2">
                      {msg.steps.map((step, sIdx) => (
                        <StepItem key={`step-${sIdx}`} step={step} />
                      ))}
                    </div>
                  )}

                  {/* Content Bubble */}
                  {(msg.content || msg.isStreaming) && (
                    <div
                      className={`inline-block rounded-2xl px-4 py-3 text-left ${
                        msg.role === 'user'
                          ? 'bg-[var(--accent)] text-white'
                          : 'bg-[var(--main-bg-alt)]'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        <>
                          <div className="prose-chat">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {msg.content || ''}
                            </ReactMarkdown>
                          </div>
                          {msg.isStreaming && <span className="typing-cursor"></span>}
                        </>
                      )}
                    </div>
                  )}

                  {/* Thinking indicator */}
                  {msg.role === 'assistant' && msg.isStreaming && !msg.content && (!msg.steps || msg.steps.length === 0) && (
                    <div className="thinking-dots py-2">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  )}
                </div>

                {/* User Avatar */}
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-purple-600 text-white text-sm font-medium">
                    U
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
      <div className="border-t border-[var(--input-border)] bg-[var(--main-bg)]">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="relative flex items-end bg-[var(--input-bg)] rounded-2xl border border-[var(--input-border)] input-focus-ring">
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
              className="flex-1 bg-transparent px-4 py-3 resize-none focus:outline-none text-[var(--main-text)] placeholder-[var(--main-text-muted)]"
              style={{ maxHeight: '200px' }}
              placeholder="Message DeepEye..."
              disabled={isStreaming}
            />
            {showMentions && mentionMatches.length > 0 && (
              <div className="absolute bottom-full left-3 mb-2 w-72 rounded-xl border border-slate-800 bg-slate-950 shadow-xl text-xs overflow-hidden z-50">
                <div className="px-3 py-2 text-slate-400 border-b border-slate-800">Knowledge Bases</div>
                <div className="max-h-48 overflow-y-auto">
                  {mentionMatches.map((kb) => (
                    <button
                      key={kb.id}
                      type="button"
                      onClick={() => handleMentionSelect(kb.name)}
                      className="w-full text-left px-3 py-2 hover:bg-slate-900 text-slate-200"
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
              className={`btn m-2 p-2 rounded-xl ${
                input.trim() && !isStreaming
                  ? 'bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white'
                  : 'bg-transparent text-[var(--main-text-muted)]'
              }`}
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

