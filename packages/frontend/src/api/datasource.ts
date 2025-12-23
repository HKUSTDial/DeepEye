import type { DataSource, DataSourceCreate } from '../types'
import { http } from './client'

export const datasourceApi = {
  list: () => http.get<DataSource[]>('/datasources'),
  create: (data: DataSourceCreate) => http.post<DataSource>('/datasources', data),
  delete: (id: string) => http.delete<void>(`/datasources/${id}`),
}
