/**
 * DataPlot 节点 - 智能数据可视化
 * 使用 LLM 将自然语言转换为可视化代码并生成图表
 */

import { Node } from '@/nodes/decorators'
import { BarChart3 } from 'lucide-react'
import { nodesAPI } from '@/shared/api'

@Node({
  type: 'ai.dataplot',
  label: '智能数据可视化',
  category: 'ai',
  icon: BarChart3,
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
      description: '自然语言描述的可视化任务',
      placeholder: '折线图、柱状图、散点图、热力图等',
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
    images: {
      type: 'array',
      label: '生成的图片',
      description: '图片列表（PNG 格式）'
    },
    code: {
      type: 'string',
      label: '生成的代码',
      description: 'LLM 生成的可视化代码'
    }
  },
  ai: {
    enableChat: true,
    placeholder: '输入可视化任务，如：绘制月度销售额折线图'
  }
})
export class DataPlotNode {
  data: any = null
  task: string = ''
  model: string = 'gpt-4'
  max_retries: number = 3
  verbose: boolean = false
  images: any[] = []
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
      let dataInput: any
      if (Array.isArray(this.data)) {
        dataInput = { dataframe_list: this.data }
      } else {
        dataInput = { dataframe: this.data }
      }

      const result = await nodesAPI.execute(
        'DataPlot',
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
        this.images = result.outputs.images || []
        this.code = result.outputs.code || ''
        this.task = prompt
        
        return {
            role: 'assistant' as const,
            content: `✅ 可视化完成，已生成 ${this.images.length} 张图表`
        }
      } else {
        throw new Error(result.error || '数据可视化失败')
      }
    } catch (error: any) {
      console.error('DataPlot 执行失败:', error)
      throw error
    }
  }

  async compute() {
    try {
      // 检查必要的输入
      if (!this.data) {
        throw new Error('请先连接数据源（data 输入端口）')
      }

      if (!this.task || this.task.trim() === '') {
        throw new Error('请输入可视化任务描述')
      }

      // 包装数据为后端期望的格式
      let dataInput: any
      if (Array.isArray(this.data)) {
        dataInput = { dataframe_list: this.data }
      } else {
        dataInput = { dataframe: this.data }
      }

      const result = await nodesAPI.execute(
        'DataPlot',
        {
          data: dataInput,
          task: { description: this.task }
        },
        {
          model: this.model,
          max_retries: this.max_retries,
          verbose: this.verbose
        }
      )

      if (result.status === 'success') {
        this.images = result.outputs.images || []
        // code 在 outputs 中
        this.code = result.outputs.code || ''
      } else {
        throw new Error(result.error || '数据可视化失败')
      }
    } catch (error: any) {
      console.error('DataPlot 执行失败:', error)
      throw error
    }
  }
}

