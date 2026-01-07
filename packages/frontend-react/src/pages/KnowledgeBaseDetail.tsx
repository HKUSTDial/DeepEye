import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { knowledgeBasesApi } from '../api'
import type { KnowledgeBase, KnowledgeBaseFile } from '../types'

export default function KnowledgeBaseDetail() {
  const { kbId } = useParams()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [files, setFiles] = useState<KnowledgeBaseFile[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!kbId) return
    const load = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const kbDetail = await knowledgeBasesApi.get(kbId)
        setKb(kbDetail)
        const fileList = await knowledgeBasesApi.listFiles(kbId)
        setFiles(fileList)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load knowledge base.')
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [kbId])

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!kbId || !event.target.files || event.target.files.length === 0) return
    const file = event.target.files[0]
    setIsUploading(true)
    setError(null)
    try {
      await knowledgeBasesApi.uploadFile(kbId, file)
      const fileList = await knowledgeBasesApi.listFiles(kbId)
      setFiles(fileList)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file.')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDeleteFile = async (fileId: string) => {
    if (!kbId) return
    setError(null)
    try {
      await knowledgeBasesApi.deleteFile(kbId, fileId)
      setFiles((prev) => prev.filter((file) => file.id !== fileId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete file.')
    }
  }

  const totalSize = useMemo(() => files.reduce((acc, file) => acc + (file.size_bytes || 0), 0), [files])

  const filteredFiles = useMemo(() => {
    if (!searchQuery.trim()) return files
    const q = searchQuery.toLowerCase()
    return files.filter((file) => file.filename.toLowerCase().includes(q))
  }, [files, searchQuery])

  const getFileExtension = (filename: string) => {
    const parts = filename.split('.')
    return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : 'FILE'
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'pdf':
        return '📄'
      case 'doc':
      case 'docx':
        return '📝'
      case 'txt':
        return '📃'
      case 'md':
        return '📋'
      default:
        return '📄'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex h-screen bg-slate-950 text-white overflow-hidden"
    >
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-800 px-6 py-4">
          <button
            onClick={() => navigate('/knowledge-bases')}
            className="text-xs text-slate-400 hover:text-slate-200 mb-3 flex items-center gap-1"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Knowledge Bases
          </button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold">{kb?.name || 'Knowledge Base'}</h1>
              <p className="text-sm text-slate-400 mt-1">{kb?.description || 'No description'}</p>
            </div>
          </div>
        </div>

        {/* Toolbar */}
        <div className="border-b border-slate-800 px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-700 bg-slate-900/60 text-sm focus:outline-none focus:border-slate-600"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-4 text-xs text-slate-400 px-4 py-2 rounded-lg border border-slate-800 bg-slate-900/40">
              <div className="flex items-center gap-2">
                <span className="text-slate-500">Files:</span>
                <span className="text-slate-200 font-medium">{files.length}</span>
              </div>
              <div className="w-px h-4 bg-slate-700"></div>
              <div className="flex items-center gap-2">
                <span className="text-slate-500">Size:</span>
                <span className="text-slate-200 font-medium">{(totalSize / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="px-4 py-2 rounded-lg bg-blue-600 text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {isUploading ? 'Uploading...' : 'Upload Document'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleUpload}
              className="hidden"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-sm text-slate-400">Loading documents...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-sm text-rose-400">{error}</div>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
              {/* Table Header */}
              <div className="grid grid-cols-12 gap-4 px-6 py-4 text-xs font-medium text-slate-400 border-b border-slate-800 bg-slate-900/60">
                <div className="col-span-5">Document Name</div>
                <div className="col-span-2">Type</div>
                <div className="col-span-1">Size</div>
                <div className="col-span-2">Status</div>
                <div className="col-span-2 text-right">Actions</div>
              </div>
              
              {/* Table Body */}
              {filteredFiles.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 px-6">
                  <svg className="w-16 h-16 text-slate-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <p className="text-sm text-slate-400 mb-1">
                    {searchQuery.trim() ? 'No documents found' : 'No documents uploaded yet'}
                  </p>
                  <p className="text-xs text-slate-500">
                    {searchQuery.trim() ? 'Try a different search term' : 'Upload your first document to get started'}
                  </p>
                </div>
              ) : (
                filteredFiles.map((file, index) => (
                  <div
                    key={file.id}
                    className={`grid grid-cols-12 gap-4 px-6 py-4 text-sm hover:bg-slate-900/60 transition-colors ${
                      index < filteredFiles.length - 1 ? 'border-b border-slate-800/60' : ''
                    }`}
                  >
                    <div className="col-span-5 flex items-center gap-3 min-w-0">
                      <span className="text-2xl flex-shrink-0">{getFileIcon(file.filename)}</span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium text-slate-200">{file.filename}</div>
                        {file.error && (
                          <div className="text-xs text-rose-400 mt-0.5 truncate">{file.error}</div>
                        )}
                      </div>
                    </div>
                    <div className="col-span-2 flex items-center">
                      <span className="px-2 py-1 rounded text-xs font-medium bg-slate-800 text-slate-300">
                        {getFileExtension(file.filename)}
                      </span>
                    </div>
                    <div className="col-span-1 flex items-center text-slate-400">
                      {file.size_bytes >= 1024 * 1024
                        ? `${(file.size_bytes / 1024 / 1024).toFixed(1)} MB`
                        : `${(file.size_bytes / 1024).toFixed(1)} KB`}
                    </div>
                    <div className="col-span-2 flex items-center">
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                          file.status === 'ready'
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : file.status === 'processing'
                            ? 'bg-amber-500/10 text-amber-400'
                            : file.status === 'failed'
                            ? 'bg-rose-500/10 text-rose-400'
                            : 'bg-slate-500/10 text-slate-400'
                        }`}
                      >
                        {file.status.charAt(0).toUpperCase() + file.status.slice(1)}
                      </span>
                    </div>
                    <div className="col-span-2 flex items-center justify-end gap-2">
                      <span className="text-xs text-slate-500">
                        {new Date(file.updated_at).toLocaleDateString()}
                      </span>
                      <button
                        onClick={() => handleDeleteFile(file.id)}
                        className="p-1.5 rounded hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors"
                        title="Delete"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
