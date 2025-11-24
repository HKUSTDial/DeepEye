/**
 * CreateWorkflowDialog - 创建工作流对话框
 */

import { useState } from 'react'
import { X, Loader2 } from 'lucide-react'

interface CreateWorkflowDialogProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (data: { name: string; description?: string; tags?: string[] }) => Promise<void>
}

export function CreateWorkflowDialog({ isOpen, onClose, onCreate }: CreateWorkflowDialogProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    tags: '',
  })
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.name.trim()) {
      setError('请输入工作流名称')
      return
    }

    setIsCreating(true)
    setError(null)

    try {
      const tags = formData.tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0)

      await onCreate({
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        tags: tags.length > 0 ? tags : undefined,
      })

      // 重置表单
      setFormData({ name: '', description: '', tags: '' })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败')
    } finally {
      setIsCreating(false)
    }
  }

  const handleClose = () => {
    if (!isCreating) {
      setFormData({ name: '', description: '', tags: '' })
      setError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-card p-6 shadow-xl">
        {/* 标题栏 */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-card-foreground">
            新建工作流
          </h2>
          <button
            onClick={handleClose}
            disabled={isCreating}
            className="rounded-lg p-1 text-muted-foreground hover:bg-secondary hover:text-foreground disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 名称 */}
          <div>
            <label className="block text-sm font-medium text-foreground">
              名称 <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              disabled={isCreating}
              placeholder="输入工作流名称"
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              autoFocus
            />
          </div>

          {/* 描述 */}
          <div>
            <label className="block text-sm font-medium text-foreground">
              描述
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              disabled={isCreating}
              placeholder="输入工作流描述（可选）"
              rows={3}
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            />
          </div>

          {/* 标签 */}
          <div>
            <label className="block text-sm font-medium text-foreground">
              标签
            </label>
            <input
              type="text"
              name="tags"
              value={formData.tags}
              onChange={handleChange}
              disabled={isCreating}
              placeholder="输入标签，用逗号分隔（可选）"
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              例如：数据分析, AI, 可视化
            </p>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* 按钮 */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isCreating}
              className="flex-1 rounded-lg border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isCreating ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  创建中...
                </>
              ) : (
                '创建'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

