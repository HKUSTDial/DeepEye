/**
 * 数据表格视图组件
 *
 * 用于显示节点中被 @ViewData 标记的数据
 * 统一处理数组格式的数据，自动提取列名和值
 */

import { cn } from '@/shared/utils'
import { useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Maximize2, Search } from 'lucide-react'

export interface DataTableViewProps {
  /** 数据 */
  data: any
  /** 显示标签 */
  label?: string
  /** 最大显示行数 */
  maxRows?: number
  /** 是否显示行号 */
  showIndex?: boolean
}

export function DataTableView({
  data,
  label,
  maxRows = 5,
  showIndex = false
}: DataTableViewProps) {
  const [showPreview, setShowPreview] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // 如果没有数据，显示空状态
  if (!data) {
    return (
      <div className="px-3 py-2 text-xs text-muted-foreground text-center">
        {label ? `${label}: ` : ''}暂无数据
      </div>
    )
  }

  // 统一数据格式转换：将所有格式转换为数组
  let tableData: any[] = []

  // 1. 如果是 DataFrame 格式，提取 preview 数组
  if (typeof data === 'object' && data.type === 'DataFrame' && data.preview) {
    tableData = data.preview
  }
  // 2. 如果有 dataframe 字段，提取其中的 preview
  else if (typeof data === 'object' && data.dataframe?.preview) {
    tableData = data.dataframe.preview
  }
  // 3. 如果直接是数组，使用它
  else if (Array.isArray(data)) {
    tableData = data
  }
  // 4. 如果是单个对象，转换为单元素数组
  else if (typeof data === 'object') {
    tableData = [data]
  }
  // 5. 其他类型，显示原始数据
  else {
    return (
      <div className="px-3 py-2 text-xs text-muted-foreground">
        {label ? `${label}: ` : ''}{String(data)}
      </div>
    )
  }

  // 如果数组为空
  if (tableData.length === 0) {
    return (
      <div className="px-3 py-2 text-xs text-muted-foreground text-center">
        {label ? `${label}: ` : ''}空数据
      </div>
    )
  }

  // 从数组第一个元素提取所有 key 作为列名
  const columns = Object.keys(tableData[0] || {})
  const totalRows = tableData.length

  // 渲染表格
  return (
    <>
      <div className="w-full">
        {renderTable(tableData, columns, totalRows, false)}
      </div>

      {/* 全屏预览弹窗 */}
      {showPreview && createPortal(
        <div
          className="fixed inset-0 z-[9999] bg-black/90 flex items-center justify-center p-4"
          onClick={() => {
            setShowPreview(false)
            setSearchQuery('')
          }}
        >
          <div
            className="bg-background rounded-lg shadow-xl w-[95vw] h-[95vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 头部 */}
            <div className="flex items-center justify-between gap-4 p-4 border-b border-border">
              <h3 className="text-base font-medium text-foreground whitespace-nowrap">
                {label || '数据预览'}
              </h3>

              {/* 搜索框 */}
              <div className="flex-1 max-w-md relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="搜索数据..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm bg-secondary/50 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              <button
                onClick={() => {
                  setShowPreview(false)
                  setSearchQuery('')
                }}
                className="p-2 rounded hover:bg-secondary transition-colors"
                title="关闭"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 表格内容 */}
            <div className="flex-1 overflow-auto mac-scrollbar p-4">
              {renderTable(tableData, columns, totalRows, true, searchQuery)}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  )

  // 渲染表格
  function renderTable(
    data: any[],
    columns: string[],
    totalRows: number,
    isFullView: boolean,
    searchFilter: string = ''
  ) {
    // 应用搜索过滤
    let filteredData = data
    if (searchFilter.trim()) {
      const query = searchFilter.toLowerCase()
      filteredData = data.filter((row) => {
        // 搜索所有列的值
        return columns.some((col) => {
          const value = row[col]
          if (value === null || value === undefined) return false
          return String(value).toLowerCase().includes(query)
        })
      })
    }

    // 在节点内部视图中，限制显示行数
    const displayData = isFullView ? filteredData : filteredData.slice(0, maxRows)
    const hasMore = totalRows > displayData.length

    // 显示搜索结果提示
    const showSearchInfo = isFullView && searchFilter.trim() && filteredData.length !== data.length

    return (
      <>
        {/* 标签和展开按钮 */}
        {label && (
          <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground bg-secondary/50 border-b flex items-center justify-between">
            <span>
              {label} ({totalRows} 行)
              {showSearchInfo && (
                <span className="ml-2 text-primary">
                  · 搜索到 {filteredData.length} 条结果
                </span>
              )}
            </span>
            {!isFullView && hasMore && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setShowPreview(true)
                }}
                onMouseDown={(e) => e.stopPropagation()}
                className="p-1 rounded hover:bg-secondary transition-colors"
                title="展开查看全部数据"
              >
                <Maximize2 className="w-3 h-3" />
              </button>
            )}
          </div>
        )}

        {/* 表格容器 */}
        <div className={cn(
          "overflow-auto mac-scrollbar",
          !isFullView && "max-h-[200px]"
        )}>
          <table className="w-full border-collapse text-xs">
            <thead className="sticky top-0 bg-secondary/30">
              <tr>
                {showIndex && (
                  <th className="px-2 py-1 text-left font-medium text-muted-foreground border-b">#</th>
                )}
                {columns.map((header) => (
                  <th
                    key={header}
                    className="px-2 py-1 text-left font-medium text-muted-foreground border-b whitespace-nowrap"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayData.map((item: any, idx: number) => (
                <tr
                  key={idx}
                  className={cn(
                    'border-b border-border/50',
                    'hover:bg-secondary/20 transition-colors'
                  )}
                >
                  {showIndex && (
                    <td className="px-2 py-1 text-muted-foreground">{idx + 1}</td>
                  )}
                  {columns.map((header) => (
                    <td
                      key={header}
                      className="px-2 py-1 text-foreground max-w-[200px] truncate"
                      title={formatValue(item[header])}
                    >
                      {formatValue(item[header])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 更多数据提示 */}
        {!isFullView && hasMore && (
          <div
            className="px-2 py-1 text-center text-muted-foreground bg-secondary/20 text-xs cursor-pointer hover:bg-secondary/30 transition-colors"
            onClick={(e) => {
              e.stopPropagation()
              setShowPreview(true)
            }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            还有 {totalRows - displayData.length} 行数据，点击展开查看
          </div>
        )}
      </>
    )
  }
}

// 格式化值的辅助函数
function formatValue(value: any): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'boolean') return value ? '✓' : '✗'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}