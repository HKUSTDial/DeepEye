import { describe, expect, it } from 'vitest'

import {
  formatConnectionSuccess,
  formatPreviewCell,
  getPreviewRangeLabel,
} from './dataSourceManagerUtils'

describe('dataSourceManagerUtils', () => {
  it('formats preview cells defensively', () => {
    expect(formatPreviewCell(null)).toBe('NULL')
    expect(formatPreviewCell(42)).toBe('42')
    expect(formatPreviewCell({ city: 'Shanghai' })).toBe('{"city":"Shanghai"}')
  })

  it('builds preview range labels from pagination metadata', () => {
    expect(
      getPreviewRangeLabel({
        datasource_id: 'ds-1',
        datasource_name: 'sales_db',
        category: 'database',
        table: 'sales',
        columns: [],
        rows: [],
        tables: [],
        total_rows: 52,
        page: 2,
        total_pages: 3,
        page_size: 25,
      }),
    ).toBe('26-50 / 52')
  })

  it('summarizes successful connection tests', () => {
    expect(
      formatConnectionSuccess({
        ok: true,
        type: 'postgres',
        table_count: 4,
        sample_tables: ['sales', 'customers', 'orders'],
      }),
    ).toContain('4 table(s) available')
  })
})
