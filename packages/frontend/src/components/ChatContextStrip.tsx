import type { DataSource } from '../types'
import { useLocale } from '../locale'

interface ChatContextStripProps {
  dataSources: DataSource[]
  isLoading?: boolean
  isCompact?: boolean
  removingDataSourceId?: string | null
  onOpenManager: () => void
  onRemoveDataSource: (dataSourceId: string) => void | Promise<void>
}

function formatDatasourceKind(source: DataSource, fileLabel: string, databaseLabel: string) {
  if (source.category === 'file') {
    return fileLabel
  }
  if (source.type) {
    return source.type.toUpperCase()
  }
  return databaseLabel
}

export function ChatContextStrip({
  dataSources,
  isLoading = false,
  isCompact = false,
  removingDataSourceId = null,
  onOpenManager,
  onRemoveDataSource,
}: ChatContextStripProps) {
  const { t } = useLocale()
  const count = dataSources.length
  const helper = count > 0
    ? t('chat.threadUsesAttachedData')
    : t('chat.attachDataFirst')

  return (
    <div className={`chat-context-strip ${isCompact ? 'is-compact' : ''}`}>
      <div className="chat-context-strip-header">
        <div className="chat-context-strip-copy">
          <span className="chat-context-strip-kicker">{t('common.attachedData')}</span>
          <span className="chat-context-strip-helper">{helper}</span>
        </div>
        <button
          type="button"
          className="chat-context-strip-manage"
          onClick={onOpenManager}
        >
          {count > 0 ? t('common.manage') : t('common.addData')}
        </button>
      </div>

      {isLoading ? (
        <div className="chat-context-strip-empty">{t('common.loadingAttachedData')}</div>
      ) : count > 0 ? (
        <div className="chat-context-strip-list">
          {dataSources.map((source) => {
            const isRemoving = removingDataSourceId === source.id
            return (
              <div key={source.id} className="chat-context-chip">
                <span className="chat-context-chip-copy">
                  <span className="chat-context-chip-title">{source.name}</span>
                  <span className="chat-context-chip-kind">
                    {formatDatasourceKind(source, t('datasource.file'), t('datasource.database'))}
                  </span>
                </span>
                <button
                  type="button"
                  className="chat-context-chip-remove"
                  onClick={() => onRemoveDataSource(source.id)}
                  disabled={isRemoving}
                  aria-label={t('common.removeDataFromThread', { name: source.name })}
                  title={t('common.removeDataFromThread', { name: source.name })}
                >
                  {isRemoving ? '…' : '×'}
                </button>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="chat-context-strip-empty">
          {t('common.noDataAttached')}
        </div>
      )}
    </div>
  )
}
