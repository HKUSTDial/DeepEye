import { useEffect, useMemo, useRef, useState } from 'react'
import FileExplorer from '../../FileExplorer'
import FileViewer from '../../FileViewer'
import { useChatStore } from '../../../stores/chat'

interface FilesPanelProps {
  sessionId: string | null
}

const MIN_EXPLORER_RATIO = 20
const MAX_EXPLORER_RATIO = 50

export function FilesPanel({ sessionId }: FilesPanelProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [explorerRatio, setExplorerRatio] = useState(35)
  const [isDraggingExplorer, setIsDraggingExplorer] = useState(false)
  const panelRef = useRef<HTMLDivElement | null>(null)

  const notifyFilesChanged = useChatStore((state) => state.notifyFilesChanged)

  useEffect(() => {
    if (sessionId) {
      notifyFilesChanged()
    }
  }, [sessionId, notifyFilesChanged])

  const handleFileSelect = (path: string) => {
    setSelectedFile(path)
  }

  const closeFileViewer = () => {
    setSelectedFile(null)
  }

  const startExplorerDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDraggingExplorer(true)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  const onExplorerDrag = (e: MouseEvent) => {
    if (!isDraggingExplorer || !panelRef.current) return
    const panelRect = panelRef.current.getBoundingClientRect()
    const panelWidth = panelRect.width
    const relativeX = e.clientX - panelRect.left
    const newRatio = (relativeX / panelWidth) * 100
    setExplorerRatio(Math.max(MIN_EXPLORER_RATIO, Math.min(MAX_EXPLORER_RATIO, newRatio)))
  }

  const stopExplorerDrag = () => {
    setIsDraggingExplorer(false)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  useEffect(() => {
    if (isDraggingExplorer) {
      document.addEventListener('mousemove', onExplorerDrag)
      document.addEventListener('mouseup', stopExplorerDrag)
      return () => {
        document.removeEventListener('mousemove', onExplorerDrag)
        document.removeEventListener('mouseup', stopExplorerDrag)
      }
    }
  }, [isDraggingExplorer])

  const explorerStyle = useMemo(
    () => ({
      flex: `0 0 ${explorerRatio}%`,
    }),
    [explorerRatio],
  )

  return (
    <div ref={panelRef} className="flex h-full w-full overflow-hidden">
      <div className="h-full relative min-w-0" style={explorerStyle}>
        <FileExplorer sessionId={sessionId} onSelectFile={handleFileSelect} />
        <div
          className={`resize-handle-explorer ${isDraggingExplorer ? 'resize-active' : ''}`}
          onMouseDown={startExplorerDrag}
        ></div>
      </div>
      <div className="flex-1 h-full min-w-0 border-l border-[#3c3c3c]">
        <FileViewer sessionId={sessionId} filePath={selectedFile} onClose={closeFileViewer} />
      </div>
    </div>
  )
}
