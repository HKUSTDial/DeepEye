/**
 * NodeView - 节点视图组件
 *
 * 显示节点的自定义视图区域
 */

import { memo, useState, useEffect } from 'react'
import { cn } from '@/shared/utils'
import type { ViewDefinition } from '@/nodes/types'

export interface NodeViewProps {
  /** 视图定义 */
  view?: ViewDefinition
  /** 节点数据 */
  nodeData?: any
  /** 额外的类名 */
  className?: string
}

export const NodeView = memo(({
  view,
  nodeData,
  className
}: NodeViewProps) => {
  // 从 nodeData 中提取 attributes，如果没有则使用整个 nodeData
  const initialAttributes = nodeData?.attributes || nodeData || {}
  const [attributes, setAttributes] = useState(initialAttributes)

  // 当 nodeData 更新时，同步更新 attributes
  useEffect(() => {
    const newAttributes = nodeData?.attributes || nodeData || {}
    setAttributes(newAttributes)
  }, [nodeData])

  if (!view) {
    return null
  }

  const updateAttributes = (updates: Record<string, any>) => {
    setAttributes((prev: any) => ({ ...prev, ...updates }))
  }

  // 如果有自定义组件，渲染组件
  if (view.component) {
    console.log('✅ NodeView: 渲染自定义组件', view.component)
    const ViewComponent = view.component
    return (
      <div className={cn(
        'bg-card border-b border',
        className
      )}>
        <ViewComponent
          attributes={attributes}
          updateAttributes={updateAttributes}
          config={view.config || {}}
        />
      </div>
    )
  }

  // 如果有 render 函数，使用 render 函数
  if (view.render) {
    return (
      <div className={cn(
        'bg-card border-b border',
        className
      )}>
        {view.render({ attributes, updateAttributes, config: view.config || {} })}
      </div>
    )
  }

  return null
})

NodeView.displayName = 'NodeView'

