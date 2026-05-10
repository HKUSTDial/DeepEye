import { Database, Sparkles } from 'lucide-react'

interface StarterPrompt {
  label: string
  description: string
  prompt: string
}

interface ChatEmptyStateProps {
  dataSourceCount: number
  emptyTitle: string
  emptySubtitle: string
  sourceStatusText: string
  contextChips: string[]
  starterPrompts: StarterPrompt[]
  addDataLabel: string
  addDataDescription: string
  onOpenDataSourceManager?: () => void
  onApplyStarterPrompt: (prompt: string) => void
}

export function ChatEmptyState({
  dataSourceCount,
  emptyTitle,
  emptySubtitle,
  sourceStatusText,
  contextChips,
  starterPrompts,
  addDataLabel,
  addDataDescription,
  onOpenDataSourceManager,
  onApplyStarterPrompt,
}: ChatEmptyStateProps) {
  return (
    <div className="chat-empty">
      <svg className="chat-empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
        />
      </svg>
      <h2 className="chat-empty-title">{emptyTitle}</h2>
      <p className="chat-empty-subtitle">{emptySubtitle}</p>
      {dataSourceCount === 0 && onOpenDataSourceManager && (
        <button
          type="button"
          className="chat-empty-primary-action"
          onClick={onOpenDataSourceManager}
        >
          <span className="chat-empty-primary-icon" aria-hidden="true">
            <Database className="h-4 w-4" />
          </span>
          <span className="chat-empty-primary-copy">
            <span className="chat-empty-primary-title">{addDataLabel}</span>
            <span className="chat-empty-primary-desc">{addDataDescription}</span>
          </span>
          <Sparkles className="chat-empty-primary-spark h-4 w-4" aria-hidden="true" />
        </button>
      )}
      <div className={`chat-empty-status ${dataSourceCount > 0 ? 'is-active' : ''}`}>
        <span className="chat-empty-status-dot" aria-hidden="true"></span>
        <span>{sourceStatusText}</span>
      </div>
      <div className="chat-empty-context">
        {contextChips.map((chip) => (
          <span key={chip} className={`chat-empty-context-chip ${dataSourceCount > 0 ? 'active' : ''}`}>
            {chip}
          </span>
        ))}
      </div>
      <div className="chat-empty-prompts">
        {starterPrompts.map((item) => (
          <button
            key={item.label}
            type="button"
            className="chat-empty-prompt"
            onClick={() => onApplyStarterPrompt(item.prompt)}
          >
            <span className="chat-empty-prompt-copy">
              <span className="chat-empty-prompt-title">{item.label}</span>
              <span className="chat-empty-prompt-desc">{item.description}</span>
            </span>
            <span className="chat-empty-prompt-arrow" aria-hidden="true">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 17 17 7M9 7h8v8" />
              </svg>
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
