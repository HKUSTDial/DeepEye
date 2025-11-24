/**
 * WorkflowCard - 工作流卡片组件
 */

import { WorkflowListItem } from '@/shared/api'
import { Clock, Tag, Trash2, Edit, FileText } from 'lucide-react'

interface WorkflowCardProps {
  workflow: WorkflowListItem
  onOpen: (id: string) => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
}

export function WorkflowCard({ workflow, onOpen, onEdit, onDelete }: WorkflowCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) return '今天'
    if (days === 1) return '昨天'
    if (days < 7) return `${days} 天前`

    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
    })
  }

  return (
    <div
      onClick={() => onOpen(workflow.id)}
      className="group relative cursor-pointer rounded-lg border bg-card p-5 transition-all hover:border-primary/50 hover:shadow-md"
    >
      {/* 标题区域 */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="truncate text-base font-semibold text-card-foreground">
            {workflow.name}
          </h3>
          {workflow.description && (
            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
              {workflow.description}
            </p>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit(workflow.id)
            }}
            className="rounded p-1.5 text-muted-foreground hover:bg-secondary hover:text-primary"
            title="编辑信息"
          >
            <Edit size={16} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete(workflow.id)
            }}
            className="rounded p-1.5 text-muted-foreground hover:bg-secondary hover:text-destructive"
            title="删除"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* 标签 */}
      {workflow.tags && workflow.tags.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {workflow.tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="inline-flex items-center gap-1 rounded bg-secondary px-2 py-0.5 text-xs text-secondary-foreground"
            >
              <Tag size={10} />
              {tag}
            </span>
          ))}
          {workflow.tags.length > 3 && (
            <span className="inline-flex items-center rounded bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
              +{workflow.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* 底部信息 */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Clock size={12} />
          <span>{formatDate(workflow.updated_at || workflow.created_at)}</span>
        </div>
        <div className="flex items-center gap-1">
          <FileText size={12} />
          <span>v{workflow.version}</span>
        </div>
      </div>
    </div>
  )
}

