import type { FileContentResponse } from '../api/sandbox'

export const CODE_EXTENSIONS = new Set([
  'py',
  'js',
  'ts',
  'jsx',
  'tsx',
  'json',
  'html',
  'css',
  'xml',
  'yaml',
  'yml',
  'vue',
  'sh',
  'bash',
  'sql',
])

export function getFileName(filePath: string | null) {
  return filePath?.split('/').pop() || ''
}

export function getFileExtension(fileName: string) {
  return fileName.includes('.') ? fileName.split('.').pop()?.toLowerCase() || '' : ''
}

export function getFileViewerType(
  fileContent: FileContentResponse | null,
  fileExtension: string,
) {
  if (!fileContent) return 'none'

  if (fileContent.content_type === 'image') {
    return 'image'
  }

  if (fileContent.content_type === 'binary') {
    if (fileExtension === 'xlsx' || fileExtension === 'xls') return 'xlsx'
    return 'binary'
  }

  if (fileExtension === 'md') return 'markdown'
  if (fileExtension === 'csv') return 'csv'
  if (CODE_EXTENSIONS.has(fileExtension)) return 'code'
  return 'text'
}

export function parseCsvPreviewData(content: string) {
  const lines = content.trim().split('\n')
  if (lines.length === 0 || !lines[0]) return null

  return {
    headers: lines[0].split(',').map((header) => header.trim()),
    rows: lines.slice(1).map((line) => line.split(',').map((cell) => cell.trim())),
  }
}

export function getFileIconColor(fileExtension: string) {
  const colorMap: Record<string, string> = {
    py: '#3572A5',
    js: '#f1e05a',
    ts: '#3178c6',
    json: '#cbcb41',
    html: '#e34c26',
    css: '#563d7c',
    vue: '#41b883',
    md: '#083fa1',
    csv: '#217346',
  }

  return colorMap[fileExtension] || '#75beff'
}
