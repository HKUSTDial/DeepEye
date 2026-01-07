import { useState, useEffect, useMemo } from 'react'
import { X, FileCode, FileText as FileTextIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { sandboxApi, type FileContentResponse } from '../api/sandbox'
import { useCodeHighlight } from '../hooks/useCodeHighlight'
import './FileViewer.css'

interface FileViewerProps {
  sessionId: string | null
  filePath: string | null
  onClose: () => void
}

export default function FileViewer({ sessionId, filePath, onClose }: FileViewerProps) {
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [highlightedCode, setHighlightedCode] = useState<string>('')

  const { highlight, isInitializing: isHighlighterLoading } = useCodeHighlight()

  const fileName = useMemo(() => {
    return filePath?.split('/').pop() || ''
  }, [filePath])

  const fileExtension = useMemo(() => {
    const name = fileName
    return name.includes('.') ? name.split('.').pop()?.toLowerCase() : ''
  }, [fileName])

  const viewerType = useMemo(() => {
    if (!fileContent) return 'none'
    
    if (fileContent.content_type === 'image') {
      return 'image'
    }
    
    const ext = fileExtension
    
    if (ext === 'md') return 'markdown'
    if (ext === 'csv') return 'csv'
    if (['py', 'js', 'ts', 'jsx', 'tsx', 'json', 'html', 'css', 'xml', 'yaml', 'yml'].includes(ext || '')) {
      return 'code'
    }
    
    return 'text'
  }, [fileContent, fileExtension])

  const csvData = useMemo(() => {
    if (viewerType !== 'csv' || !fileContent) return null
    
    const lines = fileContent.content.trim().split('\n')
    if (lines.length === 0 || !lines[0]) return null
    
    const headers = lines[0].split(',').map(h => h.trim())
    const rows = lines.slice(1).map(line => 
      line.split(',').map(cell => cell.trim())
    )
    
    return { headers, rows }
  }, [viewerType, fileContent])

  const codeLines = useMemo(() => {
    if (!fileContent) return []
    return fileContent.content.split('\n')
  }, [fileContent])

  const iconColor = useMemo(() => {
    const ext = fileExtension
    const colorMap: Record<string, string> = {
      'py': '#3572A5',
      'js': '#f1e05a',
      'ts': '#3178c6',
      'json': '#cbcb41',
      'html': '#e34c26',
      'css': '#563d7c',
      'vue': '#41b883',
      'md': '#083fa1',
      'csv': '#217346',
    }
    return colorMap[ext || ''] || '#75beff'
  }, [fileExtension])

  const loadFile = async (sessionId: string, path: string) => {
    setIsLoading(true)
    setError(null)
    setHighlightedCode('')
    
    try {
      const content = await sandboxApi.getFileContent(sessionId, path)
      setFileContent(content)
      
      // Highlight code if it's a code file
      if (content.content_type === 'text') {
        const ext = path.split('.').pop()?.toLowerCase() || ''
        if (['py', 'js', 'ts', 'jsx', 'tsx', 'json', 'html', 'css', 'xml', 'yaml', 'yml', 'vue', 'sh', 'bash', 'sql'].includes(ext)) {
          const code = await highlight(content.content, ext)
          setHighlightedCode(code)
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load file')
      setFileContent(null)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (sessionId && filePath) {
      loadFile(sessionId, filePath)
    } else {
      setFileContent(null)
      setHighlightedCode('')
    }
  }, [sessionId, filePath])

  return (
    <div className="h-full flex flex-col bg-[#1e1e1e]">
      {/* Tab Bar */}
      {filePath && (
        <div className="h-9 flex items-center bg-[#252526] border-b border-[#3c3c3c]">
          <div className="h-full flex items-center gap-2 px-3 bg-[#1e1e1e] border-r border-[#3c3c3c] max-w-[200px]">
            <FileCode size={14} style={{ color: iconColor }} />
            <span className="text-[13px] text-[#cccccc] truncate">{fileName}</span>
            <button
              onClick={onClose}
              className="ml-1 p-0.5 hover:bg-[#3c3c3c] rounded transition-colors opacity-60 hover:opacity-100"
              title="Close"
            >
              <X size={14} className="text-[#cccccc]" />
            </button>
          </div>
        </div>
      )}

      {/* Breadcrumb */}
      {filePath && (
        <div className="h-6 flex items-center px-3 bg-[#1e1e1e] border-b border-[#3c3c3c]/50 text-[11px] text-[#808080]">
          <span className="truncate font-mono">{filePath}</span>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Loading */}
        {isLoading && (
          <div className="h-full flex flex-col items-center justify-center">
            <div className="w-8 h-8 rounded-full border border-[#606060] border-t-[#75beff] animate-spin"></div>
            <p className="text-xs text-[#808080] mt-3">Loading...</p>
          </div>
        )}

        {/* Error */}
        {!isLoading && error && (
          <div className="h-full flex flex-col items-center justify-center p-6">
            <div className="w-10 h-10 rounded bg-[#5a1d1d] flex items-center justify-center mb-3">
              <svg className="w-5 h-5 text-[#f48771]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="text-sm text-[#f48771]">Failed to load file</p>
            <p className="text-xs text-[#808080] mt-2 text-center">{error}</p>
          </div>
        )}

        {/* Image Viewer */}
        {!isLoading && !error && viewerType === 'image' && fileContent && (
          <div className="h-full flex items-center justify-center p-6 bg-[#1e1e1e] overflow-auto">
            <img
              src={`data:image/${fileExtension};base64,${fileContent.content}`}
              alt={fileName}
              className="max-w-full max-h-full object-contain"
            />
          </div>
        )}

        {/* Markdown Viewer */}
        {!isLoading && !error && viewerType === 'markdown' && fileContent && (
          <div className="flex-1 overflow-auto p-6 bg-[#1e1e1e]">
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
              >
                {fileContent.content}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* CSV Viewer */}
        {!isLoading && !error && viewerType === 'csv' && csvData && (
          <div className="flex-1 overflow-auto bg-[#1e1e1e]">
            <table className="w-full text-[13px] border-collapse">
              <thead className="sticky top-0 z-10">
                <tr className="bg-[#252526]">
                  <th className="px-3 py-2 text-left font-semibold text-[#4fc1ff] border-b border-r border-[#3c3c3c] whitespace-nowrap">
                    #
                  </th>
                  {csvData.headers.map((header, idx) => (
                    <th
                      key={idx}
                      className="px-3 py-2 text-left font-semibold text-[#4fc1ff] border-b border-r border-[#3c3c3c] whitespace-nowrap"
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {csvData.rows.map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-[#2a2d2e] transition-colors">
                    <td className="px-3 py-1.5 text-[#858585] border-r border-[#3c3c3c]/50 font-mono text-right">
                      {rowIdx + 1}
                    </td>
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx} className="px-3 py-1.5 text-[#cccccc] border-r border-[#3c3c3c]/50">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Code Viewer with Line Numbers */}
        {!isLoading && !error && viewerType === 'code' && fileContent && (
          <div className="flex-1 overflow-auto ide-code-viewer">
            {isHighlighterLoading && !highlightedCode ? (
              <div className="h-full flex flex-col items-center justify-center">
                <div className="w-6 h-6 rounded-full border border-[#606060] border-t-[#75beff] animate-spin"></div>
                <p className="text-xs text-[#808080] mt-2">Loading syntax highlighter...</p>
              </div>
            ) : highlightedCode ? (
              <div className="code-with-lines">
                <div dangerouslySetInnerHTML={{ __html: highlightedCode }} className="shiki-wrapper"></div>
              </div>
            ) : (
              <div className="text-viewer">
                <table className="text-viewer-table">
                  <tbody>
                    {codeLines.map((line, idx) => (
                      <tr key={idx} className="text-line">
                        <td className="line-number">{idx + 1}</td>
                        <td className="line-content">
                          <pre>{line}</pre>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Text Viewer with Line Numbers */}
        {!isLoading && !error && viewerType === 'text' && fileContent && (
          <div className="flex-1 overflow-auto text-viewer">
            <table className="text-viewer-table">
              <tbody>
                {codeLines.map((line, idx) => (
                  <tr key={idx} className="text-line">
                    <td className="line-number">{idx + 1}</td>
                    <td className="line-content">
                      <pre>{line}</pre>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* No File Selected */}
        {!isLoading && !error && !fileContent && (
          <div className="h-full flex flex-col items-center justify-center p-6 bg-[#1e1e1e]">
            <FileTextIcon size={48} className="text-[#404040] mb-4" />
            <p className="text-sm text-[#808080]">Select a file to preview</p>
            <p className="text-xs text-[#606060] mt-1">Click a file on the left</p>
          </div>
        )}
      </div>
    </div>
  )
}

