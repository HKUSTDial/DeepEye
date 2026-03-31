import { ArrowUpRight, Workflow as WorkflowIcon } from 'lucide-react'

export function WorkflowLiveEmptyState({ dataSourceCount }: { dataSourceCount: number }) {
  const hasDataSources = dataSourceCount > 0

  return (
    <div className="right-panel-empty">
      <div className="right-panel-empty-kicker">Workflow</div>
      <WorkflowIcon className="right-panel-empty-icon" />
      <h3 className="right-panel-empty-title">
        {hasDataSources ? 'Ready to analyze' : 'Attach data to begin'}
      </h3>
      <p className="right-panel-empty-subtitle">
        {hasDataSources
          ? `You have ${dataSourceCount} attached data source(s). Ask DeepEye to analyze them and the workflow graph will open here.`
          : 'Upload a file or connect a database from the composer to start your first analysis workflow.'}
      </p>

      {hasDataSources && (
        <div className="panel-empty-suggestions">
          {[
            'Show me a summary of the data',
            'Analyze trends over time',
            'Visualize the distribution of key metrics',
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
