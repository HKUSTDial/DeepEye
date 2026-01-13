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
    <div className="file-viewer">
      {/* Tab Bar */}
      {filePath && (
        <div className="file-viewer-tab-bar">
          <div className="file-viewer-tab">
            <FileCode size={14} style={{ color: iconColor }} />
            <span className="file-viewer-tab-name">{fileName}</span>
            <button
              onClick={onClose}
              className="file-viewer-tab-close"
              title="Close"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Breadcrumb */}
      {filePath && (
        <div className="file-viewer-breadcrumb">
          <span className="truncate font-mono">{filePath}</span>
        </div>
      )}

      {/* Content */}
      <div className="file-viewer-content">
        {/* Loading */}
        {isLoading && (
          <div className="file-viewer-loading">
            <div className="loading-spinner"></div>
            <p className="loading-text">Loading...</p>
          </div>
        )}

        {/* Error */}
        {!isLoading && error && (
          <div className="file-viewer-error">
            <div className="error-icon">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <p className="error-title">Failed to load file</p>
            <p className="error-message">{error}</p>
          </div>
        )}

        {/* Image Viewer */}
        {!isLoading && !error && viewerType === 'image' && fileContent && (
          <div className="image-viewer">
            <img
              src={`data:image/${fileExtension};base64,${fileContent.content}`}
              alt={fileName}
              className="image-viewer-img"
            />
          </div>
        )}

        {/* Markdown Viewer */}
        {!isLoading && !error && viewerType === 'markdown' && fileContent && (
          <div className="markdown-viewer">
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
          <div className="csv-viewer">
            <table className="csv-table">
              <thead>
                <tr>
                  <th className="csv-row-number">#</th>
                  {csvData.headers.map((header, idx) => (
                    <th key={idx}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {csvData.rows.map((row, rowIdx) => (
                  <tr key={rowIdx}>
                    <td className="csv-row-number">{rowIdx + 1}</td>
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Code Viewer with Line Numbers */}
        {!isLoading && !error && viewerType === 'code' && fileContent && (
          <div className="code-viewer">
            {isHighlighterLoading && !highlightedCode ? (
              <div className="file-viewer-loading">
                <div className="loading-spinner small"></div>
                <p className="loading-text">Loading syntax highlighter...</p>
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

        {/* No File Selected */}
        {!isLoading && !error && !fileContent && (
          <div className="file-viewer-empty">
            <FileTextIcon className="file-viewer-empty-icon" />
            <p className="file-viewer-empty-title">Select a file to preview</p>
            <p className="file-viewer-empty-subtitle">Click a file on the left</p>
          </div>
        )}
      </div>
    </div>
  )
}

