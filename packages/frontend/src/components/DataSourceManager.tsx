import { useCallback, useEffect, useRef, useState } from 'react'
import { datasourceApi, sessionApi, type DatasourceTablesResponse } from '../api'
import { useChatStore } from '../stores/chat'
import type { DataSource } from '../types'
import './DataSourceManager.css'

interface DataSourceManagerProps {
  onDataSourcesChange?: (dataSources: DataSource[]) => void
  variant?: 'sidebar' | 'composer' | 'modal'
}

const ENGINE_OPTIONS = [
  { value: 'postgres', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'sqlite', label: 'SQLite' },
] as const

const URI_EXAMPLES: Record<string, string> = {
  postgres: 'postgresql://user:password@localhost:5432/analytics',
  mysql: 'mysql://user:password@localhost:3306/analytics',
  sqlite: 'sqlite:////absolute/path/to/analytics.db',
}

const emitDatasourceUpdated = () => {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('datasources:updated'))
  }
}

const isSupportedFile = (file: File) => {
  const name = file.name.toLowerCase()
  return (
    name.endsWith('.csv') ||
    name.endsWith('.json') ||
    name.endsWith('.xlsx') ||
    name.endsWith('.xls') ||
    name.endsWith('.parquet')
  )
}

interface EngineSelectProps {
  value: string
  onChange: (value: string) => void
}

function EngineSelect({ value, onChange }: EngineSelectProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  const selected = ENGINE_OPTIONS.find((option) => option.value === value) ?? ENGINE_OPTIONS[0]

  useEffect(() => {
    if (!open) return

    const onMouseDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className={`data-source-select-shell ${open ? 'is-open' : ''}`} ref={rootRef}>
      <button
        type="button"
        className={`data-source-field data-source-select-trigger ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="data-source-select-trigger-value">{selected.label}</span>
        <span className="data-source-select-chevron" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="m5.5 7.5 4.5 5 4.5-5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>

      {open && (
        <div className="data-source-select-menu" role="listbox" aria-label="Database engine">
          {ENGINE_OPTIONS.map((option) => {
            const isSelected = option.value === value
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={`data-source-select-option ${isSelected ? 'is-selected' : ''}`}
                onClick={() => {
                  onChange(option.value)
                  setOpen(false)
                }}
              >
                <span className="data-source-select-option-label">{option.label}</span>
                {isSelected && (
                  <span className="data-source-select-option-check" aria-hidden="true">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="m4.5 10 3.2 3.2L15.5 5.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function DataSourceManager({ onDataSourcesChange, variant = 'sidebar' }: DataSourceManagerProps) {
  const sessionId = useChatStore((state) => state.sessionId)
  const createSession = useChatStore((state) => state.createSession)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [newDs, setNewDs] = useState({ name: '', type: 'postgres', connection_string: '' })
  const [isUploading, setIsUploading] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tablesByDsId, setTablesByDsId] = useState<Record<string, DatasourceTablesResponse>>({})
  const [loadingTablesId, setLoadingTablesId] = useState<string | null>(null)
  const [expandedDsId, setExpandedDsId] = useState<string | null>(null)
  const [editingDsId, setEditingDsId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ name: '', type: 'mysql', connection_string: '' })
  const [isSavingEdit, setIsSavingEdit] = useState(false)

  const applyDataSources = useCallback(
    (next: DataSource[] | ((current: DataSource[]) => DataSource[])) => {
      setDataSources((current) => {
        const resolved =
          typeof next === 'function' ? (next as (value: DataSource[]) => DataSource[])(current) : next
        onDataSourcesChange?.(resolved)
        return resolved
      })
    },
    [onDataSourcesChange],
  )

  const loadDataSources = useCallback(async (targetSessionId?: string | null) => {
    setError(null)
    const effectiveSessionId = targetSessionId ?? sessionId
    if (!effectiveSessionId || effectiveSessionId === 'draft') {
      applyDataSources([])
      return
    }
    try {
      const list = await sessionApi.listAttachments(effectiveSessionId)
      applyDataSources(list)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to load'
      const is502 = typeof msg === 'string' && (msg.includes('Bad Gateway') || msg.includes('502'))
      setError(
        is502
          ? '后端未就绪或不可达。若用 Docker：请用 http://localhost:8080 访问，并执行 docker compose ps 确认 backend-api 为 healthy；再点「重试」。'
          : msg,
      )
    }
  }, [applyDataSources, sessionId])

  const ensureSessionId = useCallback(async () => {
    if (sessionId && sessionId !== 'draft') {
      return sessionId
    }

    const created = await createSession()
    if (!created) {
      throw new Error('Failed to create a session before attaching data')
    }
    return created.id
  }, [createSession, sessionId])

  const uploadFiles = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return

      const supportedFiles = files.filter(isSupportedFile)
      const ignoredCount = files.length - supportedFiles.length
      if (supportedFiles.length === 0) {
        setError('Only CSV, JSON, Excel, and Parquet files are supported.')
        return
      }

      setIsUploading(true)
      setError(null)
      try {
        const targetSessionId = await ensureSessionId()
        for (const file of supportedFiles) {
          await datasourceApi.upload(file, targetSessionId)
        }
        await loadDataSources(targetSessionId)
        emitDatasourceUpdated()
        if (ignoredCount > 0) {
          setError(`${ignoredCount} unsupported file(s) were skipped.`)
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Upload failed')
      } finally {
        setIsUploading(false)
        setIsDragOver(false)
      }
    },
    [ensureSessionId, loadDataSources],
  )

  const createDataSource = async () => {
    const conn = newDs.connection_string.trim()
    if (!conn) {
      setError('请填写连接字符串 (Connection URI)')
      return
    }
    try {
      setError(null)
      const targetSessionId = await ensureSessionId()
      await datasourceApi.create({
        name: newDs.name.trim() || newDs.type,
        type: newDs.type,
        connection_string: conn,
      }, targetSessionId)
      await loadDataSources(targetSessionId)
      setIsCreating(false)
      setNewDs({ name: '', type: 'postgres', connection_string: '' })
      emitDatasourceUpdated()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to create'
      const detail = (e as { response?: { detail?: string } })?.response?.detail
      setError(detail && typeof detail === 'string' ? detail : msg)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : []
    await uploadFiles(files)
    event.target.value = ''
  }

  const handleDrop = async (event: React.DragEvent<HTMLButtonElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragOver(false)
    const files = Array.from(event.dataTransfer.files || [])
    await uploadFiles(files)
  }

  const startEdit = (ds: DataSource, event: React.MouseEvent) => {
    event.stopPropagation()
    if (ds.category !== 'database') return
    setEditingDsId(ds.id)
    setExpandedDsId(null)
    setEditForm({
      name: ds.name,
      type: ds.type || 'mysql',
      connection_string: ds.connection_string || '',
    })
    setError(null)
  }

  const saveEdit = async () => {
    if (!editingDsId) return
    const conn = editForm.connection_string.trim()
    if (!conn) {
      setError('请填写连接字符串')
      return
    }
    setIsSavingEdit(true)
    setError(null)
    try {
      const updated = await datasourceApi.update(editingDsId, {
        name: editForm.name.trim() || editForm.type,
        type: editForm.type,
        connection_string: conn,
      })
      applyDataSources((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setTablesByDsId((prev) => {
        const next = { ...prev }
        delete next[editingDsId]
        return next
      })
      setEditingDsId(null)
      emitDatasourceUpdated()
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
      setExpandedDsId((current) => (current === id ? null : id))
      return
    }
    setLoadingTablesId(id)
    setError(null)
    try {
      const response = await datasourceApi.tables(id)
      setTablesByDsId((prev) => ({ ...prev, [id]: response }))
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
    if (!sessionId || sessionId === 'draft') return
    if (!confirm('Remove this data source from the current thread?')) return
    try {
      await sessionApi.detachDatasource(sessionId, id)
      applyDataSources((current) => current.filter((item) => item.id !== id))
      setTablesByDsId((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
      if (expandedDsId === id) setExpandedDsId(null)
      if (editingDsId === id) setEditingDsId(null)
      emitDatasourceUpdated()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete')
    }
  }

  useEffect(() => {
    void loadDataSources()
  }, [loadDataSources])

  useEffect(() => {
    const onUpdated = () => {
      void loadDataSources()
    }
    window.addEventListener('datasources:updated', onUpdated)
    return () => window.removeEventListener('datasources:updated', onUpdated)
  }, [loadDataSources])

  return (
    <div className={`data-source-manager ${variant === 'modal' ? 'is-modal' : variant === 'composer' ? 'is-composer' : 'is-sidebar'}`}>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileUpload}
        disabled={isUploading}
        accept=".csv,.json,.xlsx,.xls,.parquet"
        multiple
      />

      <div className="data-source-header">
        <div className="data-source-heading">
          <span className="data-source-heading-label">Attached Data</span>
          <span className="data-source-heading-note">Everything attached here is available to the assistant automatically.</span>
        </div>
        <div className="data-source-actions">
          <button
            type="button"
            className="data-source-toolbar-btn"
            title="Upload file data"
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? (
              <div className="data-source-spinner" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
            )}
            <span>Upload file</span>
          </button>
          <button
            type="button"
            onClick={() => setIsCreating((current) => !current)}
            className={`data-source-toolbar-btn ${isCreating ? 'is-active' : ''}`}
            title={isCreating ? 'Cancel database form' : 'Add database'}
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
            <span>Database</span>
          </button>
          <span className="data-source-count-chip">{dataSources.length}</span>
        </div>
      </div>

      {variant === 'modal' && (
        <button
          type="button"
          className={`data-source-dropzone ${isDragOver ? 'is-dragover' : ''} ${isUploading ? 'is-uploading' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault()
            event.stopPropagation()
            setIsDragOver(true)
          }}
          onDragEnter={(event) => {
            event.preventDefault()
            event.stopPropagation()
            setIsDragOver(true)
          }}
          onDragLeave={(event) => {
            event.preventDefault()
            event.stopPropagation()
            setIsDragOver(false)
          }}
          onDrop={handleDrop}
        >
          <span className="data-source-dropzone-icon">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15 12 10.5 16.5 15M12 10.5V21M20.25 16.5A3.75 3.75 0 0 0 18 9.672 5.25 5.25 0 0 0 7.5 8.25a4.5 4.5 0 0 0-.63 8.956" />
            </svg>
          </span>
          <span className="data-source-dropzone-copy">
            <span className="data-source-dropzone-title">
              {isUploading ? 'Uploading files...' : 'Drag files here or click to browse'}
            </span>
            <span className="data-source-dropzone-note">
              CSV, JSON, Excel, and Parquet are supported.
            </span>
          </span>
        </button>
      )}

      {error && (
        <div className="data-source-error">
          <span>{error}</span>
          <button type="button" onClick={() => void loadDataSources()} className="data-source-link-btn">
            重试
          </button>
        </div>
      )}

      {isCreating && (
        <div className="data-source-form-panel data-source-form-panel-db">
          <div className="data-source-form-intro">
            <span className="data-source-form-kicker">Database connection</span>
            <span className="data-source-form-copy">Create a reusable live source for reports, dashboards, and follow-up analysis.</span>
          </div>
          <div className="data-source-form-grid">
            <label className="data-source-field-group">
              <span className="data-source-field-label">Display name</span>
              <input
                value={newDs.name}
                onChange={(event) => setNewDs({ ...newDs, name: event.target.value })}
                placeholder="Revenue warehouse"
                className="data-source-field"
              />
            </label>
            <label className="data-source-field-group">
              <span className="data-source-field-label">Engine</span>
              <EngineSelect
                value={newDs.type}
                onChange={(nextType) => setNewDs({ ...newDs, type: nextType })}
              />
            </label>
          </div>
          <label className="data-source-field-group">
            <span className="data-source-field-label">Connection URI</span>
            <textarea
              value={newDs.connection_string}
              onChange={(event) => setNewDs({ ...newDs, connection_string: event.target.value })}
              placeholder={URI_EXAMPLES[newDs.type] || 'Connection URI'}
              className="data-source-field data-source-field-mono data-source-textarea"
              rows={3}
            />
          </label>
          <div className="data-source-uri-help">
            <span className="data-source-uri-label">Example</span>
            <code className="data-source-uri-example">{URI_EXAMPLES[newDs.type] || 'Connection URI'}</code>
          </div>
          <div className="data-source-form-footer">
            <button type="button" onClick={createDataSource} className="data-source-submit-btn">
              Connect database
            </button>
          </div>
        </div>
      )}

      <div className="data-source-list">
        {dataSources.length === 0 && !isCreating && (
          <div className="data-source-empty-state">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-6 h-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.25"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
            <span>No attached data yet</span>
          </div>
        )}

        {dataSources.map((ds) => {
          const isDatabase = ds.category === 'database'
          const isOpen = expandedDsId === ds.id || editingDsId === ds.id
          return (
            <div key={ds.id} className={`data-source-card ${isOpen ? 'is-open' : ''}`}>
              <div className="data-source-row">
                <div className={`data-source-kind ${isDatabase ? 'is-database' : 'is-file'}`}>
                  {isDatabase ? (
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.6">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.6" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  )}
                </div>
                <div className="data-source-copy">
                  <span className="data-source-name">{ds.name}</span>
                  <span className="data-source-meta">{isDatabase ? (ds.type || 'database').toUpperCase() : 'FILE'}</span>
                </div>
                <div className="data-source-row-actions">
                  {isDatabase && (
                    <button
                      type="button"
                      onClick={(event) => startEdit(ds, event)}
                      className="data-source-icon-btn"
                      title="Edit connection"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  )}
                  {isDatabase && (
                    <button
                      type="button"
                      onClick={(event) => void loadTables(ds.id, event)}
                      className="data-source-icon-btn"
                      title="View tables"
                    >
                      {loadingTablesId === ds.id ? (
                        <div className="data-source-spinner is-small" />
                      ) : (
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                        </svg>
                      )}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={(event) => void deleteDataSource(ds.id, event)}
                    className="data-source-icon-btn is-danger"
                    title="Delete data source"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {isDatabase && editingDsId === ds.id && (
                <div className="data-source-subpanel" onClick={(event) => event.stopPropagation()}>
                  <div className="data-source-form-grid">
                    <label className="data-source-field-group">
                      <span className="data-source-field-label">Display name</span>
                      <input
                        value={editForm.name}
                        onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))}
                        placeholder="Revenue warehouse"
                        className="data-source-field"
                      />
                    </label>
                    <label className="data-source-field-group">
                      <span className="data-source-field-label">Engine</span>
                      <EngineSelect
                        value={editForm.type}
                        onChange={(nextType) => setEditForm((current) => ({ ...current, type: nextType }))}
                      />
                    </label>
                  </div>
                  <label className="data-source-field-group">
                    <span className="data-source-field-label">Connection URI</span>
                    <textarea
                      value={editForm.connection_string}
                      onChange={(event) => setEditForm((current) => ({ ...current, connection_string: event.target.value }))}
                      placeholder={URI_EXAMPLES[editForm.type] || 'Connection URI'}
                      className="data-source-field data-source-field-mono data-source-textarea"
                      rows={3}
                    />
                  </label>
                  <div className="data-source-uri-help">
                    <span className="data-source-uri-label">Example</span>
                    <code className="data-source-uri-example">{URI_EXAMPLES[editForm.type] || 'Connection URI'}</code>
                  </div>
                  <div className="data-source-subpanel-actions">
                    <button
                      type="button"
                      onClick={saveEdit}
                      disabled={isSavingEdit}
                      className="data-source-submit-btn"
                    >
                      {isSavingEdit ? '保存中...' : '保存连接'}
                    </button>
                    <button type="button" onClick={cancelEdit} className="data-source-secondary-btn">
                      取消
                    </button>
                  </div>
                </div>
              )}

              {isDatabase && expandedDsId === ds.id && tablesByDsId[ds.id] && (
                <div className="data-source-subpanel" onClick={(event) => event.stopPropagation()}>
                  <div className="data-source-subpanel-note">Tables ({tablesByDsId[ds.id].tables.length})</div>
                  <ul className="data-source-table-list">
                    {tablesByDsId[ds.id].tables.map((table) => (
                      <li key={table.name} className="data-source-table-item" title={`${table.name}: ${table.columns.map((column) => column.name).join(', ')}`}>
                        <span className="data-source-table-name">{table.name}</span>
                        <span className="data-source-table-meta">{table.columns.length} columns</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
