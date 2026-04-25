import { useMemo, useState, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import type { ChatProgressLine } from '../utils/chatProgress'
import type { Message } from '../types'
import { useLocale } from '../locale'
import StepItem from './StepItem'
import { hasText } from './chatBoxUtils'
import { splitAssistantMessageSections } from './assistantMessageBodyUtils'

interface AssistantMessageBodyProps {
  message: Message
  renderProgressLine: (progress: ChatProgressLine, key: string) => ReactNode
  renderStreamingIndicator: () => ReactNode
}

export function AssistantMessageBody({
  message,
  renderProgressLine,
  renderStreamingIndicator,
}: AssistantMessageBodyProps) {
  const { t } = useLocale()
  const { finalContent, processEntries } = useMemo(
    () => splitAssistantMessageSections(message),
    [message],
  )
  const hasFinalContent = hasText(finalContent)
  const [showProcess, setShowProcess] = useState(
    () => message.isStreaming || !hasFinalContent || processEntries.length > 0,
  )
  const isProcessVisible = showProcess || message.isStreaming || !hasFinalContent

  return (
    <div className="assistant-message-stack">
      {processEntries.length > 0 && (
        <section className="assistant-process-card">
          <button
            type="button"
            className="assistant-process-toggle"
            onClick={() => setShowProcess((current) => !current)}
            aria-expanded={isProcessVisible}
          >
            <span className="assistant-process-toggle-copy">
              <span className="assistant-process-toggle-label">{t('assistant.activity')}</span>
              <span className="assistant-process-toggle-meta">
                {t('assistant.activityUpdates', { count: processEntries.length })}
              </span>
            </span>
            <span className={`assistant-process-toggle-chevron ${isProcessVisible ? 'is-open' : ''}`}>
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="m5 7.5 5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          </button>
          {isProcessVisible && (
            <div className="assistant-process-body">
              {processEntries.map((entry, index) => {
                if (entry.kind === 'step') {
                  return <StepItem key={`timeline-step-${index}`} step={entry.step} />
                }
                return renderProgressLine(entry.progress, `timeline-progress-${index}`)
              })}
            </div>
          )}
        </section>
      )}

      {hasFinalContent && (
        <section className="assistant-answer-card">
          <div className="assistant-answer-kicker">
            {message.isStreaming ? t('assistant.draftingResponse') : t('assistant.finalAnswer')}
          </div>
          <div className="message-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalContent}</ReactMarkdown>
            {message.isStreaming && renderStreamingIndicator()}
          </div>
        </section>
      )}

      {!hasFinalContent && message.isStreaming && processEntries.length === 0 && (
        <div className="message-content">
          {renderStreamingIndicator()}
        </div>
      )}
    </div>
  )
}
