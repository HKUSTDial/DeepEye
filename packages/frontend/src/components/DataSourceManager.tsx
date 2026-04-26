import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { datasourceApi, sessionApi, type DatasourcePreviewResponse } from '../api'
import { selectCurrentSessionId, useChatStore } from '../stores/chat'
import { useDatasourceSyncStore } from '../stores/datasourceSync'
import type { DataSource } from '../types'
import { useLocale } from '../locale'
import { deferEffectWork } from '../utils/effects'
import { DataSourceConnectionForm } from './data-source/DataSourceConnectionForm'
import { DataSourcePreviewPanel } from './data-source/DataSourcePreviewPanel'
import {
  PREVIEW_PAGE_SIZE,
  formatConnectionSuccess,
  isSupportedFile,
} from './data-source/dataSourceManagerUtils'
import './DataSourceManager.css'

interface DataSourceManagerProps {
  onDataSourcesChange?: (dataSources: DataSource[]) => void
  variant?: 'sidebar' | 'composer' | 'modal'
}

export default function DataSourceManager({ onDataSourcesChange, variant = 'sidebar' }: DataSourceManagerProps) {
  const { locale, t } = useLocale()
  const sessionId = useChatStore(selectCurrentSessionId)
  const createSession = useChatStore((state) => state.createSession)
  const datasourceRevision = useDatasourceSyncStore((state) => state.revision)
  const notifyDatasourceUpdated = useDatasourceSyncStore((state) => state.notifyUpdated)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const onDataSourcesChangeRef = useRef(onDataSourcesChange)
  const [dataSources, setDataSources] = useState<DataSource[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [newDs, setNewDs] = useState({ name: '', type: 'postgres', connection_string: '' })
  const [isUploading, setIsUploading] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewByDsId, setPreviewByDsId] = useState<Record<string, DatasourcePreviewResponse>>({})
  const [loadingPreviewId, setLoadingPreviewId] = useState<string | null>(null)
  const [expandedDsId, setExpandedDsId] = useState<string | null>(null)
  const [editingDsId, setEditingDsId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ name: '', type: 'mysql', connection_string: '' })
  const [isSavingEdit, setIsSavingEdit] = useState(false)
  const [isTestingCreate, setIsTestingCreate] = useState(false)
  const [isTestingEdit, setIsTestingEdit] = useState(false)
  const [createConnectionStatus, setCreateConnectionStatus] = useState<string | null>(null)
  const [editConnectionStatus, setEditConnectionStatus] = useState<string | null>(null)

  useEffect(() => {
    onDataSourcesChangeRef.current = onDataSourcesChange
  }, [onDataSourcesChange])

  useEffect(() => {
    onDataSourcesChangeRef.current?.(dataSources)
  }, [dataSources])

  const getApiErrorDetail = useCallback((error: unknown, fallback: string) => {
    if (error instanceof ApiError) {
      const detail = (error.response as { detail?: unknown } | undefined)?.detail
      if (typeof detail === 'string') return detail
      return error.message || fallback
    }
    return error instanceof Error ? error.message : fallback
  }, [])

  const applyDataSources = useCallback(
    (next: DataSource[] | ((current: DataSource[]) => DataSource[])) => {
      setDataSources((current) =>
        typeof next === 'function' ? (next as (value: DataSource[]) => DataSource[])(current) : next,
      )
    },
    [],
  )

  const loadDataSources = useCallback(async (targetSessionId?: string | null) => {
    setError(null)
    const effectiveSessionId = targetSessionId ?? sessionId
    if (!effectiveSessionId || effectiveSessionId === 'draft') {
      applyDataSources([])
      setPreviewByDsId({})
      setExpandedDsId(null)
      setEditingDsId(null)
      return
    }
    try {
      const list = await sessionApi.listAttachments(effectiveSessionId)
      applyDataSources(list)
      const visibleIds = new Set(list.map((item) => item.id))
      setPreviewByDsId((current) =>
        Object.fromEntries(Object.entries(current).filter(([id]) => visibleIds.has(id))),
      )
      setExpandedDsId((current) => (current && visibleIds.has(current) ? current : null))
      setEditingDsId((current) => (current && visibleIds.has(current) ? current : null))
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : t('datasource.errorLoad')
      const is502 = typeof msg === 'string' && (msg.includes('Bad Gateway') || msg.includes('502'))
      setError(
        is502
          ? t('datasource.errorBackendUnavailable')
          : msg,
      )
    }
  }, [applyDataSources, sessionId, t])

  const ensureSessionId = useCallback(async () => {
    if (sessionId && sessionId !== 'draft') {
      return sessionId
    }

    const created = await createSession()
    if (!created) {
      throw new Error(t('datasource.errorCreateSession'))
    }
    return created.id
  }, [createSession, sessionId, t])

  const loadPreview = useCallback(
    async (
      datasource: DataSource,
      options?: {
        table?: string | null
        page?: number
      },
    ) => {
      setLoadingPreviewId(datasource.id)
      setExpandedDsId(datasource.id)
      setEditingDsId(null)
      setError(null)
      try {
        const cached = previewByDsId[datasource.id]
        const preview = await datasourceApi.preview(datasource.id, {
          table: options?.table ?? cached?.table ?? undefined,
          page: options?.page ?? cached?.page ?? 1,
          pageSize: PREVIEW_PAGE_SIZE,
        })
        setPreviewByDsId((current) => ({ ...current, [datasource.id]: preview }))
      } catch (e: unknown) {
        setError(getApiErrorDetail(e, t('datasource.errorPreview')))
      } finally {
        setLoadingPreviewId(null)
      }
    },
    [getApiErrorDetail, previewByDsId, t],
  )

  const uploadFiles = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return

      const supportedFiles = files.filter(isSupportedFile)
      const ignoredCount = files.length - supportedFiles.length
      if (supportedFiles.length === 0) {
        setError(t('datasource.errorUnsupportedFiles'))
        return
      }

      setIsUploading(true)
      setError(null)
      try {
        const targetSessionId = await ensureSessionId()
        const createdSources: DataSource[] = []
        for (const file of supportedFiles) {
          const created = await datasourceApi.upload(file, targetSessionId)
          createdSources.push(created)
        }
        await loadDataSources(targetSessionId)
        const latest = createdSources[createdSources.length - 1]
        if (latest) {
          await loadPreview(latest, { page: 1 })
        }
        notifyDatasourceUpdated()
        if (ignoredCount > 0) {
          setError(t('datasource.errorUnsupportedSkipped', { count: ignoredCount }))
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : t('datasource.errorUpload'))
      } finally {
        setIsUploading(false)
        setIsDragOver(false)
      }
    },
    [ensureSessionId, loadDataSources, loadPreview, notifyDatasourceUpdated, t],
  )

  const createDataSource = async () => {
    const conn = newDs.connection_string.trim()
    if (!conn) {
      setError(t('datasource.errorConnectionUriRequired'))
      return
    }
    try {
      setError(null)
      const tested = await runCreateConnectionTest()
      if (!tested) return
      const targetSessionId = await ensureSessionId()
      const created = await datasourceApi.create({
        name: newDs.name.trim() || newDs.type,
        type: newDs.type,
        connection_string: conn,
      }, targetSessionId)
      await loadDataSources(targetSessionId)
      await loadPreview(created, { page: 1 })
      setIsCreating(false)
      setNewDs({ name: '', type: 'postgres', connection_string: '' })
      setCreateConnectionStatus(null)
      notifyDatasourceUpdated()
    } catch (e: unknown) {
      setError(getApiErrorDetail(e, t('datasource.errorCreate')))
    }
  }

  const runCreateConnectionTest = async () => {
    const conn = newDs.connection_string.trim()
    if (!conn) {
      setError(t('datasource.errorConnectionUriRequired'))
      return false
    }
    setIsTestingCreate(true)
    setError(null)
    setCreateConnectionStatus(null)
    try {
      const result = await datasourceApi.testConnection({
        type: newDs.type,
        connection_string: conn,
      })
      setCreateConnectionStatus(formatConnectionSuccess(result, locale))
      return true
    } catch (e: unknown) {
      setError(getApiErrorDetail(e, t('datasource.errorDatabaseConnection')))
      return false
    } finally {
      setIsTestingCreate(false)
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
    setEditConnectionStatus(null)
    setError(null)
  }

  const saveEdit = async () => {
    if (!editingDsId) return
    const conn = editForm.connection_string.trim()
    if (!conn) {
      setError(t('datasource.errorConnectionUriRequiredShort'))
      return
    }
    setIsSavingEdit(true)
    setError(null)
    try {
      const tested = await runEditConnectionTest()
      if (!tested) return
      const updated = await datasourceApi.update(editingDsId, {
        name: editForm.name.trim() || editForm.type,
        type: editForm.type,
        connection_string: conn,
      })
      applyDataSources((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setPreviewByDsId((current) => {
        const next = { ...current }
        delete next[editingDsId]
        return next
      })
      setEditingDsId(null)
      setEditConnectionStatus(null)
      await loadPreview(updated, { page: 1 })
      notifyDatasourceUpdated()
    } catch (e: unknown) {
      setError(getApiErrorDetail(e, t('datasource.errorUpdate')))
    } finally {
      setIsSavingEdit(false)
    }
  }

  const runEditConnectionTest = async () => {
    const conn = editForm.connection_string.trim()
    if (!conn) {
      setError(t('datasource.errorConnectionUriRequiredShort'))
      return false
    }
    setIsTestingEdit(true)
    setError(null)
    setEditConnectionStatus(null)
    try {
      const result = await datasourceApi.testConnection({
        type: editForm.type,
        connection_string: conn,
      })
      setEditConnectionStatus(formatConnectionSuccess(result, locale))
      return true
    } catch (e: unknown) {
      setError(getApiErrorDetail(e, t('datasource.errorDatabaseConnection')))
      return false
    } finally {
      setIsTestingEdit(false)
    }
  }

  const cancelEdit = () => {
    setEditingDsId(null)
    setEditConnectionStatus(null)
    setError(null)
  }

  const togglePreview = async (datasource: DataSource, event: React.MouseEvent) => {
    event.stopPropagation()
    if (expandedDsId === datasource.id && editingDsId !== datasource.id) {
      setExpandedDsId(null)
      return
    }
    const cached = previewByDsId[datasource.id]
    if (cached) {
      setExpandedDsId(datasource.id)
      setEditingDsId(null)
      return
    }
    await loadPreview(datasource, { page: 1 })
  }

  const changePreviewTable = async (datasource: DataSource, table: string) => {
    await loadPreview(datasource, { table, page: 1 })
  }

  const changePreviewPage = async (datasource: DataSource, nextPage: number) => {
    const preview = previewByDsId[datasource.id]
    if (!preview) return
    await loadPreview(datasource, {
      table: preview.table,
      page: nextPage,
    })
  }

  const deleteDataSource = async (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    if (!sessionId || sessionId === 'draft') return
    const target = dataSources.find((item) => item.id === id)
    if (!confirm(t('datasource.confirmRemove', { name: target?.name ?? t('common.attachedData') }))) return
    try {
      await sessionApi.detachDatasource(sessionId, id)
      applyDataSources((current) => current.filter((item) => item.id !== id))
      setPreviewByDsId((current) => {
        const next = { ...current }
        delete next[id]
        return next
      })
      if (expandedDsId === id) setExpandedDsId(null)
      if (editingDsId === id) setEditingDsId(null)
      notifyDatasourceUpdated()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('datasource.errorDelete'))
    }
  }

  useEffect(() => {
    return deferEffectWork(() => {
      void loadDataSources()
    })
  }, [loadDataSources, datasourceRevision])

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
          <span className="data-source-heading-label">{t('datasource.title')}</span>
          <span className="data-source-heading-note">{t('datasource.note')}</span>
        </div>
        <div className="data-source-actions">
          <button
            type="button"
            className="data-source-toolbar-btn"
            title={t('datasource.uploadFileData')}
            onClick={() => fileInputRef.current?.click()}
          >
            {isUploading ? (
              <div className="data-source-spinner" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
            )}
            <span>{t('datasource.uploadFile')}</span>
          </button>
          <button
            type="button"
            onClick={() => setIsCreating((current) => !current)}
            className={`data-source-toolbar-btn ${isCreating ? 'is-active' : ''}`}
            title={isCreating ? t('datasource.cancelDatabaseForm') : t('datasource.addDatabase')}
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
            <span>{t('datasource.addDatabase')}</span>
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
              {isUploading ? t('datasource.dropzoneUploading') : t('datasource.dropzoneTitle')}
            </span>
            <span className="data-source-dropzone-note">
              {t('datasource.dropzoneNote')}
            </span>
          </span>
        </button>
      )}

      {error && (
        <div className="data-source-error">
          <span>{error}</span>
          <button type="button" onClick={() => void loadDataSources()} className="data-source-link-btn">
            {t('common.retry')}
          </button>
        </div>
      )}

      {isCreating && (
        <div className="data-source-form-panel data-source-form-panel-db">
          <DataSourceConnectionForm
            form={newDs}
            onChange={setNewDs}
            statusMessage={createConnectionStatus}
            onClearStatus={() => setCreateConnectionStatus(null)}
            onTest={() => void runCreateConnectionTest()}
            onSubmit={() => void createDataSource()}
            isTesting={isTestingCreate}
            isSubmitting={false}
            submitLabel={t('datasource.connectDatabase')}
            testingLabel={t('datasource.testingConnection')}
            idleTestLabel={t('datasource.testConnection')}
            intro={{
              kicker: t('datasource.databaseConnection'),
              copy: t('datasource.databaseConnectionIntro'),
            }}
          />
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
            <span>{t('datasource.noAttachedData')}</span>
          </div>
        )}

        {dataSources.map((ds) => {
          const isDatabase = ds.category === 'database'
          const isOpen = expandedDsId === ds.id || editingDsId === ds.id
          const preview = previewByDsId[ds.id]
          const isPreviewLoading = loadingPreviewId === ds.id

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
                  <span className="data-source-meta">{isDatabase ? (ds.type || 'database').toUpperCase() : (ds.type || 'file').toUpperCase()}</span>
                </div>
                <div className="data-source-row-actions">
                  <button
                    type="button"
                    onClick={(event) => void togglePreview(ds, event)}
                    className="data-source-icon-btn"
                    title={t('datasource.previewData')}
                  >
                    {isPreviewLoading ? (
                      <div className="data-source-spinner is-small" />
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5.75h18M3 12h18M3 18.25h18" />
                      </svg>
                    )}
                  </button>
                  {isDatabase && (
                    <button
                      type="button"
                      onClick={(event) => startEdit(ds, event)}
                      className="data-source-icon-btn"
                      title={t('datasource.editConnection')}
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={(event) => void deleteDataSource(ds.id, event)}
                    className="data-source-icon-btn is-danger"
                    title={t('datasource.deleteDataSource')}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {isDatabase && editingDsId === ds.id && (
                <div className="data-source-subpanel" onClick={(event) => event.stopPropagation()}>
                  <DataSourceConnectionForm
                    form={editForm}
                    onChange={setEditForm}
                    statusMessage={editConnectionStatus}
                    onClearStatus={() => setEditConnectionStatus(null)}
                    onTest={() => void runEditConnectionTest()}
                    onSubmit={() => void saveEdit()}
                    onCancel={cancelEdit}
                    isTesting={isTestingEdit}
                    isSubmitting={isSavingEdit}
                    submitLabel={t('datasource.saveConnection')}
                    testingLabel={t('datasource.testingConnection')}
                    idleTestLabel={t('datasource.testConnection')}
                  />
                </div>
              )}

              {expandedDsId === ds.id && editingDsId !== ds.id && (
                <DataSourcePreviewPanel
                  datasource={ds}
                  preview={preview}
                  isLoading={isPreviewLoading}
                  onChangeTable={(table) => {
                    void changePreviewTable(ds, table)
                  }}
                  onChangePage={(nextPage) => {
                    void changePreviewPage(ds, nextPage)
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
