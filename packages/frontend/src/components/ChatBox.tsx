import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { useChat } from '../hooks/useChat'
import {
  selectCurrentMessages,
  selectCurrentSessionId,
  selectIsStreaming,
  useChatStore,
} from '../stores/chat'
import { useWorkspaceUiStore } from '../stores/workspaceUi'
import { useRightPanelStore } from '../stores/rightPanel'
import { type ChatProgressLine } from '../utils/chatProgress'
import { AssistantMessageBody } from './AssistantMessageBody'
import { ChatEmptyState } from './ChatEmptyState'
import { ChatContextStrip } from './ChatContextStrip'
import { ChatErrorNotice } from './ChatErrorNotice'
import { buildFollowUpPrompts, buildMessageActivityKey, hasText } from './chatBoxUtils'
import type { DataSource } from '../types'
import { useLocale } from '../locale'
import { deferEffectWork } from '../utils/effects'
import './ChatBox.css'

interface ChatBoxProps {
  dataSources: DataSource[]
  compact?: boolean
  isLoadingDataSources?: boolean
  onRemoveDataSource?: (dataSourceId: string) => void | Promise<void>
}

export default function ChatBox({
  dataSources,
  compact = false,
  isLoadingDataSources = false,
  onRemoveDataSource,
}: ChatBoxProps) {
  const { sendMessage, stopMessage, error } = useChat()
  // 每个属性单独订阅 - 最简单可靠的方式
  const messages = useChatStore(selectCurrentMessages)
  const sessionId = useChatStore(selectCurrentSessionId)
  const isStreaming = useChatStore(selectIsStreaming)
  const showDataSourceManager = useWorkspaceUiStore((state) => state.isDataSourceManagerOpen)
  const openDataSourceManager = useWorkspaceUiStore((state) => state.openDataSourceManager)
  const openOrFocusTab = useRightPanelStore((state) => state.openOrFocusTab)
  const { locale, isZh, t } = useLocale()
  
  const [input, setInput] = useState('')
  const [isNearBottom, setIsNearBottom] = useState(true)
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null)
  const [queuedPrompt, setQueuedPrompt] = useState<string | null>(null)
  const [removingDataSourceId, setRemovingDataSourceId] = useState<string | null>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const composingRef = useRef(false)
  const compositionEndedAtRef = useRef(0)
  const dataSourceIds = useMemo(() => dataSources.map((source) => source.id), [dataSources])
  const hasDatabaseSource = dataSources.some((source) => source.category === 'database')
  const hasFileSource = dataSources.some((source) => source.category === 'file')
  const sourceNames = dataSources.map((source) => source.name)
  const starterPrompts = useMemo(() => {
    if (dataSources.length === 0) {
      return [
        {
          label: isZh ? '快速看数' : 'Profile the data',
          description: isZh
            ? '先规划接入文件或数据库后的第一轮检查。'
            : 'Plan a fast first pass once files or databases are attached.',
          prompt: isZh
            ? '请分析我附加的数据源，说明关键字段、数据质量问题，以及最值得继续追问的方向。'
            : 'Please analyze my attached data sources, highlight key fields, data quality issues, and the most practical next steps.',
        },
        {
          label: isZh ? '推荐图表' : 'Recommend charts',
          description: isZh
            ? '给出最值得做的图和每张图回答的问题。'
            : 'Suggest the highest-signal visuals and what each one answers.',
          prompt: isZh
            ? '请推荐三种最有价值的可视化，并说明每张图能回答什么业务问题。'
            : 'Recommend three high-value visualizations for this dataset and explain what business questions each chart answers.',
        },
        {
          label: isZh ? '报告大纲' : 'Outline a report',
          description: isZh
            ? '先起一个结论、风险和建议都齐全的报告草稿。'
            : 'Draft a concise report with findings, risks, and actions.',
          prompt: isZh
            ? '请生成一份业务报告草稿，包含摘要、关键发现、风险和可执行建议。'
            : 'Generate a business report draft with summary, key findings, risks, and actionable recommendations.',
        },
      ]
    }

    if (hasDatabaseSource && !hasFileSource) {
      return [
        {
          label: isZh ? '梳理库表' : 'Map the schema',
          description: isZh
            ? '先确认核心表、join 路径和最值得切入的问题。'
            : 'Identify core tables, join paths, and the best starting questions.',
          prompt: isZh
            ? '请检查已附加的数据库数据源，识别核心表与 join 关系，并给出三个最值得先做的分析方向。'
            : 'Inspect the attached database sources, identify the core tables and joins, and recommend the three strongest analysis directions.',
        },
        {
          label: isZh ? '设计 KPI' : 'Design KPIs',
          description: isZh
            ? '把现有 schema 变成一版高层指标方案。'
            : 'Turn the available schema into an executive KPI plan.',
          prompt: isZh
            ? '基于已附加的数据库数据源，设计一版 KPI dashboard 大纲，包含核心指标、维度和 drill-down。'
            : 'Based on the attached database sources, propose a KPI dashboard outline with the highest-value metrics, dimensions, and drill-downs.',
        },
        {
          label: isZh ? '写分析 SQL' : 'Write analysis SQL',
          description: isZh
            ? '直接起草第一批最有价值的查询。'
            : 'Draft the first set of practical queries to answer business questions.',
          prompt: isZh
            ? '请为已附加的数据库数据源写出第一批 SQL，用来发现业务趋势、异常和机会。'
            : 'Write the first batch of SQL queries I should run against the attached database sources to uncover business trends, anomalies, and opportunities.',
        },
      ]
    }

    if (dataSources.length > 1) {
      return [
        {
          label: isZh ? '梳理数据关系' : 'Reconcile the sources',
          description: isZh
            ? '先确认这些数据源之间怎么关联。'
            : 'Figure out how the attached files and databases relate.',
          prompt: isZh
            ? '请检查这些已附加的数据源，说明它们如何组合使用，并指出我应该先验证的 join、主键和潜在不一致。'
            : 'Review the attached data sources, explain how they can be combined, and identify the joins, keys, and mismatches I should validate first.',
        },
        {
          label: isZh ? '跨源洞察' : 'Find cross-source insights',
          description: isZh
            ? '推荐跨数据源最值得做的对比分析。'
            : 'Recommend the most valuable comparisons across the attached sources.',
          prompt: isZh
            ? '请找出这些已附加数据源最值得做的跨源分析，并说明每一种能揭示什么。'
            : 'Find the highest-value cross-source analyses for the attached data and explain what each one could reveal.',
        },
        {
          label: isZh ? '组合报告' : 'Plan a combined report',
          description: isZh
            ? '把多个数据源整合成一条完整业务叙事。'
            : 'Turn the attached sources into one concise business narrative.',
          prompt: isZh
            ? '请基于这些已附加数据源规划一份整合报告，形成一条包含发现、风险和建议动作的业务故事线。'
            : 'Create a report outline that combines the attached data sources into one executive story with findings, risks, and recommended actions.',
        },
      ]
    }

    return [
      {
        label: isZh ? '检查文件' : 'Profile the file',
        description: isZh
          ? '先看字段、结构、质量问题和第一批机会。'
          : 'Check fields, structure, data quality, and immediate issues.',
        prompt: isZh
          ? `请分析当前附加的数据集${sourceNames[0] ? `（${sourceNames[0]}）` : ''}，总结 schema、数据质量问题，以及最值得继续追问的方向。`
          : `Analyze the attached dataset ${sourceNames[0] ? `(${sourceNames[0]}) ` : ''}and summarize the schema, data quality issues, and the best next questions to ask.`,
      },
      {
        label: isZh ? '推荐图表' : 'Recommend charts',
        description: isZh
          ? '挑出最有信号的图表和它们回答的问题。'
          : 'Suggest the highest-signal visuals and what each one answers.',
        prompt: isZh
          ? '请为当前附加的数据集推荐三种最有价值的可视化，并解释每种图表回答什么业务问题。'
          : 'Recommend three high-value visualizations for the attached dataset and explain what business questions each chart answers.',
      },
      {
        label: isZh ? '起草报告' : 'Draft a report',
        description: isZh
          ? '先生成一版数据洞察报告结构。'
          : 'Outline the strongest structure for a data insight report.',
        prompt: isZh
          ? '请为当前附加的数据集生成一份业务报告草稿，包含摘要、关键发现、风险和可执行建议。'
          : 'Generate a business report draft for the attached dataset with summary, key findings, risks, and actionable recommendations.',
      },
    ]
  }, [dataSources.length, hasDatabaseSource, hasFileSource, isZh, sourceNames])

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [])

  useEffect(() => {
    resizeTextarea()
  }, [input, resizeTextarea])

  const resetComposer = () => {
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleSend = () => {
    if (!input.trim()) return
    const query = input.trim()
    if (isStreaming) {
      setQueuedPrompt(query)
      setInput('')
      resetComposer()
      return
    }
    void sendMessage(query, dataSourceIds)
    setInput('')
    setIsNearBottom(true)
    setQueuedPrompt(null)
    resetComposer()
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

  useEffect(() => {
    if (isStreaming || error || !queuedPrompt) {
      return
    }
    return deferEffectWork(() => {
      const nextPrompt = queuedPrompt
      setQueuedPrompt(null)
      void sendMessage(nextPrompt, dataSourceIds)
      setIsNearBottom(true)
      scrollToBottom()
    })
  }, [dataSourceIds, error, isStreaming, queuedPrompt, sendMessage])

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

  const insertQuotedMessage = (content: string) => {
    const quoted = content
      .trim()
      .split('\n')
      .map((line) => `> ${line}`)
      .join('\n')
    const prefix = input.trim() ? `${input.trim()}\n\n` : ''
    const nextValue = `${prefix}${quoted}\n\n`
    setInput(nextValue)
    requestAnimationFrame(() => {
      if (!textareaRef.current) return
      textareaRef.current.focus()
      const caret = nextValue.length
      textareaRef.current.setSelectionRange(caret, caret)
      resizeTextarea()
    })
  }

  const removeDataSource = async (dataSourceId: string) => {
    if (!onRemoveDataSource) return
    setRemovingDataSourceId(dataSourceId)
    try {
      await onRemoveDataSource(dataSourceId)
    } finally {
      setRemovingDataSourceId((current) => (current === dataSourceId ? null : current))
    }
  }

  const retryLastPrompt = () => {
    if (isStreaming) return
    const lastUserPrompt = [...messages]
      .reverse()
      .find((message) => message.role === 'user' && hasText(message.content))
      ?.content
      ?.trim()
    if (!lastUserPrompt) return
    setQueuedPrompt(null)
    void sendMessage(lastUserPrompt, dataSourceIds)
    setIsNearBottom(true)
    scrollToBottom()
  }

  const renderStreamingIndicator = () => (
    <span className="streaming-indicator" aria-hidden="true">
      <span className="streaming-indicator-dot"></span>
      <span className="streaming-indicator-dot"></span>
      <span className="streaming-indicator-dot"></span>
    </span>
  )
  const getProgressStatusLabel = (status: ChatProgressLine['status']) => {
    if (status === 'done') return t('common.completed')
    if (status === 'warning') return t('common.needsAttention')
    if (status === 'error') return t('common.failed')
    return t('common.running')
  }
  const renderProgressLine = (progress: ChatProgressLine, key: string) => (
    <div key={key} className={`chat-progress-line chat-progress-line--${progress.tone} chat-progress-line--${progress.status}`}>
      <span className="chat-progress-badge">{progress.badge}</span>
      <span className="chat-progress-copy">
        <span className="chat-progress-label">{progress.label}</span>
        {progress.detail ? <span className="chat-progress-detail">{progress.detail}</span> : null}
      </span>
      <span className={`chat-progress-state chat-progress-state--${progress.status}`}>{getProgressStatusLabel(progress.status)}</span>
    </div>
  )
  const showJumpButton = messages.length > 0 && !isNearBottom
  const dataSourceCount = dataSources.length
  const lastAssistantMessageIndex = [...messages]
    .map((message, index) => ({ message, index }))
    .reverse()
    .find((item) => item.message.role === 'assistant')
    ?.index ?? -1
  const sourceStatusText = dataSourceIds.length > 0
    ? t('common.attachedDataCount', { count: dataSourceIds.length })
    : t('common.noDataAttached')
  const composerHelperText = dataSourceIds.length > 0
    ? t('chat.threadUsesAttachedData')
    : t('chat.attachDataFirst')
  const emptyTitle = dataSourceIds.length > 0
    ? t('chat.emptyTitleAttached')
    : t('chat.emptyTitleNoData')
  const emptySubtitle = dataSourceIds.length > 0
    ? t('chat.emptySubtitleAttached')
    : t('chat.emptySubtitleNoData')
  const emptyContextChips = useMemo(() => {
    if (dataSources.length === 0) {
      return [t('chat.contextChipJoin')]
    }

    const chips = dataSources.slice(0, 2).map((source) => source.name)
    if (dataSources.length > 2) {
      chips.push(t('chat.contextChipMoreSources', { count: dataSources.length - 2 }))
    }
    if (hasDatabaseSource && hasFileSource) {
      chips.push(t('chat.contextChipCombined'))
    } else if (hasDatabaseSource) {
      chips.push(t('chat.contextChipSql'))
    } else {
      chips.push(t('chat.contextChipFile'))
    }
    return chips
  }, [dataSources, hasDatabaseSource, hasFileSource, t])
  const canRetry = !isStreaming && messages.some((message) => message.role === 'user' && hasText(message.content))

  return (
    <div className={`chat-container ${compact ? 'compact' : ''}`}>
      {/* Messages Area */}
      <div ref={chatContainerRef} className="chat-messages">
        {/* Empty State */}
        {messages.length === 0 && (
          <ChatEmptyState
            dataSourceCount={dataSourceCount}
            emptyTitle={emptyTitle}
            emptySubtitle={emptySubtitle}
            sourceStatusText={sourceStatusText}
            contextChips={emptyContextChips}
            starterPrompts={starterPrompts}
            addDataLabel={t('common.addData')}
            addDataDescription={t('chat.addDataCtaDescription')}
            onOpenDataSourceManager={openDataSourceManager}
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
                    {t('common.assistant')}
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
                        {copiedMessageIndex === index ? t('common.copied') : t('common.copy')}
                      </button>
                      <button
                        type="button"
                        className="message-action-btn"
                        onClick={() => insertQuotedMessage(msg.content)}
                      >
                        {t('common.quote')}
                      </button>
                      {index === lastAssistantMessageIndex && (
                        <button
                          type="button"
                          className="message-action-btn"
                          onClick={retryLastPrompt}
                          disabled={isStreaming}
                        >
                          {t('common.retry')}
                        </button>
                      )}
                    </div>
                  )}
                  {msg.role === 'assistant' &&
                    index === lastAssistantMessageIndex &&
                    hasText(msg.content) &&
                    !msg.isStreaming && (
                      <div className="message-followups">
                        {buildFollowUpPrompts(msg.content, dataSourceCount > 0, locale).map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            className="message-followup-chip"
                            onClick={() => applyStarterPrompt(prompt)}
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    )}
                </div>

                {msg.role === 'user' && (
                  <div className="message-avatar user" aria-hidden="true">
                    {isZh ? '你' : 'You'}
                  </div>
                )}
              </div>
            ))}

            {/* Error */}
            {error && (
              <ChatErrorNotice
                error={error}
                canRetry={canRetry}
                canOpenWorkflow={!!sessionId && sessionId !== 'draft'}
                canOpenData
                onRetry={retryLastPrompt}
                onOpenData={openDataSourceManager}
                onOpenWorkflow={() => openOrFocusTab('workflow')}
              />
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
          {t('common.jumpToLatest')}
        </button>
      )}

      {/* Input Area */}
      <div className="chat-input-container">
        <div className="chat-input-shell">
          <ChatContextStrip
            dataSources={dataSources}
            isLoading={isLoadingDataSources}
            isCompact={compact}
            removingDataSourceId={removingDataSourceId}
            onOpenManager={openDataSourceManager}
            onRemoveDataSource={removeDataSource}
          />
          {queuedPrompt && (
            <div className="chat-queued-prompt">
              <div className="chat-queued-prompt-copy">
                <span className="chat-queued-prompt-label">{t('chat.queuedNext')}</span>
                <span className="chat-queued-prompt-text">{queuedPrompt}</span>
              </div>
              <button
                type="button"
                className="chat-queued-prompt-clear"
                onClick={() => setQueuedPrompt(null)}
              >
                {t('common.clear')}
              </button>
            </div>
          )}
          <div className={`chat-input-wrapper ${isStreaming ? 'is-streaming' : ''}`}>
            <button
              type="button"
              className={`chat-upload-btn ${showDataSourceManager ? 'is-active' : ''}`}
              onClick={openDataSourceManager}
              title={dataSourceIds.length > 0 ? t('common.attachedDataCount', { count: dataSourceIds.length }) : t('common.addData')}
              aria-label={dataSourceIds.length > 0 ? t('common.attachedDataCount', { count: dataSourceIds.length }) : t('common.addData')}
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
              placeholder={dataSourceIds.length > 0
                ? t('chat.placeholderAttached')
                : t('chat.placeholderNoData')}
            />
            <div className="chat-composer-actions">
              {isStreaming && (
                <button
                  type="button"
                  onClick={stopMessage}
                  className="chat-stop-btn"
                  title={t('common.stop')}
                >
                  {t('common.stop')}
                </button>
              )}
              <button
                type="button"
                onClick={handleSend}
                disabled={!input.trim()}
                className={isStreaming ? 'chat-queue-btn' : 'chat-send-btn'}
              >
                {isStreaming ? (
                  t('common.queue')
                ) : (
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
                )}
              </button>
            </div>
          </div>
          {!compact && (
            <div className="chat-input-meta">
              <p className="chat-input-hint">
                {isStreaming
                  ? t('chat.streamingHint')
                  : `${composerHelperText} ${t('chat.inputHintSuffix')}`}
              </p>
              <span className={`chat-input-ds-badge ${dataSourceIds.length > 0 ? 'is-active' : ''}`}>
                {queuedPrompt
                  ? t('common.onePromptQueued')
                  : dataSourceIds.length > 0
                    ? t('common.dataAttachedBadge', { count: dataSourceIds.length })
                    : t('common.usePlusToAddData')}
              </span>
            </div>
          )}
          {compact && (
            <div className="chat-input-meta">
              <span className={`chat-input-ds-badge ${dataSourceIds.length > 0 ? 'is-active' : ''}`}>
                {queuedPrompt
                  ? t('common.onePromptQueued')
                  : dataSourceIds.length > 0
                    ? t('common.dataAttachedBadge', { count: dataSourceIds.length })
                    : t('common.usePlusToAddData')}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
