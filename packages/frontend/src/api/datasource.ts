import type { DataSource, DataSourceCreate } from '../types'
import { http } from './client'

export const datasourceApi = {
  list: () => http.get<DataSource[]>('/datasources'),
  create: (data: DataSourceCreate) => http.post<DataSource>('/datasources', data),
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

