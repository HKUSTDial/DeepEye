import type { DataSource } from '../../types'
import { translateApp } from '../../locale'

type OutputRecord = Record<string, unknown>
type DatasetRefOutput = OutputRecord & {
  kind?: string
  path?: string
  format?: string
  name?: string
  source?: string
  row_count?: number
  columns?: unknown
  preview_rows?: unknown
}

export type { OutputRecord, DatasetRefOutput }

export function stringifyParams(params: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(Object.entries(params).map(([key, value]) => [key, String(value)]))
}

export function asObjectRecord(value: unknown): OutputRecord | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as OutputRecord) : null
}

export function asObjectArray(value: unknown): OutputRecord[] | null {
  if (!Array.isArray(value) || value.length === 0) {
    return null
  }
  return value.every((item) => item && typeof item === 'object' && !Array.isArray(item))
    ? (value as OutputRecord[])
    : null
}

export function isDatasetRefOutput(value: unknown): value is DatasetRefOutput {
  const record = asObjectRecord(value)
  return !!record && record.kind === 'dataset_ref' && typeof record.path === 'string'
}

export function formatOutputLabel(key: string): string {
  return key.replace(/[_.-]+/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

export function formatScalarValue(value: unknown): string {
  if (value == null) return 'N/A'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value, null, 2)
}

export function formatDatasetMetaValue(value: unknown): string | null {
  if (typeof value === 'number') return `${value}`
  if (typeof value === 'string' && value.trim()) return value
  return null
}

export function getDatasetPreviewRows(datasetRef: DatasetRefOutput): OutputRecord[] {
  const rows = asObjectArray(datasetRef.preview_rows)
  return rows ? rows.slice(0, 8) : []
}

export function getPreviewColumns(rows: OutputRecord[]): string[] {
  const seen = new Set<string>()
  const columns: string[] = []
  rows.forEach((row) => {
    Object.keys(row).forEach((column) => {
      if (!seen.has(column)) {
        seen.add(column)
        columns.push(column)
      }
    })
  })
  return columns.slice(0, 8)
}

export function getDatasourceCategoryForNodeType(
  nodeType: string | undefined,
): DataSource['category'] | null {
  switch (nodeType) {
    case 'datasource.read':
      return 'file'
    case 'sql.execute':
      return 'database'
    default:
      return null
  }
}

export function getDatasourcePlaceholder(category: DataSource['category'] | null): string {
  if (category === 'file') {
    return translateApp('workflowInspector.selectFileDatasource')
  }
  if (category === 'database') {
    return translateApp('workflowInspector.selectDatabaseDatasource')
  }
  return translateApp('workflowInspector.selectDatasource')
}

export function getEmptyDatasourceMessage(category: DataSource['category'] | null): string {
  if (category === 'file') {
    return translateApp('workflowInspector.noFileDatasources')
  }
  if (category === 'database') {
    return translateApp('workflowInspector.noDatabaseDatasources')
  }
  return translateApp('workflowInspector.noDatasources')
}

export function formatDatasourceOptionLabel(datasource: DataSource): string {
  const compactName =
    datasource.name.length > 28 ? `${datasource.name.slice(0, 27)}...` : datasource.name
  return `${compactName} · ${datasource.category === 'file' ? translateApp('workflowInspector.fileBadge') : translateApp('workflowInspector.dbBadge')}`
}

export function isMultilineParam(nodeType: string | undefined, key: string): boolean {
  if (!nodeType) return false
  if (nodeType === 'python.code' && key === 'code') return true
  if (nodeType === 'sql.execute' && key === 'query') return true
  if (key === 'question') return true
  if (key === 'prompt') return true
  if (key === 'system_prompt') return true
  if (key === 'user_prompt') return true
  return false
}

export function getStatusClass(status: string): string {
  switch (status) {
    case 'running':
      return 'running'
    case 'success':
    case 'completed':
      return 'success'
    case 'failed':
      return 'failed'
    case 'pending':
      return 'pending'
    default:
      return ''
  }
}
