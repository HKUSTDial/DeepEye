import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { BookOpen, FileText, Folder } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { knowledgeBasesApi } from '../api'
import type { KnowledgeBase, KnowledgeBaseFile } from '../types'
import './KnowledgeBaseDetail.css'

export default function KnowledgeBaseDetail() {
  const { kbId } = useParams()
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [files, setFiles] = useState<KnowledgeBaseFile[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
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

  const visibleFiles = useMemo(() => {
    if (statusFilter === 'all') return filteredFiles
    return filteredFiles.filter((file) => file.status === statusFilter)
  }, [filteredFiles, statusFilter])

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'pdf':
        return <FileText size={18} />
      case 'doc':
      case 'docx':
        return <FileText size={18} />
      case 'txt':
        return <FileText size={18} />
      case 'md':
        return <FileText size={18} />
      default:
        return <FileText size={18} />
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="kb-detail-page"
    >
      <aside className="kb-detail-sidebar">
        <div className="kb-summary">
          <div className="kb-summary-icon">
            <BookOpen size={18} />
          </div>
          <div className="kb-summary-text">
            <div className="kb-summary-name">{kb?.name || 'Knowledge Base'}</div>
            <div className="kb-summary-desc">{kb?.description || 'No description'}</div>
          </div>
        </div>
        <div className="kb-nav">
          <button type="button" className="kb-nav-item active">
            <Folder size={16} className="kb-nav-icon" />
            Documents
          </button>
        </div>
      </aside>

      <div className="kb-detail-main">
        {/* Header */}
        <div className="kb-detail-header">
          <div>
            <button onClick={() => navigate('/knowledge-bases')} className="kb-back-link">
              <svg className="kb-back-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Knowledge Bases
            </button>
            <h1 className="kb-page-title">Documents</h1>
            <p className="kb-page-subtitle">Manage files in this knowledge base for retrieval and chat.</p>
          </div>
        </div>

        {/* Toolbar */}
        <div className="kb-detail-toolbar">
          <div className="kb-toolbar-left">
            <div className="kb-filter">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="kb-select"
              >
                <option value="all">All</option>
                <option value="ready">Ready</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
            </div>
            <div className="kb-search">
              <svg className="kb-search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="kb-search-input"
              />
            </div>
          </div>
          <div className="kb-toolbar-right">
            <div className="kb-stats">
              <div className="kb-stat">
                <span className="kb-stat-label">Files</span>
                <span className="kb-stat-value">{files.length}</span>
              </div>
              <div className="kb-stat-divider"></div>
              <div className="kb-stat">
                <span className="kb-stat-label">Size</span>
                <span className="kb-stat-value">{(totalSize / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            </div>
            <button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="kb-upload-btn">
              <svg className="kb-upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
            <input ref={fileInputRef} type="file" onChange={handleUpload} className="hidden" />
          </div>
        </div>

        {/* Content */}
        <div className="kb-detail-content">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-sm" style={{ color: 'var(--main-text-muted)' }}>Loading documents...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-sm text-rose-400">{error}</div>
            </div>
          ) : (
            <div className="kb-table">
              {/* Table Header */}
              <div className="kb-table-row kb-table-header">
                <div>Document</div>
                <div>Segment Mode</div>
                <div>Words</div>
                <div>Recalls</div>
                <div>Uploaded</div>
                <div>Status</div>
                <div className="kb-table-actions">Actions</div>
              </div>

              {/* Table Body */}
              {visibleFiles.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 px-6">
                  <svg className="w-16 h-16 mb-4" style={{ color: 'var(--main-text-muted)', opacity: 0.4 }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <p className="text-sm mb-1" style={{ color: 'var(--main-text-muted)' }}>
                    {searchQuery.trim() ? 'No documents found' : 'No documents uploaded yet'}
                  </p>
                  <p className="text-xs" style={{ color: 'var(--main-text-muted)', opacity: 0.7 }}>
                    {searchQuery.trim() ? 'Try a different search term' : 'Upload your first document to get started'}
                  </p>
                </div>
              ) : (
                visibleFiles.map((file, index) => {
                  const statusClass = ['ready', 'processing', 'failed'].includes(file.status)
                    ? file.status
                    : 'default'
                  return (
                  <div
                    key={file.id}
                    className={`kb-table-row ${index < visibleFiles.length - 1 ? 'kb-table-divider' : ''}`}
                  >
                    <div className="kb-doc-cell">
                      <span className="kb-doc-icon" aria-hidden="true">
                        {getFileIcon(file.filename)}
                      </span>
                      <div className="kb-doc-text">
                        <div className="kb-doc-name">{file.filename}</div>
                        {file.error && <div className="kb-doc-error">{file.error}</div>}
                      </div>
                    </div>
                    <div>
                      <span className="kb-pill">Auto</span>
                    </div>
                    <div className="kb-muted">--</div>
                    <div className="kb-muted">0</div>
                    <div className="kb-muted">{new Date(file.updated_at).toLocaleString()}</div>
                    <div>
                      <span className={`kb-status ${statusClass}`}>
                        {file.status.charAt(0).toUpperCase() + file.status.slice(1)}
                      </span>
                    </div>
                    <div className="kb-table-actions">
                      <button className="kb-action-btn" onClick={() => handleDeleteFile(file.id)} title="Delete">
                        <svg className="kb-action-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  )
                })
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
