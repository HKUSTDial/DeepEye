import { describe, expect, it } from 'vitest'

import {
  getArtifactFileName,
  getArtifactHtml,
  getArtifactPreviewUrl,
  getArtifactTaskId,
  latestArtifactByKind,
} from './artifactUtils'

describe('artifactUtils', () => {
  it('prefers normalized preview URLs over legacy URL fields', () => {
    expect(
      getArtifactPreviewUrl({
        kind: 'dashboard',
        dashboard_url: 'https://example.com/legacy-dashboard',
        preview: { type: 'url', url: 'https://example.com/normalized-dashboard' },
      }),
    ).toBe('https://example.com/normalized-dashboard')

    expect(
      getArtifactPreviewUrl({
        kind: 'video',
        payload: { video_url: 'https://example.com/payload-video' },
      }),
    ).toBe('https://example.com/payload-video')
  })

  it('reads report content and filenames through preview and file metadata', () => {
    const artifact = {
      kind: 'report',
      preview: { type: 'html', content_key: 'html_body' },
      payload: { html_body: '<h1>Report</h1>' },
      files: [{ role: 'report', name: 'analysis.html', path: '/workspace/analysis.html' }],
    }

    expect(getArtifactHtml(artifact)).toBe('<h1>Report</h1>')
    expect(getArtifactFileName(artifact, 'report')).toBe('analysis.html')
  })

  it('finds the latest artifact and reads task id from payload fallback', () => {
    const latest = latestArtifactByKind(
      [
        { kind: 'video', payload: { task_id: '20260331_010203' } },
        { kind: 'dashboard', preview: { type: 'url', url: '/dashboards/demo/' } },
        { kind: 'video', task_id: '20260401_010203' },
      ],
      'video',
    )

    expect(getArtifactTaskId(latest)).toBe('20260401_010203')
  })
})
