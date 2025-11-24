/**
 * EditWorkflowDialog - 编辑工作流对话框
 */

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { WorkflowListItem } from '@/shared/api'

interface EditWorkflowDialogProps {
  isOpen: boolean
  workflow: WorkflowListItem | null
  onClose: () => void
  onSave: (id: string, data: { name: string; description?: string; tags?: string[] }) => Promise<void>
}

export function EditWorkflowDialog({ isOpen, workflow, onClose, onSave }: EditWorkflowDialogProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [tagsInput, setTagsInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (workflow) {
      setName(workflow.name)
      setDescription(workflow.description || '')
      setTagsInput(workflow.tags?.join(', ') || '')
    }
  }, [workflow])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!workflow || !name.trim()) return

    setIsSubmitting(true)
    try {
      const tags = tagsInput
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0)

      await onSave(workflow.id, {
        name: name.trim(),
        description: description.trim() || undefined,
        tags: tags.length > 0 ? tags : undefined,
      })
      onClose()
    } catch (error) {
      console.error('保存失败:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen || !workflow) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-card p-6 shadow-xl">
        {/* 标题栏 */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-card-foreground">
            编辑工作流
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <X size={20} />
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 名称 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground">
              名称 <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入工作流名称"
              required
              className="w-full rounded-lg border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* 描述 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground">
              描述
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="输入工作流描述（可选）"
              rows={3}
              className="w-full rounded-lg border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* 标签 */}
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground">
              标签
            </label>
            <input
              type="text"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="输入标签，用逗号分隔（可选）"
              className="w-full rounded-lg border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              例如：数据分析, 可视化, 报表
            </p>
          </div>

          {/* 按钮 */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border px-4 py-2 text-foreground hover:bg-secondary"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="rounded-lg bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

