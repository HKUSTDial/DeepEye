import type { DataSource, DataSourceCreate, DataSourceUpdate } from '../types'
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

export const datasourceApi = {
  list: () => http.get<DataSource[]>('/datasources'),
  create: (data: DataSourceCreate, sessionId?: string | null) => {
    const url = sessionId ? `/datasources?session_id=${sessionId}` : '/datasources'
    return http.post<DataSource>(url, data)
  },
  update: (id: string, data: DataSourceUpdate) => http.patch<DataSource>(`/datasources/${id}`, data),
  tables: (id: string) => http.get<DatasourceTablesResponse>(`/datasources/${id}/tables`),
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
