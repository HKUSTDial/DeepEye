import { useState, useEffect, useRef } from 'react'
import { ChevronRight, RefreshCw, Home, FolderOpen } from 'lucide-react'
import { sandboxApi } from '../api/sandbox'
import { selectIsStreaming, useChatStore } from '../stores/chat'
import { useLocale } from '../locale'
import { deferEffectWork } from '../utils/effects'
import FileTreeItem, { type FileNode } from './FileTreeItem'
import './FileExplorer.css'

interface FileExplorerProps {
  sessionId: string | null
  selectedPath?: string | null
  onSelectFile: (path: string) => void
}

export default function FileExplorer({
  sessionId,
  selectedPath = null,
  onSelectFile,
}: FileExplorerProps) {
  const { t } = useLocale()
  // 每个属性单独订阅 - 最简单可靠的方式
  const isStreaming = useChatStore(selectIsStreaming)
  const filesChangedTrigger = useChatStore((state) => state.filesChangedTrigger)
  const sandboxReadySessionId = useChatStore((state) => state.sandboxReadySessionId)
  const isSwitchingSession = useChatStore((state) => state.isSwitchingSession)
  
  const [rootFiles, setRootFiles] = useState<FileNode[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sandboxNotCreated, setSandboxNotCreated] = useState(false)
  const [currentSelectedPath, setCurrentSelectedPath] = useState<string | null>(null)
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())
  
  // Delete confirmation dialog
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ path: string; name: string } | null>(null)
  
  const previousSessionIdRef = useRef<string | null>(null)
  const wasStreamingRef = useRef(false)
  const activeSessionRef = useRef<string | null>(sessionId)

  useEffect(() => {
    activeSessionRef.current = sessionId
  }, [sessionId])

  useEffect(() => {
    return deferEffectWork(() => {
      setCurrentSelectedPath(selectedPath)
    })
  }, [selectedPath])

  // Helper functions
  const getFilesFingerprint = (files: FileNode[]): string => {
    const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path))
    return sortedFiles.map(f => `${f.path}|${f.type}|${f.size ?? 0}`).join(';')
  }

  const hasFilesChanged = (oldFiles: FileNode[], newFiles: { path: string; type: string; size?: number }[]): boolean => {
    if (oldFiles.length !== newFiles.length) return true
    
    const oldFingerprint = getFilesFingerprint(oldFiles)
    const newFingerprint = newFiles
      .sort((a, b) => a.path.localeCompare(b.path))
      .map(f => `${f.path}|${f.type}|${f.size ?? 0}`)
      .join(';')
    
    return oldFingerprint !== newFingerprint
  }

  const loadRootFiles = async (preserveExpanded = false) => {
    if (!sessionId || sandboxReadySessionId !== sessionId) return
    
    setIsLoading(true)
    setError(null)
    setSandboxNotCreated(false)
    
    try {
      const response = await sandboxApi.listFiles(sessionId, '/workspace')
      if (activeSessionRef.current !== sessionId) return
      
      setRootFiles(response.files.map(f => ({
        ...f,
        children: undefined,
        isOpen: preserveExpanded && expandedPaths.has(f.path),
        isLoading: false
      })) as FileNode[])
      
      setSandboxNotCreated(false)
    } catch (e: unknown) {
      const status = typeof e === 'object' && e !== null && 'status' in e
        ? (e as { status?: number }).status
        : undefined
      if (status === 404) {
        setSandboxNotCreated(true)
        setError(null)
        setRootFiles([])
        } else {
        setError(e instanceof Error ? e.message : t('files.loadFailedTitle'))
        setRootFiles([])
      }
    } finally {
      setIsLoading(false)
    }
  }

  const loadFolderChildrenRecursive = async (node: FileNode, pathsToExpand: Set<string>) => {
    if (!sessionId || sandboxReadySessionId !== sessionId || node.type !== 'directory') return
    
    node.isLoading = true
    try {
      const response = await sandboxApi.listFiles(sessionId, node.path)
      if (activeSessionRef.current !== sessionId) return
      node.children = response.files.map(f => ({
        ...f,
        children: undefined,
        isOpen: pathsToExpand.has(f.path),
        isLoading: false
      })) as FileNode[]
      
      for (const child of node.children) {
        if (child.isOpen && child.type === 'directory') {
          loadFolderChildrenRecursive(child, pathsToExpand)
        }
      }
    } catch (e) {
      console.error('Failed to load folder:', e)
    } finally {
      node.isLoading = false
    }
  }

  const refreshWithExpandedState = async () => {
    if (!sessionId || sandboxReadySessionId !== sessionId) return
    
    try {
      const response = await sandboxApi.listFiles(sessionId, '/workspace')
      if (activeSessionRef.current !== sessionId) return
      
      const pathsToExpand = new Set(expandedPaths)
      const rootChanged = hasFilesChanged(rootFiles, response.files)
      if (!rootChanged && pathsToExpand.size === 0) {
        console.debug('[FileExplorer] No changes detected, skipping refresh')
        return
      }
      
      console.debug('[FileExplorer] Refreshing files...')
      
      setRootFiles(response.files.map(f => ({
        ...f,
        children: undefined,
        isOpen: pathsToExpand.has(f.path),
        isLoading: false
      })) as FileNode[])
      
      // Load children for expanded folders regardless of root change
      for (const file of response.files) {
        if (pathsToExpand.has(file.path) && file.type === 'directory') {
          loadFolderChildrenRecursive(
            {
              ...file,
              children: undefined,
              isOpen: true,
              isLoading: false,
            } as FileNode,
            pathsToExpand,
          )
        }
      }
    } catch (e) {
      console.error('[FileExplorer] Refresh error:', e)
    }
  }

  const loadFolderChildren = async (node: FileNode) => {
    if (!sessionId || sandboxReadySessionId !== sessionId || node.type !== 'directory') return
    
    node.isLoading = true
    try {
      const response = await sandboxApi.listFiles(sessionId, node.path)
      if (activeSessionRef.current !== sessionId) return
      node.children = response.files.map(f => ({
        ...f,
        children: undefined,
        isOpen: false,
        isLoading: false
      })) as FileNode[]
    } catch (e) {
      console.error('Failed to load folder:', e)
    } finally {
      node.isLoading = false
    }
  }

  const handleToggle = async (node: FileNode) => {
    if (node.isOpen) {
      node.isOpen = false
      setExpandedPaths(prev => {
        const newSet = new Set(prev)
        newSet.delete(node.path)
        return newSet
      })
      setRootFiles([...rootFiles])
      return
    }
    
    node.isOpen = true
    setExpandedPaths(prev => new Set(prev).add(node.path))
    
    if (!node.children) {
      await loadFolderChildren(node)
    }
    setRootFiles([...rootFiles])
  }

  const handleSelect = (path: string) => {
    setCurrentSelectedPath(path)
    onSelectFile(path)
  }

  const handleDownload = async (path: string) => {
    if (!sessionId) return

    try {
      const { blob, filename } = await sandboxApi.download(sessionId, path)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Download failed:', e)
    }
  }

  const handleDeleteRequest = (path: string, name: string) => {
    setDeleteTarget({ path, name })
    setShowDeleteConfirm(true)
  }

  const confirmDelete = async () => {
    if (!sessionId || !deleteTarget) return
    
    try {
      await sandboxApi.deleteFile(sessionId, deleteTarget.path)
      setShowDeleteConfirm(false)
      setDeleteTarget(null)
      await loadRootFiles(true)
    } catch (e) {
      console.error('Failed to delete:', e)
    }
  }

  const cancelDelete = () => {
    setShowDeleteConfirm(false)
    setDeleteTarget(null)
  }

  // Watch for session changes
  useEffect(() => {
    const oldSessionId = previousSessionIdRef.current
    previousSessionIdRef.current = sessionId
    if (isSwitchingSession) return

    return deferEffectWork(() => {
      if (sessionId && sandboxReadySessionId === sessionId) {
        if (oldSessionId !== undefined && oldSessionId !== null) {
          loadRootFiles()
        } else {
          setSandboxNotCreated(true)
          setRootFiles([])
        }
      } else {
        setRootFiles([])
        setSandboxNotCreated(Boolean(sessionId))
        setError(null)
      }
    })
    // We intentionally react only to session/stream flags; `loadRootFiles` is stable enough for this lifecycle hook.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, sandboxReadySessionId, isSwitchingSession])

  // Auto-refresh when streaming completes
  useEffect(() => {
    const wasStreaming = wasStreamingRef.current
    wasStreamingRef.current = isStreaming

    if (wasStreaming && !isStreaming && sessionId && sandboxReadySessionId === sessionId) {
      setTimeout(() => {
        loadRootFiles()
      }, 500)
    }
    // Triggered by streaming/session changes only; do not re-run for internal helper identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isStreaming, sessionId, sandboxReadySessionId])

  // Refresh when files change (via event from backend)
  useEffect(() => {
    if (sessionId && sandboxReadySessionId === sessionId && filesChangedTrigger > 0) {
      return deferEffectWork(() => {
        refreshWithExpandedState()
      })
    }
    // This effect is keyed by backend file-change signals and active session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filesChangedTrigger, sessionId, sandboxReadySessionId])

  return (
    <div className="file-explorer">
      {/* Header */}
      <div className="file-explorer-header">
        <div className="file-explorer-breadcrumb">
          <Home size={14} />
          <ChevronRight size={12} className="file-explorer-breadcrumb-separator" />
          <span>{t('files.workspaceRoot')}</span>
        </div>
        {sessionId && (
          <button
            onClick={() => loadRootFiles(true)}
            disabled={isLoading}
            className="file-explorer-btn"
            title={t('files.refreshTitle')}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
        )}
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto ide-scrollbar">
        {/* Empty State */}
        {!sessionId && (
          <div className="file-explorer-empty">
            <div className="file-explorer-empty-icon">
              <FolderOpen size={22} />
            </div>
            <p className="file-explorer-empty-title">{t('files.noSessionTitle')}</p>
            <p className="file-explorer-empty-subtitle">{t('files.noSessionSubtitle')}</p>
          </div>
        )}

        {/* Loading Root */}
        {sessionId && isLoading && rootFiles.length === 0 && (
          <div className="file-explorer-empty">
            <div className="w-6 h-6 rounded-full border-2 border-[var(--border-color)] border-t-[var(--accent)] animate-spin"></div>
            <p className="file-explorer-empty-title mt-3">{t('files.loadingWorkspaceTitle')}</p>
            <p className="file-explorer-empty-subtitle">{t('files.loadingWorkspaceSubtitle')}</p>
          </div>
        )}

        {/* Sandbox Not Created */}
        {sandboxNotCreated && (
          <div className="file-explorer-empty">
            <div className="file-explorer-empty-icon">
              <FolderOpen size={22} />
            </div>
            <p className="file-explorer-empty-title">{t('files.notReadyTitle')}</p>
            <p className="file-explorer-empty-subtitle">{t('files.notReadySubtitle')}</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="file-explorer-empty">
            <div className="file-explorer-empty-icon file-explorer-empty-icon--error">
              <svg className="w-5 h-5 text-[#ff3b30]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="file-explorer-empty-title">{t('files.loadFailedTitle')}</p>
            <p className="file-explorer-empty-subtitle">{error}</p>
          </div>
        )}

        {/* File Tree */}
        {!error && !sandboxNotCreated && !isLoading && rootFiles.length > 0 && (
          <div className="py-0.5">
            {rootFiles.map(file => (
              <FileTreeItem
                key={file.path}
                file={file}
                selectedPath={currentSelectedPath}
                onToggle={handleToggle}
                onSelect={handleSelect}
                onDownload={handleDownload}
                onDelete={handleDeleteRequest}
              />
            ))}
          </div>
        )}

        {/* Empty Root */}
        {!error && !sandboxNotCreated && !isLoading && rootFiles.length === 0 && sessionId && (
          <div className="file-explorer-empty">
            <div className="file-explorer-empty-icon">
              <FolderOpen size={22} />
            </div>
            <p className="file-explorer-empty-title">{t('files.emptyWorkspaceTitle')}</p>
            <p className="file-explorer-empty-subtitle">{t('files.emptyWorkspaceSubtitle')}</p>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="delete-overlay" onClick={cancelDelete}>
          <div className="delete-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="delete-title">{t('files.confirmDeleteTitle')}</div>
            <div className="delete-message">
              {t('files.confirmDeleteMessage', { name: deleteTarget?.name ?? '' })}
            </div>
            <div className="delete-actions">
              <button className="delete-btn delete-btn-cancel" onClick={cancelDelete}>
                {t('common.cancel')}
              </button>
              <button className="delete-btn delete-btn-confirm" onClick={confirmDelete}>
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
