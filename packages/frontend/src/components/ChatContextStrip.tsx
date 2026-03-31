import type { DataSource } from '../types'

interface ChatContextStripProps {
  dataSources: DataSource[]
  isLoading?: boolean
  isCompact?: boolean
  removingDataSourceId?: string | null
  onOpenManager: () => void
  onRemoveDataSource: (dataSourceId: string) => void | Promise<void>
}

function formatDatasourceKind(source: DataSource) {
  if (source.category === 'file') {
    return 'File'
  }
  if (source.type) {
    return source.type.toUpperCase()
  }
  return 'Database'
}

export function ChatContextStrip({
  dataSources,
  isLoading = false,
  isCompact = false,
  removingDataSourceId = null,
  onOpenManager,
  onRemoveDataSource,
}: ChatContextStripProps) {
  const count = dataSources.length
  const helper = count > 0
    ? 'This thread uses the attached data automatically.'
    : 'Attach files or databases once, then ask directly in chat.'

  return (
    <div className={`chat-context-strip ${isCompact ? 'is-compact' : ''}`}>
      <div className="chat-context-strip-header">
        <div className="chat-context-strip-copy">
          <span className="chat-context-strip-kicker">Attached data</span>
          <span className="chat-context-strip-helper">{helper}</span>
        </div>
        <button
          type="button"
          className="chat-context-strip-manage"
          onClick={onOpenManager}
        >
          {count > 0 ? 'Manage' : 'Add data'}
        </button>
      </div>

      {isLoading ? (
        <div className="chat-context-strip-empty">Loading attached data…</div>
      ) : count > 0 ? (
        <div className="chat-context-strip-list">
          {dataSources.map((source) => {
            const isRemoving = removingDataSourceId === source.id
            return (
              <div key={source.id} className="chat-context-chip">
                <span className="chat-context-chip-copy">
                  <span className="chat-context-chip-title">{source.name}</span>
                  <span className="chat-context-chip-kind">{formatDatasourceKind(source)}</span>
                </span>
                <button
                  type="button"
                  className="chat-context-chip-remove"
                  onClick={() => onRemoveDataSource(source.id)}
                  disabled={isRemoving}
                  aria-label={`Remove ${source.name} from this thread`}
                  title={`Remove ${source.name} from this thread`}
                >
                  {isRemoving ? '…' : '×'}
                </button>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="chat-context-strip-empty">
          No data attached yet. Use files or databases to ground the next reply.
        </div>
      )}
    </div>
  )
}
