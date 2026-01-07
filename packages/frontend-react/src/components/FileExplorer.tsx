import { useState, useEffect, useRef } from 'react'
import { ChevronRight, RefreshCw, Home, FolderOpen } from 'lucide-react'
import { sandboxApi } from '../api/sandbox'
import { useChatStore } from '../stores/chat'
import FileTreeItem, { type FileNode } from './FileTreeItem'
import './FileExplorer.css'

interface FileExplorerProps {
  sessionId: string | null
  onSelectFile: (path: string) => void
}

export default function FileExplorer({ sessionId, onSelectFile }: FileExplorerProps) {
  // 每个属性单独订阅 - 最简单可靠的方式
  const isStreaming = useChatStore((state) => state.isStreaming)
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
    } catch (e: any) {
      if (e?.status === 404) {
        setSandboxNotCreated(true)
        setError(null)
        setRootFiles([])
      } else {
        setError(e instanceof Error ? e.message : 'Failed to load files')
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

  const handleDownload = (path: string) => {
    if (!sessionId) return
    
    const url = sandboxApi.getDownloadUrl(sessionId, path)
    const link = document.createElement('a')
    link.href = url
    link.download = ''
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
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
  }, [isStreaming, sessionId, sandboxReadySessionId])

  // Refresh when files change (via event from backend)
  useEffect(() => {
    if (sessionId && sandboxReadySessionId === sessionId && filesChangedTrigger > 0) {
      refreshWithExpandedState()
    }
  }, [filesChangedTrigger, sessionId, sandboxReadySessionId])

  return (
    <div className="h-full flex flex-col bg-[#1e1e1e] select-none">
      {/* Header */}
      <div className="h-9 flex items-center justify-between px-3 bg-[#252526] border-b border-[#3c3c3c]">
        <div className="flex items-center gap-1.5 text-xs text-[#cccccc]">
          <Home size={12} className="text-[#75beff]" />
          <ChevronRight size={10} className="text-[#808080]" />
          <span className="font-medium">workspace</span>
        </div>
        {sessionId && (
          <button
            onClick={() => loadRootFiles(true)}
            disabled={isLoading}
            className="p-1 hover:bg-[#3c3c3c] rounded transition-colors"
            title="Refresh"
          >
            <RefreshCw
              size={12}
              className={`text-[#808080] hover:text-[#cccccc] ${isLoading ? 'animate-spin' : ''}`}
            />
          </button>
        )}
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto ide-scrollbar">
        {/* Empty State */}
        {!sessionId && (
          <div className="h-full flex flex-col items-center justify-center p-4 text-center">
            <FolderOpen size={32} className="text-[#606060] mb-2" />
            <p className="text-xs text-[#808080]">No active session</p>
            <p className="text-[10px] text-[#606060] mt-1">Start a chat to see files</p>
          </div>
        )}

        {/* Loading Root */}
        {sessionId && isLoading && rootFiles.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center p-4">
            <div className="w-6 h-6 rounded-full border border-[#606060] border-t-[#75beff] animate-spin"></div>
            <p className="text-[10px] text-[#808080] mt-2">Loading...</p>
          </div>
        )}

        {/* Sandbox Not Created */}
        {sandboxNotCreated && (
          <div className="h-full flex flex-col items-center justify-center p-4 text-center">
            <FolderOpen size={32} className="text-[#ccaa00] mb-2" />
            <p className="text-xs text-[#cccccc]">Workspace not ready</p>
            <p className="text-[10px] text-[#808080] mt-1 max-w-[140px]">
              Run code with AI agent, or click refresh
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="h-full flex flex-col items-center justify-center p-4 text-center">
            <div className="w-8 h-8 rounded bg-[#5a1d1d] flex items-center justify-center mb-2">
              <svg className="w-4 h-4 text-[#f48771]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="text-xs text-[#f48771]">Failed to load</p>
            <p className="text-[10px] text-[#808080] mt-1">{error}</p>
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
          <div className="h-full flex flex-col items-center justify-center p-4 text-center">
            <FolderOpen size={32} className="text-[#606060] mb-2" />
            <p className="text-xs text-[#808080]">Empty directory</p>
            <p className="text-[10px] text-[#606060] mt-1">No files in /workspace</p>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="delete-overlay" onClick={cancelDelete}>
          <div className="delete-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="delete-title">Confirm Delete</div>
            <div className="delete-message">
              Are you sure you want to delete <span className="font-medium text-white">{deleteTarget?.name}</span>?
            </div>
            <div className="delete-actions">
              <button className="delete-btn delete-btn-cancel" onClick={cancelDelete}>
                Cancel
              </button>
              <button className="delete-btn delete-btn-confirm" onClick={confirmDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

