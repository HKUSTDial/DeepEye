import { useState, useEffect, useRef } from 'react'
import { datasourceApi } from '../api'
import { useChatStore } from '../stores/chat'
import type { DataSource } from '../types'
import './DataSourceManager.css'

interface DataSourceManagerProps {
  selectedIds: string[]
  onToggle: (id: string) => void
  collapsed?: boolean
}

export default function DataSourceManager({ selectedIds, onToggle, collapsed = false }: DataSourceManagerProps) {
  const sessionId = useChatStore((state) => state.sessionId)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [newDs, setNewDs] = useState({ name: '', type: 'postgres', connection_string: '' })
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCollapsedPanel, setShowCollapsedPanel] = useState(false)
  const collapsedPanelRef = useRef<HTMLDivElement>(null)

  const loadDataSources = async () => {
    try {
      const list = await datasourceApi.list()
      setDataSources(list)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    }
  }

  const createDataSource = async () => {
    if (!newDs.name || !newDs.connection_string) return
    try {
      const created = await datasourceApi.create(newDs)
      setDataSources([...dataSources, created])
      setIsCreating(false)
      setNewDs({ name: '', type: 'postgres', connection_string: '' })
      onToggle(created.id)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create')
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setError(null)
    try {
      const created = await datasourceApi.upload(file, sessionId)
      setDataSources((prev) => [...prev, created])
      onToggle(created.id)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setIsUploading(false)
      e.target.value = '' // Reset input
    }
  }

  const deleteDataSource = async (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    if (!confirm('Delete this data source?')) return
    try {
      await datasourceApi.delete(id, sessionId)
      setDataSources(dataSources.filter((ds) => ds.id !== id))
      if (selectedIds.includes(id)) {
        onToggle(id)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete')
    }
  }

  useEffect(() => {
    loadDataSources()
  }, [])

  useEffect(() => {
    if (!collapsed) {
      setShowCollapsedPanel(false)
    }
  }, [collapsed])

  useEffect(() => {
    if (!showCollapsedPanel) return
    const onMouseDown = (event: MouseEvent) => {
      if (!collapsedPanelRef.current) return
      if (!collapsedPanelRef.current.contains(event.target as Node)) {
        setShowCollapsedPanel(false)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [showCollapsedPanel])

  const managerContent = (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1.5 mb-1">
        <span className="text-xs font-medium text-[var(--sidebar-text-muted)] uppercase tracking-wider whitespace-nowrap truncate">
          Data Sources
        </span>
        <div className="flex gap-1">
          {/* File Upload Button */}
          <label className="btn p-1.5 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--sidebar-text-muted)] hover:text-[var(--sidebar-text)] cursor-pointer">
            <input
              type="file"
              className="hidden"
              onChange={handleFileUpload}
              disabled={isUploading}
              accept=".csv,.json,.xlsx,.xls,.parquet"
            />
            {isUploading ? (
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
            )}
          </label>
          {/* Add DB Button */}
          <button
            onClick={() => setIsCreating(!isCreating)}
            className="btn p-1.5 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--sidebar-text-muted)] hover:text-[var(--sidebar-text)]"
            title={isCreating ? 'Cancel' : 'Add Database'}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className={`w-4 h-4 transition-transform duration-200 ${isCreating ? 'rotate-45' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      {/* Error */}
      {error && <div className="text-red-400 text-xs px-2 mb-2">{error}</div>}

      {/* Create Form */}
      {isCreating && (
        <div className="form-panel">
          <div className="space-y-2 p-2.5 bg-[var(--sidebar-hover)] rounded-xl mb-2">
            <input
              value={newDs.name}
              onChange={(e) => setNewDs({ ...newDs, name: e.target.value })}
              placeholder="Name"
              className="w-full px-3 py-2 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded-lg text-sm focus:outline-none input-focus-ring"
            />
            <select
              value={newDs.type}
              onChange={(e) => setNewDs({ ...newDs, type: e.target.value })}
              className="w-full px-3 py-2 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded-lg text-sm focus:outline-none input-focus-ring"
            >
              <option value="postgres">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
            </select>
            <input
              value={newDs.connection_string}
              onChange={(e) => setNewDs({ ...newDs, connection_string: e.target.value })}
              placeholder="Connection URI"
              className="w-full px-3 py-2 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded-lg text-sm focus:outline-none input-focus-ring"
            />
            <button
              onClick={createDataSource}
              className="btn w-full py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-lg text-sm font-medium"
            >
              Connect
            </button>
          </div>
        </div>
      )}

      {/* List */}
      <div className="space-y-1 max-h-36 overflow-y-auto">
        {dataSources.length === 0 && !isCreating && (
          <div className="text-[var(--sidebar-text-muted)] text-xs text-center py-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-6 h-6 mx-auto mb-1.5 opacity-40"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
            No data sources
          </div>
        )}

        {dataSources.map((ds) => (
          <div
            key={ds.id}
            onClick={() => onToggle(ds.id)}
            className={`group flex items-center gap-2 px-2.5 py-2 rounded-xl cursor-pointer text-sm ds-item ${
              selectedIds.includes(ds.id)
                ? 'bg-[var(--accent)] text-white'
                : 'hover:bg-[var(--sidebar-hover)]'
            }`}
          >
            {/* Icon */}
            {ds.category === 'file' ? (
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-4 h-4 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
                />
              </svg>
            )}
            {/* Name */}
            <span className="flex-1 truncate">{ds.name}</span>
            {/* Delete */}
            <button
              onClick={(e) => deleteDataSource(ds.id, e)}
              className={`btn opacity-0 group-hover:opacity-100 p-1 rounded-lg ${
                selectedIds.includes(ds.id)
                  ? 'hover:bg-white/20'
                  : 'hover:bg-red-500/20 text-[var(--sidebar-text-muted)] hover:text-red-400'
              }`}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </>
  )

  if (collapsed) {
    return (
      <div className="data-source-manager border-t border-[var(--sidebar-border)] p-2 relative">
        <div className="flex justify-start pl-[14px]">
          <button
            onClick={() => setShowCollapsedPanel((prev) => !prev)}
            className="btn w-12 h-12 p-0 rounded-xl hover:bg-[var(--sidebar-hover)] text-[var(--sidebar-text)] relative inline-flex items-center justify-center"
            title="Data Sources"
            aria-label="Data Sources"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-[22px] h-[22px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            {selectedIds.length > 0 && (
              <span className="ds-badge">{selectedIds.length}</span>
            )}
          </button>
        </div>
        {showCollapsedPanel && (
          <div ref={collapsedPanelRef} className="collapsed-ds-panel">
            {managerContent}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="data-source-manager border-t border-[var(--sidebar-border)] p-2">
      {managerContent}
    </div>
  )
}

