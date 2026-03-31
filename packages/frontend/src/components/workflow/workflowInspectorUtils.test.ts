import { describe, expect, it } from 'vitest'

import {
  formatDatasourceOptionLabel,
  formatOutputLabel,
  getDatasourceCategoryForNodeType,
  getPreviewColumns,
  stringifyParams,
} from './workflowInspectorUtils'

describe('workflowInspectorUtils', () => {
  it('formats workflow param values and labels predictably', () => {
    expect(stringifyParams({ limit: 10, enabled: true })).toEqual({
      limit: '10',
      enabled: 'true',
    })
    expect(formatOutputLabel('preview_rows')).toBe('Preview Rows')
  })

  it('derives datasource helpers from node metadata', () => {
    expect(getDatasourceCategoryForNodeType('sql.execute')).toBe('database')
    expect(
      formatDatasourceOptionLabel({
        id: 'ds-1',
        name: 'sales warehouse',
        type: 'postgres',
        category: 'database',
        created_at: '2026-03-31T00:00:00Z',
      }),
    ).toContain('DB')
  })

  it('keeps preview columns stable across rows', () => {
    expect(getPreviewColumns([{ city: 'Shanghai', revenue: 1 }, { city: 'Hangzhou', orders: 2 }])).toEqual([
      'city',
      'revenue',
      'orders',
    ])
  })
})
