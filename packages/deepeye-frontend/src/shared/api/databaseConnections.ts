import { apiClient } from './client'

export interface DatabaseConnection {
  id: string
  user_id: string
  name: string
  type: string
  host: string
  port: number
  username: string
  database: string
  created_at: string
  updated_at: string
}

export interface DatabaseConnectionCreate {
  name: string
  type: string
  host: string
  port: number
  username: string
  password: string
  database: string
}

export interface DatabaseConnectionUpdate {
  name?: string
  type?: string
  host?: string
  port?: number
  username?: string
  password?: string
  database?: string
}

export const databaseConnectionsAPI = {
  list: (skip = 0, limit = 100) =>
    apiClient.get<DatabaseConnection[]>('/database-connections', { skip, limit }),
  create: (data: DatabaseConnectionCreate) =>
    apiClient.post<DatabaseConnection>('/database-connections', data),
  update: (id: string, data: DatabaseConnectionUpdate) =>
    apiClient.put<DatabaseConnection>(`/database-connections/${id}`, data),
  delete: (id: string) => apiClient.delete<void>(`/database-connections/${id}`),
}


