import { API_BASE, ApiError } from './client'
import { useAuthStore } from '../stores/auth'
import type { KnowledgeBase, KnowledgeBaseFile } from '../types'

type KnowledgeBaseCreate = {
  name: string
  description?: string | null
}

type KnowledgeBaseUpdate = {
  name?: string | null
  description?: string | null
}

type KnowledgeBaseSearchResult = {
  file_id: string
  filename: string
  chunk_index: number
  content: string
}

const authHeaders = (): Record<string, string> => {
  const token = useAuthStore.getState().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const knowledgeBasesApi = {
  list: async (): Promise<KnowledgeBase[]> => {
    const res = await fetch(`${API_BASE}/knowledge-bases`, {
      headers: { ...authHeaders() },
      credentials: 'include',
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to load knowledge bases')
    return res.json()
  },
  get: async (id: string): Promise<KnowledgeBase> => {
    const res = await fetch(`${API_BASE}/knowledge-bases/${id}`, {
      headers: { ...authHeaders() },
      credentials: 'include',
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to load knowledge base')
    return res.json()
  },
  create: async (payload: KnowledgeBaseCreate): Promise<KnowledgeBase> => {
    const res = await fetch(`${API_BASE}/knowledge-bases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
      credentials: 'include',
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to create knowledge base')
    return res.json()
  },
  update: async (id: string, payload: KnowledgeBaseUpdate): Promise<KnowledgeBase> => {
    const res = await fetch(`${API_BASE}/knowledge-bases/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
      credentials: 'include',
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to update knowledge base')
    return res.json()
  },
  remove: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/knowledge-bases/${id}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
      credentials: 'include',
    })
    if (!res.ok && res.status !== 204) {
      throw new ApiError(res.status, 'Failed to delete knowledge base')
    }
  },
  listFiles: async (kbId: string): Promise<KnowledgeBaseFile[]> => {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/files`, {
      headers: { ...authHeaders() },
      credentials: 'include',
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to load files')
    return res.json()
  },
  uploadFile: async (kbId: string, file: File): Promise<KnowledgeBaseFile> => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/files`, {
      method: 'POST',
      headers: { ...authHeaders() },
      body: form,
      credentials: 'include',
    })
    if (!res.ok) throw new ApiError(res.status, 'Failed to upload file')
    return res.json()
  },
  deleteFile: async (kbId: string, fileId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/files/${fileId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
      credentials: 'include',
    })
    if (!res.ok && res.status !== 204) {
      throw new ApiError(res.status, 'Failed to delete file')
    }
  },
  search: async (kbId: string, query: string, topK = 5): Promise<KnowledgeBaseSearchResult[]> => {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ query, top_k: topK }),
      credentials: 'include',
    })
    if (!res.ok) throw new ApiError(res.status, 'Search failed')
    return res.json()
  },
}
