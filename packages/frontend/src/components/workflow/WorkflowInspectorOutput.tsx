import {
  asObjectArray,
  asObjectRecord,
  formatDatasetMetaValue,
  formatOutputLabel,
  formatScalarValue,
  getDatasetPreviewRows,
  getPreviewColumns,
  isDatasetRefOutput,
  type OutputRecord,
} from './workflowInspectorUtils'
import { useLocale } from '../../locale'

export function WorkflowInspectorOutputView({
  output,
  rawOutput,
}: {
  output: OutputRecord
  rawOutput: string
}) {
  const { t } = useLocale()
  const entries = Object.entries(output).filter(([key]) => key !== 'status')
  const hasFriendlySections = entries.length > 0

  return (
    <div className="workflow-inspector-output-stack">
      {hasFriendlySections ? (
        entries.map(([key, value]) => (
          <WorkflowInspectorOutputSection key={key} label={formatOutputLabel(key)} value={value} />
        ))
      ) : (
        <div className="workflow-inspector-output-empty">
          {t('workflowInspector.noMaterialOutput')}
        </div>
      )}

      <details className="workflow-inspector-output-raw">
        <summary>{t('workflowInspector.rawJson')}</summary>
        <pre className="workflow-inspector-output-content">{rawOutput}</pre>
      </details>
    </div>
  )
}

function WorkflowInspectorOutputSection({ label, value }: { label: string; value: unknown }) {
  const { t } = useLocale()
  if (isDatasetRefOutput(value)) {
    const previewRows = getDatasetPreviewRows(value)
    const previewColumns = getPreviewColumns(previewRows)
    const datasetColumns = Array.isArray(value.columns)
      ? value.columns.filter((column): column is string => typeof column === 'string').slice(0, 8)
      : []

    return (
      <div className="workflow-inspector-output-card">
        <div className="workflow-inspector-output-card-title">{label}</div>

        <div className="workflow-inspector-output-metrics">
          {[
            [t('workflowInspector.rows'), formatDatasetMetaValue(value.row_count)],
            [t('workflowInspector.format'), formatDatasetMetaValue(value.format)?.toUpperCase() ?? null],
            [t('workflowInspector.source'), formatDatasetMetaValue(value.source)],
            [t('workflowInspector.name'), formatDatasetMetaValue(value.name)],
          ]
            .filter(([, metricValue]) => !!metricValue)
            .map(([metricLabel, metricValue]) => (
              <div key={metricLabel} className="workflow-inspector-output-metric">
                <span className="workflow-inspector-output-metric-label">{metricLabel}</span>
                <span className="workflow-inspector-output-metric-value">{metricValue}</span>
              </div>
            ))}
        </div>

        {datasetColumns.length > 0 && (
          <div className="workflow-inspector-output-chip-list">
            {datasetColumns.map((column) => (
              <span key={column} className="workflow-inspector-output-chip">
                {column}
              </span>
            ))}
          </div>
        )}

        {previewRows.length > 0 && previewColumns.length > 0 && (
          <div className="workflow-inspector-output-table-shell">
            <table className="workflow-inspector-output-table">
              <thead>
                <tr>
                  {previewColumns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, index) => (
                  <tr key={`${label}-${index}`}>
                    {previewColumns.map((column) => (
                      <td key={`${index}-${column}`}>{formatScalarValue(row[column])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  const rows = asObjectArray(value)
  if (rows) {
    const previewColumns = getPreviewColumns(rows.slice(0, 8))
    return (
      <div className="workflow-inspector-output-card">
        <div className="workflow-inspector-output-card-title">{label}</div>
        <div className="workflow-inspector-output-table-shell">
          <table className="workflow-inspector-output-table">
            <thead>
              <tr>
                {previewColumns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 8).map((row, index) => (
                <tr key={`${label}-${index}`}>
                  {previewColumns.map((column) => (
                    <td key={`${index}-${column}`}>{formatScalarValue(row[column])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  const objectValue = asObjectRecord(value)
  if (objectValue) {
    return (
      <div className="workflow-inspector-output-card">
        <div className="workflow-inspector-output-card-title">{label}</div>
        <div className="workflow-inspector-output-kv">
          {Object.entries(objectValue).map(([entryKey, entryValue]) => (
            <div key={entryKey} className="workflow-inspector-output-kv-row">
              <span className="workflow-inspector-output-kv-key">{formatOutputLabel(entryKey)}</span>
              <span className="workflow-inspector-output-kv-value">
                {formatScalarValue(entryValue)}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="workflow-inspector-output-card">
      <div className="workflow-inspector-output-card-title">{label}</div>
      <div className="workflow-inspector-output-text">{formatScalarValue(value)}</div>
    </div>
  )
}
