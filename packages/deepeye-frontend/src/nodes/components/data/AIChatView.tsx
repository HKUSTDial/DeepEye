/**
 * AI 数据过滤器视图组件
 *
 * 在节点内部显示数据表格
 */

import type { NodeViewProps } from '@/nodes/types'

// Mock 数据
const MOCK_DATA = [
  { id: 1, name: '张三', age: 18, score: 85 },
  { id: 2, name: '李四', age: 15, score: 92 },
  { id: 3, name: '王五', age: 17, score: 78 },
  { id: 4, name: '赵六', age: 16, score: 88 },
  { id: 5, name: '钱七', age: 19, score: 95 }
]

export const AIChatView = ({ attributes }: NodeViewProps) => {
  // 使用 attributes 中的数据，如果没有则使用 mock 数据
  const data = attributes?.input_data || MOCK_DATA
  const outputData = attributes?.output_data || data

  // 获取表头（从第一条数据）
  const headers = outputData.length > 0 && typeof outputData[0] === 'object'
    ? Object.keys(outputData[0])
    : []

  return (
    <div className="w-full text-xs">
      {/* 数据表格 */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100 dark:bg-gray-800">
              {headers.map((header) => (
                <th
                  key={header}
                  className="px-2 py-1 text-left font-medium text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {outputData.slice(0, 3).map((item: any, idx: number) => (
              <tr
                key={idx}
                className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
              >
                {headers.map((header) => (
                  <td
                    key={header}
                    className="px-2 py-1 text-gray-600 dark:text-gray-400"
                  >
                    {String(item[header] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 数据统计 */}
      {outputData.length > 3 && (
        <div className="px-2 py-1 text-center text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-800/50">
          还有 {outputData.length - 3} 条数据...
        </div>
      )}
    </div>
  )
}

