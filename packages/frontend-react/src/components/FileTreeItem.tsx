import { useState, useMemo, useEffect } from 'react'
import { Loader2, Download, Trash2 } from 'lucide-react'
import type { FileInfo } from '../api/sandbox'
import './FileTreeItem.css'

export interface FileNode extends FileInfo {
  children?: FileNode[]
  isOpen?: boolean
  isLoading?: boolean
}

interface FileTreeItemProps {
  file: FileNode
  depth?: number
  selectedPath?: string | null
  onToggle: (node: FileNode) => void
  onSelect: (path: string) => void
  onDownload: (path: string, type: 'file' | 'directory') => void
  onDelete: (path: string, name: string) => void
}

export default function FileTreeItem({
  file,
  depth = 0,
  selectedPath = null,
  onToggle,
  onSelect,
  onDownload,
  onDelete,
}: FileTreeItemProps) {
  const [showContextMenu, setShowContextMenu] = useState(false)
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 })

  const paddingLeft = useMemo(() => `${depth * 12 + 8}px`, [depth])
  const isSelected = useMemo(() => selectedPath === file.path, [selectedPath, file.path])

  // File icon colors based on extension
  const getIconColor = (ext: string | undefined): string => {
    const e = ext?.toLowerCase()
    if (!e) return '#cccccc'

    const colorMap: Record<string, string> = {
      // Python
      py: '#3572A5',
      // JavaScript/TypeScript
      js: '#f1e05a',
      jsx: '#f1e05a',
      ts: '#3178c6',
      tsx: '#3178c6',
      // Web
      html: '#e34c26',
      css: '#563d7c',
      vue: '#41b883',
      svelte: '#ff3e00',
      // Data
      json: '#cbcb41',
      yaml: '#cb171e',
      yml: '#cb171e',
      xml: '#e34c26',
      csv: '#217346',
      xlsx: '#217346',
      // Markdown
      md: '#083fa1',
      txt: '#cccccc',
      // Config
      toml: '#9c4121',
      ini: '#cccccc',
      env: '#ecd53f',
      // Shell
      sh: '#89e051',
      bash: '#89e051',
      // Images
      png: '#a074c4',
      jpg: '#a074c4',
      jpeg: '#a074c4',
      gif: '#a074c4',
      svg: '#ffb13b',
      // Archives
      zip: '#ec915c',
      tar: '#ec915c',
      gz: '#ec915c',
    }

    return colorMap[e] || '#cccccc'
  }

  const folderColor = useMemo(() => (file.isOpen ? '#dcb67a' : '#c09553'), [file.isOpen])

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenuPos({ x: e.clientX, y: e.clientY })
    setShowContextMenu(true)
  }

  const handleDownload = () => {
    setShowContextMenu(false)
    onDownload(file.path, file.type as 'file' | 'directory')
  }

  const handleDeleteClick = () => {
    setShowContextMenu(false)
    onDelete(file.path, file.name)
  }

  // Close menu on click outside
  useEffect(() => {
    if (!showContextMenu) return

    const closeMenu = () => setShowContextMenu(false)
    setTimeout(() => {
      document.addEventListener('click', closeMenu)
      document.addEventListener('contextmenu', closeMenu)
    }, 0)

    return () => {
      document.removeEventListener('click', closeMenu)
      document.removeEventListener('contextmenu', closeMenu)
    }
  }, [showContextMenu])

  return (
    <div className="select-none relative">
      {/* Item Row */}
      <div
        onClick={() => (file.type === 'directory' ? onToggle(file) : onSelect(file.path))}
        onContextMenu={handleContextMenu}
        className={`group flex items-center h-[22px] cursor-pointer ${
          isSelected ? 'bg-[#094771]' : 'hover:bg-[#2a2d2e]'
        }`}
        style={{ paddingLeft }}
      >
        {/* Arrow for Directory */}
        <div className="w-4 h-4 flex items-center justify-center flex-shrink-0">
          {file.isLoading ? (
            <Loader2 size={10} className="animate-spin text-[#808080]" />
          ) : file.type === 'directory' ? (
            <svg
              className={`w-3 h-3 text-[#c5c5c5] transition-transform duration-150 ${
                file.isOpen ? 'rotate-90' : ''
              }`}
              fill="currentColor"
              viewBox="0 0 16 16"
            >
              <path d="M6 4v8l4-4-4-4z" />
            </svg>
          ) : null}
        </div>

        {/* Folder/File Icon */}
        <div className="w-4 h-4 flex items-center justify-center flex-shrink-0 mr-1">
          {file.type === 'directory' ? (
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
              {file.isOpen ? (
                <path
                  d="M20 19H4a2 2 0 01-2-2V7a2 2 0 012-2h5l2 2h9a2 2 0 012 2v8a2 2 0 01-2 2z"
                  fill={folderColor}
                />
              ) : (
                <path
                  d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z"
                  fill={folderColor}
                />
              )}
            </svg>
          ) : (
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
              <path
                d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
                fill="#3c3c3c"
                stroke="#808080"
                strokeWidth="1"
              />
              <path d="M14 2v6h6" fill="#3c3c3c" stroke="#808080" strokeWidth="1" />
              <rect x="8" y="12" width="8" height="1.5" rx="0.5" fill={getIconColor(file.extension)} />
              <rect x="8" y="15" width="5" height="1.5" rx="0.5" fill={getIconColor(file.extension)} />
            </svg>
          )}
        </div>

        {/* Name */}
        <span
          className={`text-[13px] truncate leading-[22px] ${isSelected ? 'text-white' : 'text-[#cccccc]'}`}
        >
          {file.name}
        </span>
      </div>

      {/* Children */}
      {file.isOpen && file.children && (
        <div>
          {file.children.map((child) => (
            <FileTreeItem
              key={child.path}
              file={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onToggle={onToggle}
              onSelect={onSelect}
              onDownload={onDownload}
              onDelete={onDelete}
            />
          ))}
          {/* Empty folder message */}
          {file.children.length === 0 && !file.isLoading && (
            <div
              className="h-[22px] flex items-center text-[11px] text-[#6e6e6e] italic"
              style={{ paddingLeft: `${(depth + 1) * 12 + 24}px` }}
            >
              (empty)
            </div>
          )}
        </div>
      )}

      {/* Context Menu Portal */}
      {showContextMenu && (
        <div
          className="context-menu"
          style={{ left: contextMenuPos.x + 'px', top: contextMenuPos.y + 'px' }}
        >
          <div className="context-menu-item" onClick={handleDownload}>
            <Download size={14} />
            <span>{file.type === 'directory' ? 'Download as ZIP' : 'Download'}</span>
          </div>
          <div className="context-menu-divider"></div>
          <div className="context-menu-item context-menu-item-danger" onClick={handleDeleteClick}>
            <Trash2 size={14} />
            <span>Delete</span>
          </div>
        </div>
      )}
    </div>
  )
}

