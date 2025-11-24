/**
 * DatabaseDataSource 节点 - 数据库数据源
 * 从数据库读取数据（SQLite、MySQL、PostgreSQL）
 */

import { Node } from '@/nodes/decorators'
import { Database } from 'lucide-react'
import { nodesAPI } from '@/shared/api'

@Node({
  type: 'datasource.database',
  label: '数据库数据源',
  category: 'datasource',
  icon: Database,
  color: '#10B981',
  properties: {
    connection_string: {
      type: 'string',
      label: '连接字符串',
      description: '数据库连接字符串',
      placeholder: 'sqlite:///data.db 或 postgresql://user:pass@host/db'
    },
    query: {
      type: 'string',
      label: 'SQL 查询',
      description: 'SQL 查询语句（可选，留空则返回所有表信息）',
      placeholder: 'SELECT * FROM users LIMIT 100',
      multiline: true
    },
    max_rows: {
      type: 'number',
      label: '最大行数',
      description: '查询结果的最大行数',
      default: 100000,
      min: 1
    }
  },
  outputs: {
    data: {
      type: 'object',
      label: '数据输出',
      description: '查询模式：DataFrame 数据；内省模式：{connection_string, database_info}'
    }
  }
})
export class DatabaseDataSourceNode {
  connection_string: string = ''
  query: string = ''
  max_rows: number = 100000
  data: any = null

  async compute() {
    try {
      // 根据是否有 query 自动判断模式（小写）
      const mode = this.query && this.query.trim() ? 'query' : 'introspect'

      // 查询模式需要通过 sql 输入端口传递 SQL
      const inputs = mode === 'query' ? { sql: this.query } : {}

      const result = await nodesAPI.execute(
        'DatabaseDataSource',
        inputs,
        {
          connection_string: this.connection_string,
          mode: mode,
          max_rows: this.max_rows
        }
      )

      if (result.status === 'success') {
        // 后端只有一个输出 data
        // 内省模式: data = {connection_string, database_info}
        // 查询模式: data = {dataframe: DataFrame}
        this.data = result.outputs.data
      } else {
        throw new Error(result.error || '数据库查询失败')
      }
    } catch (error: any) {
      console.error('DatabaseDataSource 执行失败:', error)
      throw error
    }
  }
}

