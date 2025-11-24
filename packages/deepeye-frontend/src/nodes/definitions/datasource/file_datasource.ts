/**
 * FileDataSource 节点 - 文件数据源
 * 从本地文件或 URL 读取数据（CSV、JSON、Excel）
 */

import { Node } from '@/nodes/decorators'
import { FileText } from 'lucide-react'
import { nodesAPI } from '@/shared/api'

@Node({
  type: 'datasource.file',
  label: '文件数据源',
  category: 'datasource',
  icon: FileText,
  color: '#10B981',
  properties: {
    file_path: {
      type: 'string',
      label: '文件路径',
      description: '本地文件路径或 URL',
      placeholder: 'data/sales.csv 或 https://example.com/data.csv'
    },
    file_type: {
      type: 'select',
      label: '文件类型',
      description: '文件格式（auto 自动检测）',
      options: [
        { label: '自动检测', value: 'auto' },
        { label: 'CSV', value: 'csv' },
        { label: 'JSON', value: 'json' },
        { label: 'Excel', value: 'excel' }
      ],
      default: 'auto'
    },
    delimiter: {
      type: 'string',
      label: 'CSV 分隔符',
      description: 'CSV 文件的分隔符',
      default: ','
    },
    encoding: {
      type: 'string',
      label: '文件编码',
      description: '文件编码格式',
      default: 'utf-8'
    },
    nrows: {
      type: 'number',
      label: '最大行数',
      description: '读取的最大行数（0 表示不限制）',
      default: 0,
      min: 0
    },
    allow_remote: {
      type: 'boolean',
      label: '允许远程 URL',
      description: '是否允许从 URL 读取数据',
      default: true
    }
  },
  outputs: {
    data: {
      type: 'object',
      label: '数据输出',
      description: 'DataFrame 数据'
    }
  }
})
export class FileDataSourceNode {
  file_path: string = ''
  file_type: string = 'auto'
  delimiter: string = ','
  encoding: string = 'utf-8'
  nrows: number = 0
  allow_remote: boolean = true
  data: any = null

  async compute() {
    // 调用后端 API 执行文件读取
    try {
      const result = await nodesAPI.execute(
        'FileDataSource',
        {}, // 没有输入
        {
          file_path: this.file_path,
          file_type: this.file_type,
          delimiter: this.delimiter,
          encoding: this.encoding,
          nrows: this.nrows > 0 ? this.nrows : null,  // 0 表示不限制，传 null 给后端
          allow_remote: this.allow_remote
        }
      )

      if (result.status === 'success') {
        this.data = result.outputs.data
      } else {
        throw new Error(result.error || '文件读取失败')
      }
    } catch (error: any) {
      console.error('FileDataSource 执行失败:', error)
      throw error
    }
  }
}

