/**
 * NodeHeader - 节点头部组件
 * 
 * 显示节点的图标、标签和颜色
 */

import { memo } from 'react'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/shared/utils'

export interface NodeHeaderProps {
  /** 节点标签 */
  label: string
  /** 节点图标 */
  icon?: LucideIcon
  /** 节点颜色 */
  color?: string
  /** 是否选中 */
  selected?: boolean
  /** 额外的类名 */
  className?: string
  /** 右侧插槽（用于 AI 徽章等） */
  rightSlot?: React.ReactNode
}

export const NodeHeader = memo(({
  label,
  icon: Icon,
  color = '#5856D6',
  selected = false,
  className,
  rightSlot
}: NodeHeaderProps) => {
  return (
    <div
      className={cn(
        'px-3 py-2 text-white text-sm font-semibold flex items-center gap-2',
        'rounded-t-lg',
        selected && 'node-header-selected',
        className
      )}
      style={{ backgroundColor: color }}
    >
      {Icon && <Icon className="w-4 h-4 flex-shrink-0" strokeWidth={2.5} />}
      <span className="flex-1 truncate">{label}</span>
      {rightSlot}
    </div>
  )
})

NodeHeader.displayName = 'NodeHeader'

