/**
 * WorkflowListPage - 工作流列表页面
 */

import { useState, useEffect } from 'react'
import { toast } from '@/store'
import { workflowAPI, WorkflowListItem } from '@/shared/api'
import { WorkflowCard } from './WorkflowCard'
import { CreateWorkflowDialog } from './CreateWorkflowDialog'
import { EditWorkflowDialog } from './EditWorkflowDialog'
import { ConfirmDialog, ThemeToggle } from '@/shared/components'
import { Plus, Loader2, Search } from 'lucide-react'

interface WorkflowListPageProps {
  onOpenWorkflow: (workflowId: string) => void
}

export function WorkflowListPage({ onOpenWorkflow }: WorkflowListPageProps) {
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowListItem | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean
    title: string
    message: string
    onConfirm: () => void
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  })

  useEffect(() => {
    loadWorkflows()
  }, [])

  const loadWorkflows = async () => {
    setIsLoading(true)
    try {
      const data = await workflowAPI.list()
      setWorkflows(data)
    } catch (error) {
      console.error('加载工作流失败:', error)
      toast.error('加载工作流失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async (data: { name: string; description?: string; tags?: string[] }) => {
    try {
      const newWorkflow = await workflowAPI.create({
        name: data.name,
        description: data.description,
        tags: data.tags,
        workflow_data: {
          nodes: [],
          edges: [],
          viewport: { x: 0, y: 0, zoom: 1 },
        },
      })
      toast.success('工作流创建成功')
      // 创建成功后直接打开编辑器
      onOpenWorkflow(newWorkflow.id)
    } catch (error) {
      console.error('创建工作流失败:', error)
      toast.error('创建工作流失败')
      throw error
    }
  }

  const handleEdit = (workflowId: string) => {
    const workflow = workflows.find(w => w.id === workflowId)
    if (workflow) {
      setEditingWorkflow(workflow)
    }
  }

  const handleSaveEdit = async (
    workflowId: string,
    data: { name: string; description?: string; tags?: string[] }
  ) => {
    try {
      await workflowAPI.update(workflowId, data)
      // 更新本地列表
      setWorkflows(workflows.map(w =>
        w.id === workflowId
          ? { ...w, ...data }
          : w
      ))
      toast.success('工作流已更新')
    } catch (error) {
      console.error('更新工作流失败:', error)
      toast.error('更新工作流失败')
      throw error
    }
  }

  const handleDelete = async (workflowId: string) => {
    const workflow = workflows.find(w => w.id === workflowId)
    if (!workflow) return

    setConfirmDialog({
      isOpen: true,
      title: '删除工作流',
      message: `确定要删除工作流 "${workflow.name}" 吗？此操作无法撤销。`,
      onConfirm: async () => {
        try {
          await workflowAPI.delete(workflowId)
          setWorkflows(workflows.filter(w => w.id !== workflowId))
          toast.success('工作流已删除')
        } catch (error) {
          console.error('删除工作流失败:', error)
          toast.error('删除工作流失败')
        } finally {
          setConfirmDialog({ ...confirmDialog, isOpen: false })
        }
      },
    })
  }

  const filteredWorkflows = workflows.filter(workflow =>
    workflow.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    workflow.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    workflow.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div className="flex h-full flex-col bg-background">
      {/* 顶部栏 */}
      <header className="border-b bg-card px-6 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              我的工作流
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              管理和编辑您的数据分析工作流
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* 主要内容区 */}
      <main className="flex-1 overflow-y-auto px-6 py-6">
        {/* 操作栏 */}
        <div className="mb-6 flex items-center justify-between gap-4">
          {/* 搜索框 */}
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={20} />
            <input
              type="text"
              placeholder="搜索工作流..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border bg-background py-2 pl-10 pr-4 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* 新建按钮 */}
          <button
            onClick={() => setIsCreateDialogOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            <Plus size={20} />
            新建工作流
          </button>
        </div>

        {/* 工作流列表 */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : filteredWorkflows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="text-center">
              <p className="text-lg font-medium text-foreground">
                {searchQuery ? '没有找到匹配的工作流' : '还没有工作流'}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {searchQuery ? '尝试使用其他关键词搜索' : '点击"新建工作流"开始创建'}
              </p>
              {!searchQuery && (
                <button
                  onClick={() => setIsCreateDialogOpen(true)}
                  className="mt-6 inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-primary-foreground hover:bg-primary/90"
                >
                  <Plus size={20} />
                  新建工作流
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredWorkflows.map((workflow) => (
              <WorkflowCard
                key={workflow.id}
                workflow={workflow}
                onOpen={onOpenWorkflow}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </main>

      {/* 创建工作流对话框 */}
      <CreateWorkflowDialog
        isOpen={isCreateDialogOpen}
        onClose={() => setIsCreateDialogOpen(false)}
        onCreate={handleCreate}
      />

      {/* 编辑工作流对话框 */}
      <EditWorkflowDialog
        isOpen={!!editingWorkflow}
        workflow={editingWorkflow}
        onClose={() => setEditingWorkflow(null)}
        onSave={handleSaveEdit}
      />

      {/* 确认对话框 */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.title}
        message={confirmDialog.message}
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog({ ...confirmDialog, isOpen: false })}
      />
    </div>
  )
}

