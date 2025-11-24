import { useEffect, useMemo, useRef, useState } from 'react'
import { filesAPI, type StoredFile } from '@/shared/api'
import { ThemeToggle, ConfirmDialog, EmptyState } from '@/shared/components'
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
} from '@/shared/components/ui'
import { toast } from '@/store'
import { downloadFileFromUrl } from '@/shared/utils'
import {
  Download,
  FileText,
  HardDrive,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  UploadCloud,
} from 'lucide-react'

const formatFileSize = (size: number): string => {
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
  const value = size / Math.pow(1024, index)
  const fixed = value >= 10 || index === 0 ? 0 : 1
  return `${value.toFixed(fixed)} ${units[index]}`
}

const formatDateTime = (value?: string) => {
  if (!value) return '--'
  return new Date(value).toLocaleString()
}

const formatRelativeTime = (value?: string) => {
  if (!value) return '--'
  const diff = Date.now() - new Date(value).getTime()
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`
  return `${Math.floor(diff / 86400000)} 天前`
}

const sortByCreatedAt = (items: StoredFile[]) =>
  [...items].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

export function FileStoragePage() {
  const [files, setFiles] = useState<StoredFile[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  })
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    void loadFiles()
  }, [])

  const loadFiles = async () => {
    setIsLoading(true)
    try {
      const data = await filesAPI.list()
      setFiles(sortByCreatedAt(data))
    } catch (error) {
      console.error('加载文件失败:', error)
      toast.error('加载文件失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  const filteredFiles = useMemo(() => {
    if (!searchQuery) return files
    const keyword = searchQuery.toLowerCase()
    return files.filter((file) =>
      [file.filename, file.original_name, file.content_type]
        .filter((field): field is string => Boolean(field))
        .some((field) => field.toLowerCase().includes(keyword))
    )
  }, [files, searchQuery])

  const stats = useMemo(() => {
    if (!files.length) {
      return {
        total: 0,
        totalSize: '0 B',
        latest: '--',
      }
    }
    const totalSize = files.reduce((sum, file) => sum + file.size, 0)
    const latest = files[0]
    return {
      total: files.length,
      totalSize: formatFileSize(totalSize),
      latest: formatRelativeTime(latest.created_at),
    }
  }, [files])

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      void uploadFile(file)
    }
    event.target.value = ''
  }

  const uploadFile = async (file: File) => {
    setIsUploading(true)
    try {
      const uploaded = await filesAPI.upload(file)
      setFiles((prev) =>
        sortByCreatedAt([uploaded, ...prev.filter((item) => item.id !== uploaded.id)])
      )
      toast.success(`已上传 ${file.name}`)
    } catch (error) {
      console.error('上传文件失败:', error)
      toast.error('上传失败，请稍后重试')
    } finally {
      setIsUploading(false)
    }
  }

  const openDeleteDialog = (file: StoredFile) => {
    setConfirmDialog({
      isOpen: true,
      title: '删除文件',
      message: `确定要删除 "${file.original_name || file.filename}" 吗？此操作无法撤销。`,
      onConfirm: () => {
        void handleDelete(file.id)
      },
    })
  }

  const handleDelete = async (fileId: string) => {
    try {
      await filesAPI.delete(fileId)
      setFiles((prev) => prev.filter((file) => file.id !== fileId))
      toast.success('文件已删除')
    } catch (error) {
      console.error('删除文件失败:', error)
      toast.error('删除文件失败，请稍后重试')
    } finally {
      setConfirmDialog((prev) => ({ ...prev, isOpen: false }))
    }
  }

  const handleDownload = async (file: StoredFile) => {
    try {
      const { url } = await filesAPI.getDownloadUrl(file.id)
      if (!url) {
        toast.error('无法获取下载链接')
        return
      }
      await downloadFileFromUrl(url, file.original_name || file.filename || 'download')
    } catch (error) {
      console.error('获取下载链接失败:', error)
      toast.error('下载失败，请稍后重试')
    }
  }

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragOver(false)
    const file = event.dataTransfer.files?.[0]
    if (file) {
      void uploadFile(file)
    }
  }

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragOver(false)
  }

  return (
    <div className="flex h-full flex-col bg-background">
      <header className="border-b bg-card px-6 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">文件空间</p>
            <h1 className="mt-1 text-2xl font-bold text-foreground">文件管理中心</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              上传模型、脚本、素材等资源，并随时下载或清理，保障数据安全
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">文件数量</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
              <p className="text-xs text-muted-foreground">当前账号下的所有文件</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">已用存储</CardTitle>
              <HardDrive className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalSize}</div>
              <p className="text-xs text-muted-foreground">自动计算所有文件大小</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最近上传</CardTitle>
              <ShieldCheck className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.latest}</div>
              <p className="text-xs text-muted-foreground">保持空间健康与最新</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-[320px,1fr]">
          <Card>
            <CardHeader>
              <CardTitle>快速上传</CardTitle>
              <CardDescription>支持拖拽上传，自动附带当前账号信息</CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`rounded-lg border-2 border-dashed p-6 text-center transition-all ${
                  isDragOver
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <UploadCloud className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
                <p className="text-lg font-medium text-foreground">拖拽文件到此区域</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  支持常见文本、压缩包、模型权重等格式（单个文件最大 200MB）
                </p>
                <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleFileInputChange}
                  />
                  <Button
                    type="button"
                    disabled={isUploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    选择文件
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void loadFiles()}
                    disabled={isLoading}
                  >
                    <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                    刷新列表
                  </Button>
                </div>
                {isUploading && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    正在上传，请稍候...
                  </p>
                )}
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                提示：上传后文件立即可用于工作流或团队协作；如需批量上传可多次选择。
              </p>
            </CardContent>
          </Card>

          <Card className="col-span-1">
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <CardTitle>我的文件</CardTitle>
                  <CardDescription>覆盖全部已上传的文件资源</CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadFiles()}
                  disabled={isLoading}
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                  刷新
                </Button>
              </div>
              <div className="mt-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="搜索文件名、类型..."
                    className="pl-9"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : filteredFiles.length === 0 ? (
                <EmptyState
                  icon={HardDrive}
                  title={searchQuery ? '没有匹配的文件' : '当前暂无文件'}
                  description={
                    searchQuery
                      ? '试试其他关键字，或清空搜索条件'
                      : '上传你的第一个文件，构建个人资料库'
                  }
                  className="py-12"
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                        <th className="py-3 pr-4 font-medium">文件名</th>
                        <th className="py-3 pr-4 font-medium">类型</th>
                        <th className="py-3 pr-4 font-medium">大小</th>
                        <th className="py-3 pr-4 font-medium">上传时间</th>
                        <th className="py-3 text-right font-medium">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredFiles.map((file) => (
                        <tr key={file.id} className="border-b border-border/60 last:border-b-0">
                          <td className="py-3 pr-4">
                            <div className="font-medium text-foreground">
                              {file.original_name || file.filename}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                              {file.filename}
                            </div>
                          </td>
                          <td className="py-3 pr-4">{file.content_type || '--'}</td>
                          <td className="py-3 pr-4">{formatFileSize(file.size)}</td>
                          <td className="py-3 pr-4">
                            <div className="text-foreground">{formatDateTime(file.created_at)}</div>
                            <div className="text-xs text-muted-foreground">
                              {formatRelativeTime(file.created_at)}
                            </div>
                          </td>
                          <td className="py-3 text-right">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label="下载文件"
                                onClick={() => void handleDownload(file)}
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label="删除文件"
                                className="text-destructive"
                                onClick={() => openDeleteDialog(file)}
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
        </div>
      </main>

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.title}
        message={confirmDialog.message}
        onConfirm={confirmDialog.onConfirm}
        onCancel={() => setConfirmDialog((prev) => ({ ...prev, isOpen: false }))}
        confirmText="删除"
        variant="danger"
      />
    </div>
  )
}


