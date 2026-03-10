import type { DataSource, DataSourceConnectionTestResponse, DataSourceCreate, DataSourceUpdate } from '../types'
import { http } from './client'

export interface DatasourceTable {
  name: string
  columns: { name: string; type: string }[]
}

export interface DatasourceTablesResponse {
  datasource_id: string
  datasource_name: string
  tables: DatasourceTable[]
}

export interface DatasourcePreviewTable {
  name: string
}

export interface DatasourcePreviewColumn {
  name: string
  type: string
}

export interface DatasourcePreviewResponse {
  datasource_id: string
  datasource_name: string
  category: 'database' | 'file'
  tables: DatasourcePreviewTable[]
  table: string | null
  columns: DatasourcePreviewColumn[]
  rows: Array<Record<string, unknown>>
  page: number
  page_size: number
  total_rows: number
  total_pages: number
}

export const datasourceApi = {
  list: () => http.get<DataSource[]>('/datasources'),
  create: (data: DataSourceCreate, sessionId?: string | null) => {
    const url = sessionId ? `/datasources?session_id=${sessionId}` : '/datasources'
    return http.post<DataSource>(url, data)
  },
  testConnection: (data: Pick<DataSourceCreate, 'type' | 'connection_string'>) =>
    http.post<DataSourceConnectionTestResponse>('/datasources/test-connection', data),
  update: (id: string, data: DataSourceUpdate) => http.patch<DataSource>(`/datasources/${id}`, data),
  tables: (id: string) => http.get<DatasourceTablesResponse>(`/datasources/${id}/tables`),
  preview: (id: string, params?: { table?: string | null; page?: number; pageSize?: number }) => {
    const query = new URLSearchParams()
    if (params?.table) query.set('table', params.table)
    if (params?.page) query.set('page', String(params.page))
    if (params?.pageSize) query.set('page_size', String(params.pageSize))
    const suffix = query.toString()
    return http.get<DatasourcePreviewResponse>(`/datasources/${id}/preview${suffix ? `?${suffix}` : ''}`)
  },
  delete: (id: string, sessionId?: string | null) => {
    const url = sessionId ? `/datasources/${id}?session_id=${sessionId}` : `/datasources/${id}`
    return http.delete<void>(url)
  },
  upload: (file: File, sessionId?: string | null) => {
    const formData = new FormData()
    formData.append('file', file)
    const url = sessionId ? `/datasources/upload?session_id=${sessionId}` : '/datasources/upload'
    return http.post<DataSource>(url, formData)
  },
}
