import { ArrowUpRight, Workflow as WorkflowIcon } from 'lucide-react'
import { useLocale } from '../../../locale'

export function WorkflowLiveEmptyState({ dataSourceCount }: { dataSourceCount: number }) {
  const { t } = useLocale()
  const hasDataSources = dataSourceCount > 0

  return (
    <div className="right-panel-empty">
      <div className="right-panel-empty-kicker">{t('workflow.toolbarLabel')}</div>
      <WorkflowIcon className="right-panel-empty-icon" />
      <h3 className="right-panel-empty-title">
        {hasDataSources ? t('workflow.emptyTitleReady') : t('workflow.emptyTitleNoData')}
      </h3>
      <p className="right-panel-empty-subtitle">
        {hasDataSources
          ? t('workflow.emptySubtitleReady', { count: dataSourceCount })
          : t('workflow.emptySubtitleNoData')}
      </p>

      {hasDataSources && (
        <div className="panel-empty-suggestions">
          {[
            t('workflow.emptySuggestion1'),
            t('workflow.emptySuggestion2'),
            t('workflow.emptySuggestion3'),
          ].map((suggestion) => (
            <div key={suggestion} className="panel-empty-suggestion">
              <span className="panel-empty-suggestion-label">"{suggestion}"</span>
              <span className="panel-empty-suggestion-arrow">
                <ArrowUpRight size={13} />
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
