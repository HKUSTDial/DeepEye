/**
 * AIBadge - AI 节点徽章
 * 
 * 显示在 AI 节点右上角的动画徽章
 */

import { memo } from 'react'
import { Sparkles } from 'lucide-react'
import { cn } from '@/shared/utils'

export interface AIBadgeProps {
  /** 额外的类名 */
  className?: string
}

export const AIBadge = memo(({ className }: AIBadgeProps) => {
  return (
    <div
      className={cn(
        'absolute -top-2 -right-2 z-10',
        'w-6 h-6 rounded-full',
        'bg-gradient-to-br from-purple-500 via-pink-500 to-purple-600',
        'flex items-center justify-center',
        'shadow-lg shadow-purple-500/50',
        'animate-pulse',
        className
      )}
      title="AI 辅助节点"
    >
      <Sparkles className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
    </div>
  )
})

AIBadge.displayName = 'AIBadge'

