import type { DatasourcePreviewResponse } from '../../api'
import type { DataSource } from '../../types'
import { useLocale } from '../../locale'
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
  const { t } = useLocale()

  return (
    <div className="data-source-subpanel data-source-preview-shell" onClick={(event) => event.stopPropagation()}>
      {isLoading && !preview ? (
        <div className="data-source-preview-state">
          <div className="data-source-spinner" />
          <span>{t('datasource.loadingPreview')}</span>
        </div>
      ) : preview ? (
        <>
          <div className="data-source-preview-toolbar">
            <div className="data-source-preview-summary">
              <span className="data-source-subpanel-note">
                {preview.table
                  ? t('datasource.previewSummary', {
                      table: preview.table,
                      columns: preview.columns.length,
                      rows: preview.total_rows,
                    })
                  : t('datasource.noPreviewableTables')}
              </span>
              {isLoading && (
                <span className="data-source-preview-loading-inline">
                  <div className="data-source-spinner is-small" />
                  <span>{t('datasource.refreshing')}</span>
                </span>
              )}
            </div>
            <span className="data-source-preview-page-badge">{t('datasource.rowsPerPage', { count: preview.page_size })}</span>
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
                          {t('datasource.noDataOnPage')}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="data-source-preview-footer">
                <span className="data-source-subpanel-note">
                  {t('datasource.rowsRange', { range: getPreviewRangeLabel(preview) })}
                </span>
                <div className="data-source-preview-pagination">
                  <button
                    type="button"
                    className="data-source-preview-page-btn"
                    onClick={() => onChangePage(preview.page - 1)}
                    disabled={isLoading || preview.page <= 1}
                  >
                    {t('common.previous')}
                  </button>
                  <span className="data-source-preview-page-text">
                    {t('datasource.pageOf', {
                      page: preview.total_pages === 0 ? 0 : preview.page,
                      total: preview.total_pages || 0,
                    })}
                  </span>
                  <button
                    type="button"
                    className="data-source-preview-page-btn"
                    onClick={() => onChangePage(preview.page + 1)}
                    disabled={isLoading || preview.total_pages === 0 || preview.page >= preview.total_pages}
                  >
                    {t('common.next')}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="data-source-preview-state is-empty">
              <span>{t('datasource.noPreviewableData')}</span>
            </div>
          )}
        </>
      ) : (
        <div className="data-source-preview-state is-empty">
          <span>{t('datasource.clickPreview')}</span>
        </div>
      )}
    </div>
  )
}
