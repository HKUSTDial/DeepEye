import { deriveChatErrorState } from '../utils/chatErrorState'

interface ChatErrorNoticeProps {
  error: string
  canRetry: boolean
  canOpenWorkflow?: boolean
  canOpenData?: boolean
  onRetry: () => void
  onOpenWorkflow: () => void
  onOpenData: () => void
}

export function ChatErrorNotice({
  error,
  canRetry,
  canOpenWorkflow = true,
  canOpenData = true,
  onRetry,
  onOpenWorkflow,
  onOpenData,
}: ChatErrorNoticeProps) {
  const state = deriveChatErrorState(error)

  return (
    <div className="chat-error-card" role="alert">
      <div className="chat-error-card-kicker">Needs attention</div>
      <div className="chat-error-card-title">{state.title}</div>
      <p className="chat-error-card-summary">{state.summary}</p>
      <p className="chat-error-card-suggestion">{state.suggestion}</p>
      <div className="chat-error-card-actions">
        <button
          type="button"
          className="chat-error-card-btn chat-error-card-btn-primary"
          onClick={onRetry}
          disabled={!canRetry}
        >
          Retry
        </button>
        {canOpenData && (
          <button
            type="button"
            className="chat-error-card-btn"
            onClick={onOpenData}
          >
            Check attached data
          </button>
        )}
        {canOpenWorkflow && (
          <button
            type="button"
            className="chat-error-card-btn"
            onClick={onOpenWorkflow}
          >
            Open workflow
          </button>
        )}
      </div>
      <details className="chat-error-card-details">
        <summary>Show technical details</summary>
        <pre>{error}</pre>
      </details>
    </div>
  )
}
