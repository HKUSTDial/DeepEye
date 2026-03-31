import { describe, expect, it } from 'vitest'

import {
  getFileExtension,
  getFileIconColor,
  getFileName,
  getFileViewerType,
  parseCsvPreviewData,
} from './fileViewerUtils'

describe('fileViewerUtils', () => {
  it('derives file names and extensions from sandbox paths', () => {
    expect(getFileName('/workspace/report.md')).toBe('report.md')
    expect(getFileExtension('report.md')).toBe('md')
    expect(getFileExtension('README')).toBe('')
  })

  it('selects viewer types from file metadata and extensions', () => {
    expect(
      getFileViewerType(
        { path: '/workspace/report.md', content: 'hello', content_type: 'text', encoding: 'utf-8' },
        'md',
      ),
    ).toBe('markdown')
    expect(
      getFileViewerType(
        { path: '/workspace/app.py', content: 'hello', content_type: 'text', encoding: 'utf-8' },
        'py',
      ),
    ).toBe('code')
    expect(
      getFileViewerType(
        {
          path: '/workspace/report.xlsx',
          content: 'base64...',
          content_type: 'binary',
          encoding: 'base64',
        },
        'xlsx',
      ),
    ).toBe('xlsx')
  })

  it('parses csv preview rows and keeps known icon colors stable', () => {
    expect(parseCsvPreviewData('city,revenue\nShanghai,120\nHangzhou,95')).toEqual({
      headers: ['city', 'revenue'],
      rows: [
        ['Shanghai', '120'],
        ['Hangzhou', '95'],
      ],
    })
    expect(getFileIconColor('py')).toBe('#3572A5')
    expect(getFileIconColor('unknown')).toBe('#75beff')
  })
})
