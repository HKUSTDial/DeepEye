/**
 * ConsoleLog 节点 - 控制台输出
 *
 * 用于调试工作流，将输入数据输出到浏览器控制台
 */

import { Node } from '@/nodes/decorators'
import { Terminal } from 'lucide-react'

@Node({
  type: 'debug.console_log',
  label: '控制台输出',
  category: 'debug',
  icon: Terminal,
  color: '#10B981',
  inputs: {
    input: {
      type: 'any',
      label: '输入数据',
      description: '要输出到控制台的数据'
    }
  },
  properties: {
    prefix: {
      type: 'string',
      label: '日志前缀',
      description: '在控制台输出前添加的前缀文本',
      default: '[ConsoleLog]'
    },
    level: {
      type: 'select',
      label: '日志级别',
      description: '控制台输出的级别',
      default: 'log',
      options: [
        { label: 'log', value: 'log' },
        { label: 'info', value: 'info' },
        { label: 'warn', value: 'warn' },
        { label: 'error', value: 'error' },
        { label: 'debug', value: 'debug' }
      ]
    },
    showTimestamp: {
      type: 'boolean',
      label: '显示时间戳',
      description: '是否在输出中包含时间戳',
      default: true
    },
    prettyPrint: {
      type: 'boolean',
      label: '美化输出',
      description: '是否使用 console.table 美化数组/对象输出',
      default: true
    }
  },
  outputs: {
    output: {
      type: 'any',
      label: '输出数据',
      description: '透传输入数据，方便链式调用'
    }
  },
  viewData: {
    output: {
      label: '输出内容',
      maxRows: 10,
      showIndex: true
    }
  }
})
export class ConsoleLogNode {
  input: any = null
  prefix: string = '[ConsoleLog]'
  level: 'log' | 'info' | 'warn' | 'error' | 'debug' = 'log'
  showTimestamp: boolean = true
  prettyPrint: boolean = true
  output: any = null

  /**
   * 执行节点逻辑
   */
  compute() {
    // 构建日志消息
    const timestamp = this.showTimestamp 
      ? `[${new Date().toLocaleTimeString('zh-CN', { hour12: false })}]` 
      : ''
    
    const prefix = this.prefix ? `${this.prefix}` : ''
    const header = [timestamp, prefix].filter(Boolean).join(' ')

    // 根据日志级别输出
    const consoleMethod = console[this.level] || console.log

    // 输出头部
    if (header) {
      consoleMethod(header)
    }

    // 美化输出
    if (this.prettyPrint && this.input !== null && this.input !== undefined) {
      // 如果是数组或对象，尝试使用 console.table
      if (Array.isArray(this.input)) {
        console.group(`${header} (Array, length: ${this.input.length})`)
        console.table(this.input)
        console.groupEnd()
      } else if (typeof this.input === 'object') {
        console.group(`${header} (Object)`)
        console.table(this.input)
        console.groupEnd()
      } else {
        consoleMethod(header, this.input)
      }
    } else {
      // 普通输出
      consoleMethod(header, this.input)
    }

    // 透传数据到输出端口
    this.output = this.input
  }
}

