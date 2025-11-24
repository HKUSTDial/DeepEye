/**
 * NL2SQL 节点 - 自然语言转 SQL
 * 将自然语言问题转换为 SQL 查询并执行
 */

import { Node } from '@/nodes/decorators'
import { Database } from 'lucide-react'
import { nodesAPI } from '@/shared/api'

@Node({
  type: 'ai.nl2sql',
  label: 'NL2SQL',
  category: 'ai',
  icon: Database,
  color: '#8B5CF6',
  inputs: {
    database: {
      type: 'object',
      label: '数据库信息',
      description: '数据库连接字符串和 schema 信息',
      required: true
    }
  },
  properties: {
    max_rows: {
      type: 'number',
      label: '最大行数',
      description: '查询结果的最大行数',
      default: 100000,
      min: 1
    },
    verbose: {
      type: 'boolean',
      label: '详细日志',
      description: '是否输出详细的执行日志',
      default: false
    }
  },
  outputs: {
    sql: {
      type: 'string',
      label: '生成的 SQL',
      description: 'LLM 生成的 SQL 查询语句'
    },
    data: {
      type: 'object',
      label: '查询结果',
      description: 'SQL 查询结果 DataFrame'
    },
    explanation: {
      type: 'string',
      label: 'SQL 解释',
      description: 'SQL 的自然语言解释'
    }
  },
  ai: {
    enableChat: true,
    placeholder: '输入问题，如：找出销售额前10的产品'
  },
  viewData: {
    data: {
      label: '查询结果',
      maxRows: 5,
      showIndex: true
    }
  }
})
export class NL2SQLNode {
  database: any = null
  max_rows: number = 100000
  verbose: boolean = false
  sql: string = ''
  data: any = null
  explanation: string = ''

  /**
   * 处理 AI 请求
   * 当用户在聊天框中输入 prompt 并点击执行时调用
   * @param prompt 用户输入的提示词（自然语言问题）
   * @param modelId 选中的模型 ID
   */
  async handleAIRequest(prompt: string, modelId: string) {
    try {
      // 检查必要的输入
      if (!this.database) {
        throw new Error('请先连接数据库（database 输入端口）')
      }

      // 检查输入数据类型
      if (typeof this.database !== 'object' || !this.database) {
        throw new Error('database 输入数据格式错误')
      }

      // 检查是否是 DataFrame 格式
      if ('type' in this.database && this.database.type === 'DataFrame') {
        throw new Error('❌ NL2SQL 节点需要连接到 DatabaseDataSource 节点的 data 输出端口（内省模式）\n\n' +
          '💡 提示：请确保 DatabaseDataSource 节点的 "SQL 查询" 属性为空，这样它会输出数据库结构信息而不是查询结果。\n\n' +
          '如果你想基于已有的 DataFrame 进行查询，请使用 DataCoder 节点。')
      }

      // 检查是否包含必要的字段
      if (!('connection_string' in this.database) || !('database_info' in this.database)) {
        throw new Error('❌ database 输入必须包含 connection_string 和 database_info\n\n' +
          '💡 提示：请连接到 DatabaseDataSource 节点的 data 输出端口（内省模式）')
      }

      // 调用后端 node execute API
      const result = await nodesAPI.execute(
        'NL2SQL',
        {
          database: this.database,
          query: prompt
        },
        {
          model: modelId,
          max_rows: this.max_rows,
          verbose: this.verbose
        }
      )

      if (result.status === 'success') {
        // 更新节点属性
        const outputData = result.outputs.data
        this.sql = outputData.sql || ''
        this.data = outputData.dataframe || null
        this.explanation = outputData.explanation || ''

        // 返回成功消息
        return {
          role: 'assistant' as const,
          content: `✅ SQL 已生成并执行：\n\n\`\`\`sql\n${this.sql}\n\`\`\`\n\n📝 解释：${this.explanation}\n\n📊 查询返回 ${this.data?.preview?.length || 0} 行数据`
        }
      } else {
        throw new Error(result.error || 'NL2SQL 执行失败')
      }
    } catch (error: any) {
      console.error('NL2SQL AI 请求失败:', error)
      return {
        role: 'assistant' as const,
        content: `❌ 生成 SQL 失败: ${error.message}`
      }
    }
  }

  async compute() {
    console.log('NL2SQLNode.compute() called, current data:', this.data)
  }
}

