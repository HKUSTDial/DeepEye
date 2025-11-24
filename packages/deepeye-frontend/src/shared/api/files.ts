import { apiClient } from './client'

export interface StoredFile {
  id: string
  filename: string
  original_name: string
  content_type?: string | null
  size: number
  created_at: string
  updated_at: string
}

export interface FileDownloadResponse {
  url: string
}

export const filesAPI = {
  list: (skip = 0, limit = 100) =>
    apiClient.get<StoredFile[]>('/files', { skip, limit }),

  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    return apiClient.request<StoredFile>('/files/upload', {
      method: 'POST',
      body: formData,
    })
  },

  delete: (id: string) => apiClient.delete<void>(`/files/${id}`),

  getDownloadUrl: (id: string) =>
    apiClient.get<FileDownloadResponse>(`/files/${id}/download`),
}


