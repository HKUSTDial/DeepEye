import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { createReportProgressLine, parseChatProgressLine, type ChatProgressLine } from '../utils/chatProgress'
import type { Message } from '../types'
import StepItem from './StepItem'
import { hasText } from './chatBoxUtils'

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
  const timeline = message.timeline && message.timeline.length > 0 ? message.timeline : null

  if (timeline) {
    return (
      <div className="assistant-timeline">
        {timeline.map((item, index) => {
          if (item.kind === 'step') {
            return <StepItem key={`timeline-step-${index}`} step={item.step} />
          }
          if (item.kind === 'report_step') {
            return renderProgressLine(
              createReportProgressLine(item.stepIndex, item.totalSteps, item.label),
              `timeline-report-${index}`,
            )
          }
          if (item.kind === 'text') {
            const progress = parseChatProgressLine(item.content || '')
            if (progress) {
              return renderProgressLine(progress, `timeline-progress-${index}`)
            }
          }
          return (
            <div key={`timeline-text-${index}`} className="message-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content || ''}</ReactMarkdown>
              {item.isStreaming && hasText(item.content) && renderStreamingIndicator()}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <>
      {message.steps && message.steps.length > 0 && (
        <div className="space-y-2 mb-3">
          {message.steps.map((step, index) => (
            <StepItem key={`step-${index}`} step={step} />
          ))}
        </div>
      )}
      {(message.content || message.isStreaming) && (
        <div className="message-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ''}</ReactMarkdown>
          {message.isStreaming && hasText(message.content) && renderStreamingIndicator()}
        </div>
      )}
    </>
  )
}
