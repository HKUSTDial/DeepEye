import { useEffect, useMemo, useState } from 'react'
import {
  databaseConnectionsAPI,
  type DatabaseConnection,
  type DatabaseConnectionUpdate,
} from '@/shared/api'
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
  Database,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Trash2,
} from 'lucide-react'

type ConnectionFormState = {
  name: string
  type: string
  host: string
  port: string
  username: string
  password: string
  database: string
}

const defaultFormState: ConnectionFormState = {
  name: '',
  type: 'postgres',
  host: '',
  port: '5432',
  username: '',
  password: '',
  database: '',
}

const databaseTypeOptions = [
  { value: 'postgres', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'mssql', label: 'SQL Server' },
  { value: 'oracle', label: 'Oracle' },
  { value: 'sqlite', label: 'SQLite' },
  { value: 'duckdb', label: 'DuckDB' },
  { value: 'other', label: '其他' },
]

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

const sortByUpdatedAt = (items: DatabaseConnection[]) =>
  [...items].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )

export function DatabaseConnectionsPage() {
  const [connections, setConnections] = useState<DatabaseConnection[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingConnection, setEditingConnection] = useState<DatabaseConnection | null>(null)
  const [formState, setFormState] = useState<ConnectionFormState>(defaultFormState)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  })

  useEffect(() => {
    void loadConnections()
  }, [])

  const loadConnections = async () => {
    setIsLoading(true)
    try {
      const data = await databaseConnectionsAPI.list()
      setConnections(sortByUpdatedAt(data))
    } catch (error) {
      console.error('加载数据库连接失败:', error)
      toast.error('加载数据库连接失败')
    } finally {
      setIsLoading(false)
    }
  }

  const filteredConnections = useMemo(() => {
    if (!searchQuery) return connections
    const keyword = searchQuery.toLowerCase()
    return connections.filter((connection) =>
      [connection.name, connection.type, connection.host, connection.database]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(keyword))
    )
  }, [connections, searchQuery])

  const stats = useMemo(() => {
    if (!connections.length) {
      return {
        total: 0,
        types: 0,
        latest: '--',
      }
    }
    const uniqueTypes = new Set(connections.map((item) => item.type.toLowerCase()))
    return {
      total: connections.length,
      types: uniqueTypes.size,
      latest: formatRelativeTime(connections[0]?.updated_at),
    }
  }, [connections])

  const handleDialogClose = () => {
    setIsDialogOpen(false)
    setEditingConnection(null)
    setFormState(defaultFormState)
  }

  const openCreateDialog = () => {
    setEditingConnection(null)
    setFormState(defaultFormState)
    setIsDialogOpen(true)
  }

  const openEditDialog = (connection: DatabaseConnection) => {
    setEditingConnection(connection)
    setFormState({
      name: connection.name,
      type: connection.type,
      host: connection.host,
      port: String(connection.port),
      username: connection.username,
      password: '',
      database: connection.database,
    })
    setIsDialogOpen(true)
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isSubmitting) return
    const portValue = Number(formState.port)
    if (Number.isNaN(portValue) || portValue <= 0) {
      toast.error('请输入有效的端口号')
      return
    }

    setIsSubmitting(true)
    try {
      if (editingConnection) {
        const payload: DatabaseConnectionUpdate = {
          name: formState.name.trim(),
          type: formState.type,
          host: formState.host.trim(),
          port: portValue,
          username: formState.username.trim(),
          database: formState.database.trim(),
        } as Omit<DatabaseConnection, 'id' | 'user_id' | 'created_at' | 'updated_at'> & {
          password?: string
        }

        if (formState.password.trim()) {
          payload.password = formState.password
        }

        const updated = await databaseConnectionsAPI.update(editingConnection.id, payload)
        setConnections((prev) =>
          sortByUpdatedAt(prev.map((item) => (item.id === updated.id ? updated : item)))
        )
        toast.success('数据库连接已更新')
      } else {
        const created = await databaseConnectionsAPI.create({
          name: formState.name.trim(),
          type: formState.type,
          host: formState.host.trim(),
          port: portValue,
          username: formState.username.trim(),
          password: formState.password,
          database: formState.database.trim(),
        })
        setConnections((prev) => sortByUpdatedAt([created, ...prev]))
        toast.success('数据库连接已创建')
      }
      handleDialogClose()
    } catch (error) {
      console.error('保存数据库连接失败:', error)
      toast.error('保存数据库连接失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (connectionId: string) => {
    try {
      await databaseConnectionsAPI.delete(connectionId)
      setConnections((prev) => prev.filter((item) => item.id !== connectionId))
      toast.success('数据库连接已删除')
    } catch (error) {
      console.error('删除数据库连接失败:', error)
      toast.error('删除数据库连接失败')
    } finally {
      setConfirmDialog((prev) => ({ ...prev, isOpen: false }))
    }
  }

  const openDeleteDialog = (connection: DatabaseConnection) => {
    setConfirmDialog({
      isOpen: true,
      title: '删除数据库连接',
      message: `确定要删除 "${connection.name}" 吗？此操作无法撤销。`,
      onConfirm: () => {
        void handleDelete(connection.id)
      },
    })
  }

  return (
    <div className="flex h-full flex-col bg-background">
      <header className="border-b bg-card px-6 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">数据源中心</p>
            <h1 className="mt-1 text-2xl font-bold text-foreground">数据库管理</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              统一维护各类数据库连接，确保数据探索、建模与执行流程顺畅
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">连接数量</CardTitle>
              <Server className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
              <p className="text-xs text-muted-foreground">当前账号下的数据库连接</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">类型覆盖</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.types}</div>
              <p className="text-xs text-muted-foreground">不同数据库类型</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最近更新</CardTitle>
              <ShieldCheck className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.latest}</div>
              <p className="text-xs text-muted-foreground">保持凭据新鲜安全</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <CardTitle>连接列表</CardTitle>
                <CardDescription>维护主机、端口、凭据等关键信息</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void loadConnections()}
                  disabled={isLoading}
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                  刷新
                </Button>
                <Button size="sm" onClick={openCreateDialog}>
                  <Plus className="h-4 w-4" />
                  新建连接
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索名称、类型、主机或数据库..."
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
            ) : filteredConnections.length === 0 ? (
              <EmptyState
                icon={Database}
                title={searchQuery ? '没有找到匹配的连接' : '当前暂无数据库连接'}
                description={
                  searchQuery
                    ? '试试其他关键字，或清空搜索条件'
                    : '点击“新建连接”即可快速配置'
                }
                className="py-12"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
                      <th className="py-3 pr-4 font-medium">名称 / 类型</th>
                      <th className="py-3 pr-4 font-medium">主机</th>
                      <th className="py-3 pr-4 font-medium">数据库</th>
                      <th className="py-3 pr-4 font-medium">用户名</th>
                      <th className="py-3 pr-4 font-medium">更新时间</th>
                      <th className="py-3 text-right font-medium">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredConnections.map((connection) => (
                      <tr key={connection.id} className="border-b border-border/60 last:border-b-0">
                        <td className="py-3 pr-4">
                          <div className="font-medium text-foreground">{connection.name}</div>
                          <div className="mt-1 text-xs font-medium uppercase text-muted-foreground">
                            {connection.type}
                          </div>
                        </td>
                        <td className="py-3 pr-4">
                          <div className="text-foreground">{connection.host}</div>
                          <div className="text-xs text-muted-foreground">端口 {connection.port}</div>
                        </td>
                        <td className="py-3 pr-4">
                          <div className="text-foreground">{connection.database}</div>
                        </td>
                        <td className="py-3 pr-4">{connection.username}</td>
                        <td className="py-3 pr-4">
                          <div className="text-foreground">{formatDateTime(connection.updated_at)}</div>
                          <div className="text-xs text-muted-foreground">
                            {formatRelativeTime(connection.updated_at)}
                          </div>
                        </td>
                        <td className="py-3 text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="编辑连接"
                              onClick={() => openEditDialog(connection)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="删除连接"
                              className="text-destructive"
                              onClick={() => openDeleteDialog(connection)}
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
            <DialogTitle>{editingConnection ? '编辑连接' : '新建数据库连接'}</DialogTitle>
            <DialogDescription>
              {editingConnection
                ? '更新数据库连接信息，密码留空则保持不变'
                : '填写数据库访问信息，所有字段均会进行加密存储'}
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="connection-name">连接名称</Label>
                <Input
                  id="connection-name"
                  value={formState.name}
                  onChange={(event) => setFormState((prev) => ({ ...prev, name: event.target.value }))}
                  placeholder="例如：生产 PostgreSQL"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="connection-type">数据库类型</Label>
                <select
                  id="connection-type"
                  value={formState.type}
                  onChange={(event) => setFormState((prev) => ({ ...prev, type: event.target.value }))}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {databaseTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="connection-host">主机地址</Label>
                <Input
                  id="connection-host"
                  value={formState.host}
                  onChange={(event) => setFormState((prev) => ({ ...prev, host: event.target.value }))}
                  placeholder="db.example.com"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="connection-port">端口</Label>
                <Input
                  id="connection-port"
                  type="number"
                  min={1}
                  value={formState.port}
                  onChange={(event) => setFormState((prev) => ({ ...prev, port: event.target.value }))}
                  required
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="connection-username">用户名</Label>
                <Input
                  id="connection-username"
                  value={formState.username}
                  onChange={(event) => setFormState((prev) => ({ ...prev, username: event.target.value }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="connection-password">
                  {editingConnection ? '密码（留空则不修改）' : '密码'}
                </Label>
                <Input
                  id="connection-password"
                  type="password"
                  value={formState.password}
                  onChange={(event) => setFormState((prev) => ({ ...prev, password: event.target.value }))}
                  placeholder={editingConnection ? '不修改则留空' : ''}
                  required={!editingConnection}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="connection-database">数据库名称</Label>
              <Input
                id="connection-database"
                value={formState.database}
                onChange={(event) => setFormState((prev) => ({ ...prev, database: event.target.value }))}
                required
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
                {editingConnection ? '保存修改' : '创建连接'}
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


