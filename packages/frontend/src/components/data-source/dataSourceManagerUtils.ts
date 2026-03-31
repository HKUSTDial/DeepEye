import type { DatasourcePreviewResponse } from '../../api'
import type { DataSourceConnectionTestResponse } from '../../types'

export const ENGINE_OPTIONS = [
  { value: 'postgres', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'sqlite', label: 'SQLite' },
] as const

export const URI_EXAMPLES: Record<string, string> = {
  postgres: 'postgresql://user:password@localhost:5432/analytics',
  mysql: 'mysql://user:password@localhost:3306/analytics',
  sqlite: 'sqlite:////absolute/path/to/analytics.db',
}

export const PREVIEW_PAGE_SIZE = 25

export const isSupportedFile = (file: File) => {
  const name = file.name.toLowerCase()
  return (
    name.endsWith('.csv') ||
    name.endsWith('.json') ||
    name.endsWith('.xlsx') ||
    name.endsWith('.xls') ||
    name.endsWith('.parquet')
  )
}

export const formatPreviewCell = (value: unknown) => {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

export const getPreviewRangeLabel = (preview: DatasourcePreviewResponse) => {
  if (preview.total_rows === 0) {
    return '0 / 0'
  }
  const start = (preview.page - 1) * preview.page_size + 1
  const end = Math.min(preview.page * preview.page_size, preview.total_rows)
  return `${start}-${end} / ${preview.total_rows}`
}

export const formatConnectionSuccess = (result: DataSourceConnectionTestResponse) => {
  const sample = result.sample_tables.slice(0, 3).join(', ')
  return result.table_count > 0
    ? `Connection successful. ${result.table_count} table(s) available. Sample: ${sample || 'none'}`
    : 'Connection successful, but no accessible tables were found in this database.'
}
