import { Suspense, lazy, useState, useEffect, useMemo, useCallback } from 'react'
import { X, FileCode, FileText as FileTextIcon, Download } from 'lucide-react'
import { sandboxApi, type FileContentResponse } from '../api/sandbox'
import {
  CODE_EXTENSIONS,
  getFileExtension,
  getFileIconColor,
  getFileName,
  getFileViewerType,
  parseCsvPreviewData,
} from './fileViewerUtils'
import { useCodeHighlight } from '../hooks/useCodeHighlight'
import { useTheme } from '../hooks/useTheme'
import { useLocale } from '../locale'
import { deferEffectWork } from '../utils/effects'
import './FileViewer.css'

interface FileViewerProps {
  sessionId: string | null
  filePath: string | null
  onClose: () => void
}

const MarkdownPreview = lazy(() => import('./file-viewers/MarkdownPreview'))
const SpreadsheetPreview = lazy(() => import('./file-viewers/SpreadsheetPreview'))
const CsvPreview = lazy(() => import('./file-viewers/CsvPreview'))
const LineNumberTextPreview = lazy(() => import('./file-viewers/LineNumberTextPreview'))

export default function FileViewer({ sessionId, filePath, onClose }: FileViewerProps) {
  const { t } = useLocale()
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [highlightedCode, setHighlightedCode] = useState<string>('')
  const [isDownloading, setIsDownloading] = useState(false)

  const { highlight, isInitializing: isHighlighterLoading } = useCodeHighlight()
  const { theme } = useTheme()

  const fileName = useMemo(() => getFileName(filePath), [filePath])

  const fileExtension = useMemo(() => getFileExtension(fileName), [fileName])

  const viewerType = useMemo(() => getFileViewerType(fileContent, fileExtension), [fileContent, fileExtension])

  const handleDownload = async () => {
    if (!sessionId || !filePath) return
    setIsDownloading(true)
    try {
      const { blob, filename } = await sandboxApi.download(sessionId, filePath)
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
    } finally {
      setIsDownloading(false)
    }
  }

  const csvData = useMemo(() => {
    if (viewerType !== 'csv' || !fileContent) return null
    return parseCsvPreviewData(fileContent.content)
  }, [viewerType, fileContent])

  const codeLines = useMemo(() => {
    if (!fileContent) return []
    return fileContent.content.split('\n')
  }, [fileContent])

  const iconColor = useMemo(() => getFileIconColor(fileExtension), [fileExtension])

  const loadFile = useCallback(async (sessionId: string, path: string) => {
    setIsLoading(true)
    setError(null)
    setHighlightedCode('')
    
    try {
      const content = await sandboxApi.getFileContent(sessionId, path)
      setFileContent(content)
      
      // Highlight code if it's a code file
      if (content.content_type === 'text') {
        const ext = path.split('.').pop()?.toLowerCase() || ''
        if (CODE_EXTENSIONS.has(ext)) {
          const code = await highlight(content.content, ext)
          setHighlightedCode(code)
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t('files.failedToLoadFile'))
      setFileContent(null)
    } finally {
      setIsLoading(false)
    }
  }, [highlight, t])

  useEffect(() => {
    return deferEffectWork(() => {
      if (sessionId && filePath) {
        loadFile(sessionId, filePath)
      } else {
        setFileContent(null)
        setHighlightedCode('')
      }
    })
  }, [sessionId, filePath, loadFile])

  useEffect(() => {
    if (!fileContent || viewerType !== 'code') return
    const ext = fileExtension || ''
    if (!CODE_EXTENSIONS.has(ext)) return

    let active = true
    highlight(fileContent.content, ext).then((code) => {
      if (active) setHighlightedCode(code)
    })

    return () => {
      active = false
    }
  }, [theme, fileContent, viewerType, fileExtension, highlight])

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
              title={t('common.close')}
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
            <p className="loading-text">{t('common.loading')}...</p>
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
            <p className="error-title">{t('files.failedToLoadFile')}</p>
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
          <Suspense fallback={<div className="file-viewer-loading"><div className="loading-spinner small"></div><p className="loading-text">{t('files.loadingMarkdown')}</p></div>}>
            <MarkdownPreview content={fileContent.content} />
          </Suspense>
        )}

        {/* CSV Viewer */}
        {!isLoading && !error && viewerType === 'csv' && csvData && (
          <Suspense fallback={<div className="file-viewer-loading"><div className="loading-spinner small"></div><p className="loading-text">{t('files.loadingCsv')}</p></div>}>
            <CsvPreview headers={csvData.headers} rows={csvData.rows} />
          </Suspense>
        )}

        {/* XLSX Viewer */}
        {!isLoading && !error && viewerType === 'xlsx' && fileContent && (
          <Suspense fallback={<div className="file-viewer-loading"><div className="loading-spinner small"></div><p className="loading-text">{t('files.loadingSpreadsheet')}</p></div>}>
            <SpreadsheetPreview
              fileContent={fileContent}
              isDownloading={isDownloading}
              onDownload={handleDownload}
            />
          </Suspense>
        )}

        {/* Binary Viewer */}
        {!isLoading && !error && viewerType === 'binary' && fileContent && (
          <div className="file-viewer-empty">
            <FileTextIcon className="file-viewer-empty-icon" />
            <p className="file-viewer-empty-title">{t('files.binaryUnsupportedTitle')}</p>
            <p className="file-viewer-empty-subtitle">{t('files.binaryUnsupportedSubtitle')}</p>
            <button
              type="button"
              className="file-explorer-btn mt-3"
              onClick={handleDownload}
              disabled={isDownloading}
              title={t('common.download')}
            >
              <Download size={14} className={isDownloading ? 'animate-spin' : ''} />
            </button>
          </div>
        )}

        {/* Code Viewer with Line Numbers */}
        {!isLoading && !error && viewerType === 'code' && fileContent && (
          <div className="code-viewer">
            {isHighlighterLoading && !highlightedCode ? (
              <div className="file-viewer-loading">
                <div className="loading-spinner small"></div>
                <p className="loading-text">{t('files.loadingHighlighter')}</p>
              </div>
            ) : highlightedCode ? (
              <div className="code-with-lines">
                <div dangerouslySetInnerHTML={{ __html: highlightedCode }} className="shiki-wrapper"></div>
              </div>
            ) : (
              <Suspense fallback={<div className="file-viewer-loading"><div className="loading-spinner small"></div><p className="loading-text">{t('files.loadingCode')}</p></div>}>
                <LineNumberTextPreview lines={codeLines} />
              </Suspense>
            )}
          </div>
        )}

        {/* Text Viewer with Line Numbers */}
        {!isLoading && !error && viewerType === 'text' && fileContent && (
          <Suspense fallback={<div className="file-viewer-loading"><div className="loading-spinner small"></div><p className="loading-text">{t('files.loadingText')}</p></div>}>
            <LineNumberTextPreview lines={codeLines} />
          </Suspense>
        )}

        {/* No File Selected */}
        {!isLoading && !error && !fileContent && (
          <div className="file-viewer-empty">
            <FileTextIcon className="file-viewer-empty-icon" />
            <p className="file-viewer-empty-title">{t('files.selectToPreviewTitle')}</p>
            <p className="file-viewer-empty-subtitle">{t('files.selectToPreviewSubtitle')}</p>
          </div>
        )}
      </div>
    </div>
  )
}
