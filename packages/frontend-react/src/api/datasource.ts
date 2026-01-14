import type { DataSource, DataSourceCreate } from '../types'
import { http } from './client'

export const datasourceApi = {
  list: () => http.get<DataSource[]>('/datasources'),
  create: (data: DataSourceCreate) => http.post<DataSource>('/datasources', data),
  delete: (id: string) => http.delete<void>(`/datasources/${id}`),
  upload: (file: File, sessionId?: string | null) => {
    const formData = new FormData()
    formData.append('file', file)
    const url = sessionId ? `/datasources/upload?session_id=${sessionId}` : '/datasources/upload'
    return http.post<DataSource>(url, formData)
  },
}

