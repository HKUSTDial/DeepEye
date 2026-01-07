import { http, API_BASE } from './client'

export interface FileInfo {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  extension?: string
}

export interface FileContentResponse {
  path: string
  content: string
  content_type: 'text' | 'binary' | 'image'
  encoding: 'utf-8' | 'base64'
}

interface ListFilesResponse {
  session_id: string
  files: FileInfo[]
}

export const sandboxApi = {
  listFiles: (sessionId: string, path: string = '/workspace') => 
    http.get<ListFilesResponse>(`/sandbox/files/sessions/${sessionId}/list?path=${encodeURIComponent(path)}`),
  
  getFileContent: (sessionId: string, path: string) => 
    http.get<FileContentResponse>(`/sandbox/files/sessions/${sessionId}/content?path=${encodeURIComponent(path)}`),
  
  writeFile: (sessionId: string, path: string, content: string) => 
    http.post<void>(`/sandbox/files/sessions/${sessionId}/write`, { path, content }),
  
  deleteFile: (sessionId: string, path: string) => 
    http.delete<void>(`/sandbox/files/sessions/${sessionId}/delete?path=${encodeURIComponent(path)}`),
  
  // Returns download URL for file/directory (uses full API base URL)
  getDownloadUrl: (sessionId: string, path: string) => 
    `${API_BASE}/sandbox/files/sessions/${sessionId}/download?path=${encodeURIComponent(path)}`,
}

