import { useState, useEffect } from 'react'
import { datasourceApi, type DatasourceTablesResponse } from '../api'
import { useChatStore } from '../stores/chat'
import type { DataSource } from '../types'
import './DataSourceManager.css'

interface DataSourceManagerProps {
  selectedIds: string[]
  onToggle: (id: string) => void
}

export default function DataSourceManager({ selectedIds, onToggle }: DataSourceManagerProps) {
  const sessionId = useChatStore((state) => state.sessionId)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [newDs, setNewDs] = useState({ name: '', type: 'postgres', connection_string: '' })
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tablesByDsId, setTablesByDsId] = useState<Record<string, DatasourceTablesResponse>>({})
  const [loadingTablesId, setLoadingTablesId] = useState<string | null>(null)
  const [expandedDsId, setExpandedDsId] = useState<string | null>(null)
  const [editingDsId, setEditingDsId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ name: '', type: 'mysql', connection_string: '' })
  const [isSavingEdit, setIsSavingEdit] = useState(false)

  const loadDataSources = async () => {
    setError(null)
    try {
      const list = await datasourceApi.list()
      setDataSources(list)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to load'
      const is502 = typeof msg === 'string' && (msg.includes('Bad Gateway') || msg.includes('502'))
      setError(
        is502
          ? '后端未就绪或不可达。若用 Docker：请用 http://localhost:8080 访问，并执行 docker compose ps 确认 backend-api 为 healthy；再点「重试」。'
          : msg,
      )
    }
  }

  const createDataSource = async () => {
    const conn = (newDs.connection_string || '').trim()
    if (!conn) {
      setError('请填写连接字符串 (Connection URI)')
      return
    }
    try {
      setError(null)
      const created = await datasourceApi.create({
        name: (newDs.name || '').trim() || newDs.type,
        type: newDs.type,
        connection_string: conn,
      })
      setDataSources([...dataSources, created])
      setIsCreating(false)
      setNewDs({ name: '', type: 'postgres', connection_string: '' })
      onToggle(created.id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to create'
      const detail = (e as { response?: { detail?: string } })?.response?.detail
      setError(detail && typeof detail === 'string' ? detail : msg)
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

  const startEdit = (ds: DataSource, event: React.MouseEvent) => {
    event.stopPropagation()
    if (ds.category !== 'database') return
    setEditingDsId(ds.id)
    setEditForm({
      name: ds.name,
      type: ds.type || 'mysql',
      connection_string: ds.connection_string || '',
    })
    setError(null)
  }

  const saveEdit = async () => {
    if (!editingDsId) return
    const conn = (editForm.connection_string || '').trim()
    if (!conn) {
      setError('请填写连接字符串')
      return
    }
    setIsSavingEdit(true)
    setError(null)
    try {
      const updated = await datasourceApi.update(editingDsId, {
        name: (editForm.name || '').trim() || editForm.type,
        type: editForm.type,
        connection_string: conn,
      })
      setDataSources((prev) => prev.map((d) => (d.id === updated.id ? updated : d)))
      setTablesByDsId((prev) => {
        const next = { ...prev }
        delete next[editingDsId]
        return next
      })
      if (expandedDsId === editingDsId) setExpandedDsId(null)
      setEditingDsId(null)
    } catch (e: unknown) {
      const msg = (e as { response?: { detail?: string } })?.response?.detail ?? (e instanceof Error ? e.message : 'Update failed')
      setError(String(msg))
    } finally {
      setIsSavingEdit(false)
    }
  }

  const cancelEdit = () => {
    setEditingDsId(null)
    setError(null)
  }

  const loadTables = async (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    if (tablesByDsId[id]) {
      setExpandedDsId((prev) => (prev === id ? null : id))
      return
    }
    setLoadingTablesId(id)
    setError(null)
    try {
      const res = await datasourceApi.tables(id)
      setTablesByDsId((prev) => ({ ...prev, [id]: res }))
      setExpandedDsId(id)
    } catch (e: unknown) {
      const msg = (e as { response?: { detail?: string } })?.response?.detail ?? (e instanceof Error ? e.message : 'Failed to load tables')
      setError(String(msg))
    } finally {
      setLoadingTablesId(null)
    }
  }

  const deleteDataSource = async (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    if (!confirm('Delete this data source?')) return
    try {
      await datasourceApi.delete(id, sessionId)
      setDataSources(dataSources.filter((ds) => ds.id !== id))
      setTablesByDsId((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
      if (expandedDsId === id) setExpandedDsId(null)
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

  return (
    <div className="border-t border-[var(--sidebar-border)] p-2">
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1.5 mb-1">
        <span className="text-xs font-medium text-[var(--sidebar-text-muted)] uppercase tracking-wider">
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
      {error && (
        <div className="text-red-400 text-xs px-2 mb-2 flex items-center justify-between gap-2">
          <span>{error}</span>
          <button type="button" onClick={() => loadDataSources()} className="shrink-0 text-[var(--accent)] hover:underline">
            重试
          </button>
        </div>
      )}

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
          <div key={ds.id} className="rounded-xl overflow-hidden">
            <div
              onClick={() => onToggle(ds.id)}
              className={`group flex items-center gap-2 px-2.5 py-2 cursor-pointer text-sm ds-item ${
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
              {/* Database: edit */}
              {ds.category === 'database' && (
                <button
                  onClick={(e) => startEdit(ds, e)}
                  className={`btn p-1 rounded-lg shrink-0 ${
                    selectedIds.includes(ds.id) ? 'hover:bg-white/20' : 'hover:bg-[var(--sidebar-border)] text-[var(--sidebar-text-muted)]'
                  }`}
                  title="编辑连接（如将 mx-mysql 改为 localhost）"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
              )}
              {/* Database: load tables */}
              {ds.category === 'database' && (
                <button
                  onClick={(e) => loadTables(ds.id, e)}
                  className={`btn p-1 rounded-lg shrink-0 ${
                    selectedIds.includes(ds.id) ? 'hover:bg-white/20' : 'hover:bg-[var(--sidebar-border)] text-[var(--sidebar-text-muted)]'
                  }`}
                  title="查看表列表"
                >
                  {loadingTablesId === ds.id ? (
                    <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                    </svg>
                  )}
                </button>
              )}
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
            {/* Edit form for database */}
            {ds.category === 'database' && editingDsId === ds.id && (
              <div
                className="p-2.5 bg-[var(--sidebar-hover)] border-t border-[var(--sidebar-border)] space-y-2 text-sm"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="text-[var(--sidebar-text-muted)] text-xs">编辑连接（本机连接请用 localhost）</div>
                <input
                  value={editForm.name}
                  onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="名称"
                  className="w-full px-2 py-1.5 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded text-xs"
                />
                <select
                  value={editForm.type}
                  onChange={(e) => setEditForm((f) => ({ ...f, type: e.target.value }))}
                  className="w-full px-2 py-1.5 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded text-xs"
                >
                  <option value="postgres">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                </select>
                <input
                  value={editForm.connection_string}
                  onChange={(e) => setEditForm((f) => ({ ...f, connection_string: e.target.value }))}
                  placeholder="mysql://root:密码@localhost:3306/数据库名"
                  className="w-full px-2 py-1.5 bg-[var(--sidebar-bg)] border border-[var(--sidebar-border)] rounded text-xs font-mono"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={saveEdit}
                    disabled={isSavingEdit}
                    className="btn flex-1 py-1.5 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded text-xs disabled:opacity-50"
                  >
                    {isSavingEdit ? '保存中...' : '保存'}
                  </button>
                  <button type="button" onClick={cancelEdit} className="btn py-1.5 px-3 rounded text-xs hover:bg-[var(--sidebar-border)]">
                    取消
                  </button>
                </div>
              </div>
            )}
            {/* Expanded: table list for database */}
            {ds.category === 'database' && expandedDsId === ds.id && tablesByDsId[ds.id] && (
              <div
                className="pl-6 pr-2 py-2 bg-[var(--sidebar-hover)] border-t border-[var(--sidebar-border)] text-xs max-h-28 overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="text-[var(--sidebar-text-muted)] mb-1">表 ({tablesByDsId[ds.id].tables.length})</div>
                <ul className="space-y-0.5">
                  {tablesByDsId[ds.id].tables.map((t) => (
                    <li key={t.name} className="truncate" title={`${t.name}: ${t.columns.map((c) => c.name).join(', ')}`}>
                      <span className="font-medium text-[var(--sidebar-text)]">{t.name}</span>
                      <span className="text-[var(--sidebar-text-muted)] ml-1">({t.columns.length} 列)</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

