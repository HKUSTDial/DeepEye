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

  startSession: (sessionId: string) =>
    http.post<{ status: string; message?: string }>(`/sandbox/sessions/${sessionId}/start`),
  
  // Returns download URL for file/directory (uses full API base URL)
  getDownloadUrl: (sessionId: string, path: string) => 
    `${API_BASE}/sandbox/files/sessions/${sessionId}/download?path=${encodeURIComponent(path)}`,

  download: async (sessionId: string, path: string) => {
    const res = await http.getResponse(
      `/sandbox/files/sessions/${sessionId}/download?path=${encodeURIComponent(path)}`,
    )

    const disposition = res.headers.get('content-disposition') || res.headers.get('Content-Disposition')
    // Prefer RFC 5987 filename* (UTF-8''...) to preserve non-ascii filenames (e.g. Chinese).
    const matchStar = disposition?.match(/filename\*\s*=\s*UTF-8''([^;]+)/i)
    const starFilename = matchStar?.[1] ? decodeURIComponent(matchStar[1].trim()) : undefined

    // Fallback to plain filename="..."
    const matchPlain = disposition?.match(/filename\s*=\s*"([^"]+)"/i) || disposition?.match(/filename\s*=\s*([^;]+)/i)
    const plainFilename = matchPlain?.[1]?.trim()

    const headerFilename = starFilename || plainFilename
    const fallbackFilename = path.replace(/\/+$/, '').split('/').pop() || 'download'
    const filename = headerFilename || fallbackFilename

    const blob = await res.blob()
    return { blob, filename }
  },
}

