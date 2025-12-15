/**
 * DataCoder 节点 - 智能数据处理器
 * 使用 LLM 将自然语言转换为 Python 代码并执行
 */

import { Node } from '@/nodes/decorators'
import { Code2 } from 'lucide-react'
import { nodesAPI } from '@/shared/api'

@Node({
  type: 'ai.datacoder',
  label: '智能数据处理',
  category: 'ai',
  icon: Code2,
  color: '#8B5CF6',
  inputs: {
    data: {
      type: 'object',
      label: '输入数据',
      description: 'DataFrame 数据或 DataFrame 列表',
      required: true
    }
  },
  properties: {
    task: {
      type: 'string',
      label: '任务描述',
      description: '自然语言描述的数据处理任务',
      placeholder: '过滤、转换、统计、合并等操作',
      multiline: true
    },
    model: {
      type: 'model-select',
      label: 'LLM 模型',
      description: 'LLM 模型名称',
      default: 'gpt-4'
    },
    max_retries: {
      type: 'number',
      label: '最大重试次数',
      description: '代码执行失败时的最大重试次数',
      default: 3,
      min: 0,
      max: 10
    },
    verbose: {
      type: 'boolean',
      label: '详细日志',
      description: '是否输出详细的执行日志',
      default: false
    }
  },
  outputs: {
    result: {
      type: 'object',
      label: '处理结果',
      description: '处理后的 DataFrame 数据'
    },
    code: {
      type: 'string',
      label: '生成的代码',
      description: 'LLM 生成的 Python 代码'
    }
  },
  ai: {
    enableChat: true,
    placeholder: '输入数据处理任务，如：过滤年龄大于28岁的员工，并按薪水降序排列'
  },
  viewData: {
    result: {
      label: '处理结果',
      maxRows: 5,
      showIndex: true
    }
  }
})
export class DataCoderNode {
  data: any = null
  task: string = ''
  model: string = 'gpt-4'
  max_retries: number = 3
  verbose: boolean = false
  result: any = null
  code: string = ''

  /**
   * 处理 AI 请求
   * @param prompt 用户输入的任务描述
   * @param modelId 选中的模型 ID
   */
  async handleAIRequest(prompt: string, modelId: string) {
    try {
      // 检查必要的输入
      if (!this.data) {
        throw new Error('请先连接数据源（data 输入端口）')
      }

      // 包装数据为后端期望的格式
      // 后端期望: {dataframe: <DataFrame>} 或 {dataframe_list: [<DataFrame>, ...]}
      let dataInput: any
      if (Array.isArray(this.data)) {
        // 多 DataFrame 模式
        dataInput = { dataframe_list: this.data }
      } else {
        // 单 DataFrame 模式
        dataInput = { dataframe: this.data }
      }

      // 调用后端 node execute API
      const result = await nodesAPI.execute(
        'DataCoder',
        {
          data: dataInput,
          task: { description: prompt }
        },
        {
          model: modelId || this.model,
          max_retries: this.max_retries,
          verbose: this.verbose
        }
      )

      if (result.status === 'success') {
        // 更新节点属性
        this.task = prompt
        this.code = result.outputs.code || ''

        // 提取 dataframe 数据
        // 后端可能返回以下几种格式：
        // 1. { dataframe: {...} }  - 包装格式
        // 2. { type: 'DataFrame', ... } - 直接 DataFrame 格式
        // 3. 其他格式
        const outputData = result.outputs.result

        console.log('🔍 DataCoder 后端返回数据:', {
          outputData,
          hasDataframe: outputData?.dataframe,
          isDataFrame: outputData?.type === 'DataFrame'
        })

        // 优先提取 dataframe 字段，如果不存在则检查是否本身就是 DataFrame
        if (outputData?.dataframe) {
          this.result = outputData.dataframe
        } else if (outputData?.type === 'DataFrame') {
          this.result = outputData
        } else {
          this.result = outputData || null
        }

        // 返回成功消息
        const rowCount = this.result?.preview?.length || this.result?.shape?.[0] || 0
        return {
          role: 'assistant' as const,
          content: `✅ 代码已生成并执行：\n\n\`\`\`python\n${this.code}\n\`\`\`\n\n📊 处理完成，返回 ${rowCount} 行数据`
        }
      } else {
        throw new Error(result.error || 'DataCoder 执行失败')
      }
    } catch (error: any) {
      console.error('DataCoder AI 请求失败:', error)
      return {
        role: 'assistant' as const,
        content: `❌ 处理失败: ${error.message}`
      }
    }
  }

  async compute() {
  }
}

