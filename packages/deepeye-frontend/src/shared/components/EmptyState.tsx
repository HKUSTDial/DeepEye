/**
 * EmptyState - 空状态组件
 * 
 * 用于显示统一的空状态界面
 */

import { LucideIcon } from 'lucide-react'
import { cn } from '@/shared/utils'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  className?: string
}

export function EmptyState({ icon: Icon, title, description, className }: EmptyStateProps) {
  return (
    <div className={cn("flex-1 flex items-center justify-center", className)}>
      <div className="text-center px-4">
        <Icon className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-50" />
        <p className="text-sm text-muted-foreground">{title}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </div>
    </div>
  )
}

