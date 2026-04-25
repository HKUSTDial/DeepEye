import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import readExcelFile from 'read-excel-file/browser'

import type { FileContentResponse } from '../../api/sandbox'
import { useLocale } from '../../locale'

type SpreadsheetPreviewProps = {
  fileContent: FileContentResponse
  isDownloading: boolean
  onDownload: () => void
}

type SpreadsheetData = {
  sheetName: string
  rows: unknown[][]
  truncated: boolean
  loading?: boolean
  error?: string
}

export default function SpreadsheetPreview({
  fileContent,
  isDownloading,
  onDownload,
}: SpreadsheetPreviewProps) {
  const { t } = useLocale()
  const [xlsxData, setXlsxData] = useState<SpreadsheetData | null>(null)

  useEffect(() => {
    let isCancelled = false

    const parseSpreadsheet = async () => {
      if (fileContent.encoding !== 'base64') {
        if (!isCancelled) {
          setXlsxData(null)
        }
        return
      }

      try {
        setXlsxData({ sheetName: 'Sheet1', rows: [], truncated: false, loading: true })

        const binaryStr = atob(fileContent.content)
        const bytes = new Uint8Array(binaryStr.length)
        for (let i = 0; i < binaryStr.length; i++) {
          bytes[i] = binaryStr.charCodeAt(i)
        }

        const workbook = await readExcelFile(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength))
        const firstSheet = workbook[0]
        const rows = firstSheet?.data ?? []
        const sheetName = firstSheet?.sheet || 'Sheet1'

        const maxRows = 200
        const maxCols = 50
        const limitedRows = rows.slice(0, maxRows).map((row) => (Array.isArray(row) ? row.slice(0, maxCols) : []))
        const truncated = rows.length > maxRows || limitedRows.some((row) => row.length > maxCols)

        if (!isCancelled) {
          setXlsxData({ sheetName, rows: limitedRows, truncated })
        }
      } catch (error) {
        if (!isCancelled) {
          setXlsxData({
            sheetName: 'Sheet1',
            rows: [],
            truncated: false,
            error: error instanceof Error ? error.message : String(error),
          })
        }
      }
    }

    void parseSpreadsheet()

    return () => {
      isCancelled = true
    }
  }, [fileContent])

  return (
    <div className="csv-viewer">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-[var(--main-text-muted)]">
          {t('files.sheet')}: <span className="font-mono">{xlsxData?.sheetName || 'Sheet1'}</span>
          {xlsxData?.loading ? <span className="ml-2">{t('files.loadingSpreadsheet')}</span> : null}
          {xlsxData?.truncated ? <span> {t('files.showingRowsCols')}</span> : null}
          {xlsxData?.error ? (
            <span className="ml-2 text-[#ff3b30]">{t('files.parseFailed', { error: xlsxData.error })}</span>
          ) : null}
        </div>
        <button
          type="button"
          className="file-explorer-btn"
          onClick={onDownload}
          disabled={isDownloading}
          title={t('common.download')}
        >
          <Download size={14} className={isDownloading ? 'animate-spin' : ''} />
        </button>
      </div>

      <table className="csv-table">
        <tbody>
          {(xlsxData?.rows || []).map((row, rowIdx) => (
            <tr key={rowIdx}>
              <td className="csv-row-number">{rowIdx + 1}</td>
              {row.map((cell, cellIdx) => (
                <td key={cellIdx}>{cell == null ? '' : String(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
