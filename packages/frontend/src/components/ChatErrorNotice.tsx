import { deriveChatErrorState } from '../utils/chatErrorState'
import { useLocale } from '../locale'

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
  const { locale, t } = useLocale()
  const state = deriveChatErrorState(error, locale)

  return (
    <div className="chat-error-card" role="alert">
      <div className="chat-error-card-kicker">{t('common.needsAttention')}</div>
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
          {t('common.retry')}
        </button>
        {canOpenData && (
          <button
            type="button"
            className="chat-error-card-btn"
            onClick={onOpenData}
          >
            {t('common.checkAttachedData')}
          </button>
        )}
        {canOpenWorkflow && (
          <button
            type="button"
            className="chat-error-card-btn"
            onClick={onOpenWorkflow}
          >
            {t('common.openWorkflow')}
          </button>
        )}
      </div>
      <details className="chat-error-card-details">
        <summary>{t('common.showTechnicalDetails')}</summary>
        <pre>{error}</pre>
      </details>
    </div>
  )
}
