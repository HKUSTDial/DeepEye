import { useMemo } from 'react'
import { Download } from 'lucide-react'
import * as XLSX from 'xlsx'

import type { FileContentResponse } from '../../api/sandbox'

type SpreadsheetPreviewProps = {
  fileContent: FileContentResponse
  isDownloading: boolean
  onDownload: () => void
}

export default function SpreadsheetPreview({
  fileContent,
  isDownloading,
  onDownload,
}: SpreadsheetPreviewProps) {
  const xlsxData = useMemo(() => {
    if (fileContent.encoding !== 'base64') return null

    try {
      const binaryStr = atob(fileContent.content)
      const bytes = new Uint8Array(binaryStr.length)
      for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i)
      }

      const workbook = XLSX.read(bytes, { type: 'array' })
      const sheetName = workbook.SheetNames[0]
      const sheet = sheetName ? workbook.Sheets[sheetName] : undefined
      if (!sheetName || !sheet) return { sheetName: 'Sheet1', rows: [], truncated: false }

      const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: true }) as unknown[][]
      const maxRows = 200
      const maxCols = 50
      const limitedRows = rows.slice(0, maxRows).map((row) => (Array.isArray(row) ? row.slice(0, maxCols) : []))
      const truncated = rows.length > maxRows || limitedRows.some((row) => row.length > maxCols)

      return { sheetName, rows: limitedRows, truncated }
    } catch (error) {
      return {
        sheetName: 'Sheet1',
        rows: [],
        truncated: false,
        error: error instanceof Error ? error.message : String(error),
      }
    }
  }, [fileContent])

  return (
    <div className="csv-viewer">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-[var(--main-text-muted)]">
          Sheet: <span className="font-mono">{xlsxData?.sheetName || 'Sheet1'}</span>
          {xlsxData?.truncated ? <span> (showing first 200 rows / 50 cols)</span> : null}
          {xlsxData && 'error' in xlsxData && xlsxData.error ? (
            <span className="ml-2 text-[#ff3b30]">Parse failed: {xlsxData.error}</span>
          ) : null}
        </div>
        <button
          type="button"
          className="file-explorer-btn"
          onClick={onDownload}
          disabled={isDownloading}
          title="Download"
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
