import { useEffect, useMemo, useState } from 'react'
import { llmModelsAPI, type LLMModel, type LLMModelUpdate } from '@/shared/api'
import { ThemeToggle, ConfirmDialog, EmptyState } from '@/shared/components'
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
} from '@/shared/components/ui'
import { toast } from '@/store'
import {
  Bot,
  Cpu,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
} from 'lucide-react'

type ModelFormState = {
  model_name: string
  model_endpoint_name: string
  base_url: string
  api_key: string
}

const defaultFormState: ModelFormState = {
  model_name: '',
  model_endpoint_name: '',
  base_url: '',
  api_key: '',
}

const formatDateTime = (value?: string) => {
  if (!value) return '--'
  return new Date(value).toLocaleString()
}

const sortByUpdatedAt = (items: LLMModel[]) =>
  [...items].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )

export function LLMModelsPage() {
  const [models, setModels] = useState<LLMModel[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingModel, setEditingModel] = useState<LLMModel | null>(null)
  const [formState, setFormState] = useState<ModelFormState>(defaultFormState)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  })

  useEffect(() => {
    void loadModels()
  }, [])

  const loadModels = async () => {
    setIsLoading(true)
    try {
      const data = await llmModelsAPI.list()
      setModels(sortByUpdatedAt(data))
    } catch (error) {
      console.error('加载模型失败:', error)
      toast.error('加载模型失败')
    } finally {
      setIsLoading(false)
    }
  }

  const filteredModels = useMemo(() => {
    if (!searchQuery) return models
    const keyword = searchQuery.toLowerCase()
    return models.filter((model) =>
      [model.model_name, model.model_endpoint_name, model.base_url]
        .filter(Boolean)
        .some((field) => field?.toLowerCase().includes(keyword))
    )
  }, [models, searchQuery])

  const stats = useMemo(() => {
    if (!models.length) {
      return {
        total: 0,
        endpoints: 0,
        latest: '--',
      }
    }

    const uniqueEndpoints = new Set(
      models.map((model) => `${model.base_url}:${model.model_endpoint_name}`)
    )

    return {
      total: models.length,
      endpoints: uniqueEndpoints.size,
      latest: formatDateTime(models[0]?.updated_at),
    }
  }, [models])

  const handleDialogClose = () => {
    setIsDialogOpen(false)
    setEditingModel(null)
    setFormState(defaultFormState)
  }

  const openCreateDialog = () => {
    setEditingModel(null)
    setFormState(defaultFormState)
    setIsDialogOpen(true)
  }

  const openEditDialog = (model: LLMModel) => {
    setEditingModel(model)
    setFormState({
      model_name: model.model_name ?? '',
      model_endpoint_name: model.model_endpoint_name,
      base_url: model.base_url,
      api_key: '',
    })
    setIsDialogOpen(true)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isSubmitting) return
    if (!formState.model_endpoint_name || !formState.base_url) {
      toast.error('请完善模型基础信息')
      return
    }

    setIsSubmitting(true)
    try {
      if (editingModel) {
        const payload: LLMModelUpdate = {
          model_name: formState.model_name.trim() || null,
          model_endpoint_name: formState.model_endpoint_name.trim(),
          base_url: formState.base_url.trim(),
        }

        if (formState.api_key.trim()) {
          payload.api_key = formState.api_key.trim()
        }

        const updated = await llmModelsAPI.update(editingModel.id, payload)
        setModels((prev) =>
          sortByUpdatedAt(prev.map((item) => (item.id === updated.id ? updated : item)))
        )
        toast.success('模型已更新')
      } else {
        if (!formState.api_key.trim()) {
          toast.error('请填写 API Key')
          setIsSubmitting(false)
          return
        }
        const created = await llmModelsAPI.create({
          model_name: formState.model_name.trim() || undefined,
          model_endpoint_name: formState.model_endpoint_name.trim(),
          base_url: formState.base_url.trim(),
          api_key: formState.api_key.trim(),
        })
        setModels((prev) => sortByUpdatedAt([created, ...prev]))
        toast.success('模型已创建')
      }
      handleDialogClose()
    } catch (error) {
      console.error('保存模型失败:', error)
      toast.error('保存模型失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (modelId: string) => {
    try {
      await llmModelsAPI.delete(modelId)
      setModels((prev) => prev.filter((model) => model.id !== modelId))
      toast.success('模型已删除')
    } catch (error) {
      console.error('删除模型失败:', error)
      toast.error('删除模型失败')
    } finally {
      setConfirmDialog((prev) => ({ ...prev, isOpen: false }))
    }
  }

  const openDeleteDialog = (model: LLMModel) => {
    setConfirmDialog({
      isOpen: true,
      title: '删除模型配置',
      message: `确定要删除模型 "${model.model_name || model.model_endpoint_name}" 吗？`,
      onConfirm: () => {
        void handleDelete(model.id)
      },
    })
  }

  return (
    <div className="flex h-full flex-col bg-background">
      <header className="border-b bg-card px-6 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">模型中心</p>
            <h1 className="mt-1 text-2xl font-bold text-foreground">模型列表</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              管理可用的 LLM 服务端点，灵活切换不同厂商和模型规格
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">可用模型</CardTitle>
              <Bot className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
              <p className="text-xs text-muted-foreground">注册到工作区的模型数量</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">独立端点</CardTitle>
              <Cpu className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.endpoints}</div>
              <p className="text-xs text-muted-foreground">Base URL + Endpoint 组合</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最近更新</CardTitle>
              <Sparkles className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.latest}</div>
              <p className="text-xs text-muted-foreground">确保凭据与配置实时生效</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <CardTitle>模型配置</CardTitle>
                <CardDescription>统一管理 API Key、Base URL、模型别名</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadModels()}
                  disabled={isLoading}
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                  刷新
                </Button>
                <Button size="sm" onClick={openCreateDialog}>
                  <Plus className="h-4 w-4" />
                  新建模型
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索模型名称、端点或 Base URL..."
                  className="pl-9"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </div>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : filteredModels.length === 0 ? (
              <EmptyState
                icon={Bot}
                title={searchQuery ? '没有符合条件的模型' : '尚未配置任何模型'}
                description={
                  searchQuery ? '换一个关键词试试' : '点击“新建模型”即可快速接入自定义 LLM'
                }
                className="py-12"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                      <th className="py-3 pr-4 font-medium">模型名称</th>
                      <th className="py-3 pr-4 font-medium">Endpoint</th>
                      <th className="py-3 pr-4 font-medium">Base URL</th>
                      <th className="py-3 pr-4 font-medium">更新时间</th>
                      <th className="py-3 text-right font-medium">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredModels.map((model) => (
                      <tr key={model.id} className="border-b border-border/60 last:border-b-0">
                        <td className="py-3 pr-4">
                          <div className="font-medium text-foreground">
                            {model.model_name || model.model_endpoint_name}
                          </div>
                          <div className="text-xs text-muted-foreground">{model.id.slice(0, 8)}</div>
                        </td>
                        <td className="py-3 pr-4">
                          <div className="text-foreground">{model.model_endpoint_name}</div>
                        </td>
                        <td className="py-3 pr-4">
                          <div className="text-foreground">{model.base_url}</div>
                        </td>
                        <td className="py-3 pr-4">
                          <div className="text-foreground">{formatDateTime(model.updated_at)}</div>
                        </td>
                        <td className="py-3 text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="编辑模型"
                              onClick={() => openEditDialog(model)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="删除模型"
                              className="text-destructive"
                              onClick={() => openDeleteDialog(model)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <Dialog open={isDialogOpen} onOpenChange={(open) => (!open ? handleDialogClose() : setIsDialogOpen(true))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingModel ? '编辑模型' : '注册新模型'}</DialogTitle>
            <DialogDescription>
              {editingModel
                ? '更新模型基础信息，API Key 留空则保持不变'
                : '填写模型访问地址和 API Key，确保网络可达'}
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="model-name">模型显示名称</Label>
              <Input
                id="model-name"
                value={formState.model_name}
                onChange={(event) => setFormState((prev) => ({ ...prev, model_name: event.target.value }))}
                placeholder="例如：DeepSeek-R1-70B"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="model-endpoint">Endpoint 名称</Label>
              <Input
                id="model-endpoint"
                value={formState.model_endpoint_name}
                onChange={(event) =>
                  setFormState((prev) => ({ ...prev, model_endpoint_name: event.target.value }))
                }
                placeholder="例如：deepseek-r1-70b"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="model-base-url">Base URL</Label>
              <Input
                id="model-base-url"
                value={formState.base_url}
                onChange={(event) => setFormState((prev) => ({ ...prev, base_url: event.target.value }))}
                placeholder="https://api.example.com/v1"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="model-api-key">{editingModel ? 'API Key（留空不变）' : 'API Key'}</Label>
              <Input
                id="model-api-key"
                type="password"
                value={formState.api_key}
                onChange={(event) => setFormState((prev) => ({ ...prev, api_key: event.target.value }))}
                placeholder={editingModel ? '不修改则留空' : 'sk-xxxxxx'}
                required={!editingModel}
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleDialogClose}
                disabled={isSubmitting}
              >
                取消
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {editingModel ? '保存修改' : '创建模型'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.title}
        message={confirmDialog.message}
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  )
}


