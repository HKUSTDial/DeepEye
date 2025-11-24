/**
 * NodePorts - 节点端口组件
 * 
 * 显示节点的输入和输出端口
 */

import { memo } from 'react'
import { Handle, Position } from 'reactflow'
import { cn } from '@/shared/utils'
import type { InputDefinition, OutputDefinition } from '@/nodes/types'

// ============================================================================
// 样式配置
// ============================================================================

const STYLE_CONFIG = {
  /** 端口和文字之间的水平间距 */
  portTextGap: 'gap-10',
  /** 端口之间的垂直间距 */
  portVerticalSpacing: 'space-y-2',
  /** 输入端口文字左内边距 */
  inputTextPadding: 'pl-2',
  /** 输出端口文字右内边距 */
  outputTextPadding: 'pr-2',
} as const

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 根据数据类型获取端口颜色
 */
export function getPortColor(type: string): string {
  switch (type) {
    case 'number':
      return 'bg-blue-500'
    case 'string':
      return 'bg-green-500'
    case 'boolean':
      return 'bg-purple-500'
    case 'object':
      return 'bg-orange-500'
    case 'array':
      return 'bg-pink-500'
    case 'any':
      return 'bg-gray-500'
    default:
      return 'bg-gray-400'
  }
}

// ============================================================================
// 组件
// ============================================================================

export interface NodePortsProps {
  /** 输入端口定义 */
  inputs: Record<string, InputDefinition>
  /** 输出端口定义 */
  outputs: Record<string, OutputDefinition>
  /** 额外的类名 */
  className?: string
}

export const NodePorts = memo(({
  inputs,
  outputs,
  className
}: NodePortsProps) => {
  const inputEntries = Object.entries(inputs || {})
  const outputEntries = Object.entries(outputs || {})
  const hasNoPorts = inputEntries.length === 0 && outputEntries.length === 0

  return (
    <div className={cn('px-3 py-2 bg-card rounded-b-lg', className)}>
      <div className="flex justify-between items-start">
        {/* 左侧输入端口 */}
        <div className="flex-1">
          {inputEntries.length > 0 && (
            <div className={STYLE_CONFIG.portVerticalSpacing}>
              {inputEntries.map(([key, input]) => (
                <div key={key} className={cn('relative flex items-center', STYLE_CONFIG.portTextGap)}>
                  <Handle
                    type="target"
                    position={Position.Left}
                    id={key}
                    className={cn(
                      'w-3 h-3 border-2 border-card',
                      '!left-[-6px]',
                      getPortColor(input.type)
                    )}
                    style={{ transform: 'translate(-50%, -50%)' }}
                  />
                  <span className={cn('text-xs text-foreground', STYLE_CONFIG.inputTextPadding)}>
                    {input.label || key}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 右侧输出端口 */}
        <div className="flex-1">
          {outputEntries.length > 0 && (
            <div className={STYLE_CONFIG.portVerticalSpacing}>
              {outputEntries.map(([key, output]) => (
                <div key={key} className={cn('relative flex items-center justify-end', STYLE_CONFIG.portTextGap)}>
                  <span className={cn('text-xs text-foreground', STYLE_CONFIG.outputTextPadding)}>
                    {output.label || key}
                  </span>
                  <Handle
                    type="source"
                    position={Position.Right}
                    id={key}
                    className={cn(
                      'w-3 h-3 border-2 border-card',
                      '!right-[-6px]',
                      getPortColor(output.type)
                    )}
                    style={{ transform: 'translate(50%, -50%)' }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 如果没有端口，显示提示 */}
      {hasNoPorts && (
        <div className="text-xs text-muted-foreground text-center py-1">
          No ports
        </div>
      )}
    </div>
  )
})

NodePorts.displayName = 'NodePorts'

