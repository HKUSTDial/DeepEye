import type { DatasourcePreviewResponse } from '../../api'
import type { DataSource } from '../../types'
import { formatPreviewCell, getPreviewRangeLabel } from './dataSourceManagerUtils'

interface DataSourcePreviewPanelProps {
  datasource: DataSource
  preview: DatasourcePreviewResponse | undefined
  isLoading: boolean
  onChangeTable: (table: string) => void
  onChangePage: (nextPage: number) => void
}

export function DataSourcePreviewPanel({
  datasource,
  preview,
  isLoading,
  onChangeTable,
  onChangePage,
}: DataSourcePreviewPanelProps) {
  return (
    <div className="data-source-subpanel data-source-preview-shell" onClick={(event) => event.stopPropagation()}>
      {isLoading && !preview ? (
        <div className="data-source-preview-state">
          <div className="data-source-spinner" />
          <span>Loading preview...</span>
        </div>
      ) : preview ? (
        <>
          <div className="data-source-preview-toolbar">
            <div className="data-source-preview-summary">
              <span className="data-source-subpanel-note">
                {preview.table
                  ? `${preview.table} · ${preview.columns.length} columns · ${preview.total_rows} rows`
                  : 'No previewable tables are available for this data source.'}
              </span>
              {isLoading && (
                <span className="data-source-preview-loading-inline">
                  <div className="data-source-spinner is-small" />
                  <span>Refreshing</span>
                </span>
              )}
            </div>
            <span className="data-source-preview-page-badge">{preview.page_size} rows / page</span>
          </div>

          {preview.tables.length > 1 && (
            <div className="data-source-preview-tabs">
              {preview.tables.map((table) => (
                <button
                  key={table.name}
                  type="button"
                  className={`data-source-preview-tab ${preview.table === table.name ? 'is-active' : ''}`}
                  onClick={() => onChangeTable(table.name)}
                  disabled={isLoading && preview.table === table.name}
                >
                  {table.name}
                </button>
              ))}
            </div>
          )}

          {preview.table && preview.columns.length > 0 ? (
            <>
              <div className="data-source-preview-table-shell">
                <table className="data-source-preview-table">
                  <thead>
                    <tr>
                      {preview.columns.map((column) => (
                        <th key={column.name}>
                          <div className="data-source-preview-col">
                            <span className="data-source-preview-col-name">{column.name}</span>
                            {column.type && (
                              <span className="data-source-preview-col-type">{column.type}</span>
                            )}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.length > 0 ? (
                      preview.rows.map((row, rowIndex) => (
                        <tr key={`${preview.table || datasource.id}-${preview.page}-${rowIndex}`}>
                          {preview.columns.map((column) => {
                            const cell = formatPreviewCell(row[column.name])
                            return (
                              <td key={`${column.name}-${rowIndex}`} title={cell}>
                                <span className="data-source-preview-cell">{cell}</span>
                              </td>
                            )
                          })}
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={preview.columns.length} className="data-source-preview-empty-row">
                          No data on this page
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="data-source-preview-footer">
                <span className="data-source-subpanel-note">Rows {getPreviewRangeLabel(preview)}</span>
                <div className="data-source-preview-pagination">
                  <button
                    type="button"
                    className="data-source-preview-page-btn"
                    onClick={() => onChangePage(preview.page - 1)}
                    disabled={isLoading || preview.page <= 1}
                  >
                    Previous
                  </button>
                  <span className="data-source-preview-page-text">
                    Page {preview.total_pages === 0 ? 0 : preview.page} of {preview.total_pages || 0}
                  </span>
                  <button
                    type="button"
                    className="data-source-preview-page-btn"
                    onClick={() => onChangePage(preview.page + 1)}
                    disabled={isLoading || preview.total_pages === 0 || preview.page >= preview.total_pages}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="data-source-preview-state is-empty">
              <span>No previewable data is available for this data source.</span>
            </div>
          )}
        </>
      ) : (
        <div className="data-source-preview-state is-empty">
          <span>Click the preview button to inspect the data.</span>
        </div>
      )}
    </div>
  )
}
