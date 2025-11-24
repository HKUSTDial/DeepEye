import { useEffect, useMemo, useState } from 'react'
import type { ComponentType, ReactNode } from 'react'
import {
  databaseConnectionsAPI,
  knowledgeAPI,
  type BusinessMetric,
  type BusinessMetricCreatePayload,
  type BusinessRule,
  type BusinessRuleCreatePayload,
  type DatabaseConnection,
  type ExampleQuery,
  type ExampleQueryPayload,
  type MetricDefinitionType,
  type TableDescription,
} from '@/shared/api'
import { ConfirmDialog, EmptyState } from '@/shared/components'
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Textarea,
} from '@/shared/components/ui'
import { toast } from '@/store'
import {
  BookMarked,
  Brain,
  CheckCircle2,
  Columns3,
  Database,
  Layers,
  Loader2,
  Pencil,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Table2,
  Trash2,
} from 'lucide-react'

const metricTypes: MetricDefinitionType[] = ['SQL_FRAGMENT', 'NATURAL_LANGUAGE', 'DERIVED']

interface ConfirmDialogState {
  isOpen: boolean
  title: string
  message: string
  onConfirm: () => void
}

export function DatabaseKnowledgePanel() {
  const [connections, setConnections] = useState<DatabaseConnection[]>([])
  const [connectionsLoading, setConnectionsLoading] = useState(true)
  const [selectedConnectionId, setSelectedConnectionId] = useState<string>('')

  const [tables, setTables] = useState<TableDescription[]>([])
  const [tableSearch, setTableSearch] = useState('')
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null)
  const [isKnowledgeLoading, setIsKnowledgeLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)

  const [tableDescriptionDraft, setTableDescriptionDraft] = useState('')
  const [columnDrafts, setColumnDrafts] = useState<Record<string, string>>({})
  const [savingTable, setSavingTable] = useState(false)
  const [savingColumnId, setSavingColumnId] = useState<string | null>(null)

  const [rules, setRules] = useState<BusinessRule[]>([])
  const [ruleForm, setRuleForm] = useState<BusinessRuleCreatePayload>({
    rule_name: '',
    description: '',
    rule_sql_snippet: '',
  })
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null)
  const [ruleSubmitting, setRuleSubmitting] = useState(false)

  const [metrics, setMetrics] = useState<BusinessMetric[]>([])
  const [metricForm, setMetricForm] = useState({
    name: '',
    aliasText: '',
    description: '',
    definition_type: 'SQL_FRAGMENT' as MetricDefinitionType,
    definition_sql: '',
  })
  const [editingMetricId, setEditingMetricId] = useState<string | null>(null)
  const [metricSubmitting, setMetricSubmitting] = useState(false)

  const [examples, setExamples] = useState<ExampleQuery[]>([])
  const [exampleForm, setExampleForm] = useState<ExampleQueryPayload>({
    question: '',
    sql_logic: '',
  })
  const [exampleSubmitting, setExampleSubmitting] = useState(false)

  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  })

  useEffect(() => {
    void loadConnections()
  }, [])

  useEffect(() => {
    if (!selectedConnectionId) {
      setTables([])
      setRules([])
      setMetrics([])
      setExamples([])
      setSelectedTableId(null)
      return
    }
    void loadKnowledge(selectedConnectionId)
  }, [selectedConnectionId])

  const selectedConnection = useMemo(
    () => connections.find((item) => item.id === selectedConnectionId) || null,
    [connections, selectedConnectionId]
  )

  const filteredTables = useMemo(() => {
    if (!tableSearch) return tables
    const keyword = tableSearch.toLowerCase()
    return tables.filter((table) => table.table_name.toLowerCase().includes(keyword))
  }, [tables, tableSearch])

  const selectedTable = useMemo(
    () => tables.find((table) => table.id === selectedTableId) || null,
    [tables, selectedTableId]
  )

  const knowledgeStats = useMemo(() => {
    const totalColumns = tables.reduce((sum, table) => sum + table.columns.length, 0)
    return {
      tableCount: tables.length,
      columnCount: totalColumns,
      ruleCount: rules.length,
      metricCount: metrics.length,
      exampleCount: examples.length,
    }
  }, [tables, rules.length, metrics.length, examples.length])

  useEffect(() => {
    if (selectedTable) {
      setTableDescriptionDraft(selectedTable.description ?? '')
      const drafts: Record<string, string> = {}
      selectedTable.columns.forEach((column) => {
        drafts[column.id] = column.description ?? ''
      })
      setColumnDrafts(drafts)
    } else {
      setTableDescriptionDraft('')
      setColumnDrafts({})
    }
  }, [selectedTable])

  const loadConnections = async () => {
    setConnectionsLoading(true)
    try {
      const data = await databaseConnectionsAPI.list()
      setConnections(data)
      if (!selectedConnectionId && data.length) {
        setSelectedConnectionId(data[0].id)
      }
    } catch (error) {
      console.error('加载数据库连接失败:', error)
      toast.error('加载数据库连接失败')
    } finally {
      setConnectionsLoading(false)
    }
  }

  const loadKnowledge = async (connectionId: string) => {
    setIsKnowledgeLoading(true)
    try {
      const [tableData, ruleData, metricData, exampleData] = await Promise.all([
        knowledgeAPI.getTablesByConnection(connectionId),
        knowledgeAPI.getBusinessRules(connectionId),
        knowledgeAPI.getBusinessMetrics(connectionId),
        knowledgeAPI.getExampleQueries(connectionId),
      ])
      setTables(tableData)
      setRules(ruleData)
      setMetrics(metricData)
      setExamples(exampleData)

      if (!tableData.length) {
        setSelectedTableId(null)
      } else if (!tableData.some((table) => table.id === selectedTableId)) {
        setSelectedTableId(tableData[0].id)
      }
    } catch (error) {
      console.error('加载知识失败:', error)
      toast.error('加载知识内容失败，请稍后再试')
    } finally {
      setIsKnowledgeLoading(false)
    }
  }

  const handleSyncSchema = async () => {
    if (!selectedConnectionId) {
      toast.info('请先选择一个数据库连接')
      return
    }
    setIsSyncing(true)
    try {
      await knowledgeAPI.syncDatabaseSchema(selectedConnectionId)
      toast.success('已同步数据库结构')
      await loadKnowledge(selectedConnectionId)
    } catch (error) {
      console.error('同步数据库结构失败:', error)
      toast.error('同步失败，请检查数据库连接配置')
    } finally {
      setIsSyncing(false)
    }
  }

  const handleSaveTableDescription = async () => {
    if (!selectedTableId) return
    setSavingTable(true)
    try {
      const updated = await knowledgeAPI.updateTableDescription(selectedTableId, {
        description: tableDescriptionDraft || null,
      })
      setTables((prev) =>
        prev.map((table) => (table.id === updated.id ? { ...table, description: updated.description } : table))
      )
      toast.success('表描述已更新')
    } catch (error) {
      console.error('更新表描述失败:', error)
      toast.error('更新失败，请稍后再试')
    } finally {
      setSavingTable(false)
    }
  }

  const handleSaveColumnDescription = async (columnId: string) => {
    const value = columnDrafts[columnId] ?? ''
    setSavingColumnId(columnId)
    try {
      const updated = await knowledgeAPI.updateColumnDescription(columnId, {
        description: value || null,
      })
      setTables((prev) =>
        prev.map((table) =>
          table.id === updated.table_description_id
            ? {
                ...table,
                columns: table.columns.map((column) =>
                  column.id === updated.id ? { ...column, description: updated.description } : column
                ),
              }
            : table
        )
      )
      toast.success('字段描述已更新')
    } catch (error) {
      console.error('更新字段描述失败:', error)
      toast.error('更新失败，请稍后再试')
    } finally {
      setSavingColumnId(null)
    }
  }

  const resetRuleForm = () => {
    setRuleForm({
      rule_name: '',
      description: '',
      rule_sql_snippet: '',
    })
    setEditingRuleId(null)
  }

  const handleSubmitRule = async () => {
    if (!selectedConnectionId) {
      toast.info('请选择数据库连接')
      return
    }
    if (!ruleForm.rule_name.trim() || !ruleForm.description.trim()) {
      toast.warning('请填写规则名称和描述')
      return
    }

    setRuleSubmitting(true)
    try {
      if (editingRuleId) {
        const updated = await knowledgeAPI.updateBusinessRule(editingRuleId, {
          ...ruleForm,
          rule_name: ruleForm.rule_name.trim(),
          description: ruleForm.description.trim(),
          rule_sql_snippet: ruleForm.rule_sql_snippet?.trim() || null,
        })
        setRules((prev) => prev.map((rule) => (rule.id === updated.id ? updated : rule)))
        toast.success('规则已更新')
      } else {
        const created = await knowledgeAPI.createBusinessRule(selectedConnectionId, {
          rule_name: ruleForm.rule_name.trim(),
          description: ruleForm.description.trim(),
          rule_sql_snippet: ruleForm.rule_sql_snippet?.trim() || null,
        })
        setRules((prev) => [created, ...prev])
        toast.success('规则已创建')
      }
      resetRuleForm()
    } catch (error) {
      console.error('提交规则失败:', error)
      toast.error('保存规则失败，请稍后再试')
    } finally {
      setRuleSubmitting(false)
    }
  }

  const handleRuleDelete = (rule: BusinessRule) => {
    setConfirmDialog({
      isOpen: true,
      title: '删除业务规则',
      message: `确定删除规则「${rule.rule_name}」吗？此操作不可撤销。`,
      onConfirm: async () => {
        try {
          await knowledgeAPI.deleteBusinessRule(rule.id)
          setRules((prev) => prev.filter((item) => item.id !== rule.id))
          toast.success('规则已删除')
        } catch (error) {
          console.error('删除规则失败:', error)
          toast.error('删除失败，请稍后再试')
        } finally {
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }))
        }
      },
    })
  }

  const resetMetricForm = () => {
    setMetricForm({
      name: '',
      aliasText: '',
      description: '',
      definition_type: 'SQL_FRAGMENT',
      definition_sql: '',
    })
    setEditingMetricId(null)
  }

  const handleSubmitMetric = async () => {
    if (!selectedConnectionId) {
      toast.info('请选择数据库连接')
      return
    }
    if (!metricForm.name.trim() || !metricForm.description.trim()) {
      toast.warning('请填写指标名称与描述')
      return
    }

    const aliasList = metricForm.aliasText
      ? metricForm.aliasText.split(',').map((item) => item.trim()).filter(Boolean)
      : undefined

    const payload: BusinessMetricCreatePayload = {
      name: metricForm.name.trim(),
      description: metricForm.description.trim(),
      alias: aliasList,
      definition_type: metricForm.definition_type,
      definition_sql: metricForm.definition_sql?.trim() || null,
    }

    setMetricSubmitting(true)
    try {
      if (editingMetricId) {
        const updated = await knowledgeAPI.updateBusinessMetric(editingMetricId, payload)
        setMetrics((prev) => prev.map((metric) => (metric.id === updated.id ? updated : metric)))
        toast.success('指标已更新')
      } else {
        const created = await knowledgeAPI.createBusinessMetric(selectedConnectionId, payload)
        setMetrics((prev) => [created, ...prev])
        toast.success('指标已创建')
      }
      resetMetricForm()
    } catch (error) {
      console.error('提交指标失败:', error)
      toast.error('保存指标失败，请稍后再试')
    } finally {
      setMetricSubmitting(false)
    }
  }

  const handleMetricDelete = (metric: BusinessMetric) => {
    setConfirmDialog({
      isOpen: true,
      title: '删除业务指标',
      message: `确定删除指标「${metric.name}」吗？`,
      onConfirm: async () => {
        try {
          await knowledgeAPI.deleteBusinessMetric(metric.id)
          setMetrics((prev) => prev.filter((item) => item.id !== metric.id))
          toast.success('指标已删除')
        } catch (error) {
          console.error('删除指标失败:', error)
          toast.error('删除指标失败，请稍后再试')
        } finally {
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }))
        }
      },
    })
  }

  const resetExampleForm = () => {
    setExampleForm({
      question: '',
      sql_logic: '',
    })
  }

  const handleSubmitExample = async () => {
    if (!selectedConnectionId) {
      toast.info('请选择数据库连接')
      return
    }
    if (!exampleForm.question.trim() || !exampleForm.sql_logic.trim()) {
      toast.warning('请完善示例问法与 SQL 逻辑')
      return
    }

    setExampleSubmitting(true)
    try {
      const created = await knowledgeAPI.createExampleQuery(selectedConnectionId, {
        question: exampleForm.question.trim(),
        sql_logic: exampleForm.sql_logic.trim(),
      })
      setExamples((prev) => [created, ...prev])
      toast.success('样例已创建')
      resetExampleForm()
    } catch (error) {
      console.error('创建样例失败:', error)
      toast.error('创建失败，请稍后再试')
    } finally {
      setExampleSubmitting(false)
    }
  }

  const handleExampleDelete = (example: ExampleQuery) => {
    setConfirmDialog({
      isOpen: true,
      title: '删除样例',
      message: `确定删除示例问法「${example.question}」吗？`,
      onConfirm: async () => {
        try {
          await knowledgeAPI.deleteExampleQuery(example.id)
          setExamples((prev) => prev.filter((item) => item.id !== example.id))
          toast.success('样例已删除')
        } catch (error) {
          console.error('删除样例失败:', error)
          toast.error('删除样例失败，请稍后再试')
        } finally {
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }))
        }
      },
    })
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>数据库知识全景</CardTitle>
          <CardDescription>
            连接真实数据库后，快速同步表结构，并维护指标、规则、样例等业务资产。
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[360px,1fr]">
          <div className="space-y-4">
            <div>
              <Label htmlFor="connection-select">数据库连接</Label>
              <div className="mt-2 flex items-center gap-3">
                <select
                  id="connection-select"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
                  value={selectedConnectionId}
                  onChange={(event) => setSelectedConnectionId(event.target.value)}
                  disabled={connectionsLoading}
                >
                  {connections.length === 0 && <option value="">暂无连接</option>}
                  {connections.map((connection) => (
                    <option key={connection.id} value={connection.id}>
                      {connection.name} · {connection.type}
                    </option>
                  ))}
                </select>
                <Button variant="outline" size="sm" onClick={() => void loadConnections()}>
                  <RefreshCw className={`h-4 w-4 ${connectionsLoading ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </div>
            <Button
              type="button"
              variant="default"
              onClick={() => void handleSyncSchema()}
              disabled={!selectedConnectionId || isSyncing}
              className="w-full"
            >
              {isSyncing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  正在同步数据库结构...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  同步数据库结构
                </>
              )}
            </Button>
            {selectedConnection && (
              <div className="rounded-lg border bg-muted/40 p-4 text-sm">
                <div className="font-medium">{selectedConnection.name}</div>
                <div className="mt-1 text-muted-foreground">
                  {selectedConnection.type.toUpperCase()} · {selectedConnection.host}:{selectedConnection.port}
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  用户名：{selectedConnection.username} · 数据库：{selectedConnection.database}
                </div>
              </div>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatisticCard
              icon={Table2}
              label="同步表"
              value={`${knowledgeStats.tableCount} 张`}
              helper="所有可见 schema 下的表"
            />
            <StatisticCard
              icon={Columns3}
              label="字段描述"
              value={`${knowledgeStats.columnCount} 个`}
              helper="字段含义、口径、枚举"
            />
            <StatisticCard
              icon={BookMarked}
              label="业务规则"
              value={`${knowledgeStats.ruleCount} 条`}
              helper="沉淀可复用 SQL 片段"
            />
            <StatisticCard
              icon={Brain}
              label="指标字典"
              value={`${knowledgeStats.metricCount} 个`}
              helper="统一业务口径"
            />
            <StatisticCard
              icon={CheckCircle2}
              label="样例问答"
              value={`${knowledgeStats.exampleCount} 条`}
              helper="Few-shot Prompt"
            />
            <StatisticCard
              icon={Layers}
              label="知识覆盖"
              value="闭环"
              helper="结构化 + 规则 + 样例"
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[360px,1fr]">
        <Card className="h-full">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>表列表</CardTitle>
                <CardDescription>选择需要维护的表，查看字段并编辑描述</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => void loadKnowledge(selectedConnectionId)} disabled={isKnowledgeLoading}>
                <RefreshCw className={`h-4 w-4 ${isKnowledgeLoading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
            </div>
            <div className="mt-4">
              <div className="relative">
                <Input
                  placeholder="搜索表名..."
                  value={tableSearch}
                  onChange={(event) => setTableSearch(event.target.value)}
                />
              </div>
            </div>
          </CardHeader>
          <CardContent className="max-h-[540px] overflow-y-auto">
            {isKnowledgeLoading ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              </div>
            ) : filteredTables.length === 0 ? (
              <EmptyState
                icon={Database}
                title={selectedConnectionId ? '没有同步到表' : '请先选择连接'}
                description={
                  selectedConnectionId
                    ? '尝试同步数据库结构，或更换 schema'
                    : '选择一个数据库连接即可查看表结构'
                }
                className="py-8"
              />
            ) : (
              <div className="space-y-2">
                {filteredTables.map((table) => {
                  const isActive = selectedTableId === table.id
                  return (
                    <button
                      key={table.id}
                      type="button"
                      onClick={() => setSelectedTableId(table.id)}
                      className={`w-full rounded-lg border px-4 py-3 text-left text-sm transition ${
                        isActive
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border hover:border-primary/40'
                      }`}
                    >
                      <div className="font-semibold">{table.table_name}</div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        Schema：{table.schema_name} · 字段 {table.columns.length}
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardHeader>
            <CardTitle>字段知识维护</CardTitle>
            <CardDescription>让每个字段都具备可读描述，便于 LLM 生成更准确的 SQL。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedTable ? (
              <EmptyState
                icon={Table2}
                title="请选择一张表"
                description="同步后选择左侧的表，即可开始维护表描述与字段信息。"
                className="py-12"
              />
            ) : (
              <>
                <div>
                  <Label htmlFor="table-description">表描述</Label>
                  <Textarea
                    id="table-description"
                    className="mt-2 min-h-[100px]"
                    placeholder="示例：订单主表，记录订单的生命周期状态、金额等关键信息"
                    value={tableDescriptionDraft}
                    onChange={(event) => setTableDescriptionDraft(event.target.value)}
                  />
                  <div className="mt-2 text-right">
                    <Button
                      size="sm"
                      onClick={() => void handleSaveTableDescription()}
                      disabled={savingTable}
                    >
                      {savingTable ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          保存中...
                        </>
                      ) : (
                        '保存表描述'
                      )}
                    </Button>
                  </div>
                </div>
                <div className="rounded-lg border bg-muted/40 p-4">
                  <div className="text-sm font-semibold">
                    字段列表（{selectedTable.columns.length}）
                  </div>
                  <div className="mt-3 space-y-3">
                    {selectedTable.columns.map((column) => (
                      <div
                        key={column.id}
                        className="rounded-md border border-border/60 bg-background p-3"
                      >
                        <div className="text-sm font-semibold">
                          <span>{column.column_name}</span>
                        </div>
                        <Textarea
                          className="mt-2 min-h-[70px] text-xs"
                          placeholder="简要描述字段含义、单位、枚举值等"
                          value={columnDrafts[column.id] ?? ''}
                          onChange={(event) =>
                            setColumnDrafts((prev) => ({
                              ...prev,
                              [column.id]: event.target.value,
                            }))
                          }
                        />
                        <div className="mt-2 text-right">
                          <Button
                            size="sm"
                            onClick={() => void handleSaveColumnDescription(column.id)}
                            disabled={savingColumnId === column.id}
                          >
                            {savingColumnId === column.id ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                保存中...
                              </>
                            ) : (
                              '保存'
                            )}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <KnowledgeAssetCard
          title="业务规则"
          description="沉淀可复用的校验逻辑与 SQL 片段"
          items={rules}
          renderItem={(rule) => (
            <div className="rounded-lg border border-border/60 bg-background p-3 text-sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{rule.rule_name}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{rule.description}</div>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      setEditingRuleId(rule.id)
                      setRuleForm({
                        rule_name: rule.rule_name,
                        description: rule.description,
                        rule_sql_snippet: rule.rule_sql_snippet || '',
                      })
                    }}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive"
                    onClick={() => handleRuleDelete(rule)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              {rule.rule_sql_snippet && (
                <pre className="mt-3 overflow-auto rounded-md bg-muted/40 p-2 text-xs text-muted-foreground">
                  {rule.rule_sql_snippet}
                </pre>
              )}
            </div>
          )}
          emptyHint="尚未配置业务规则"
          form={
            <div className="space-y-3">
              <Input
                placeholder="规则名称，如「订单金额校验」"
                value={ruleForm.rule_name}
                onChange={(event) =>
                  setRuleForm((prev) => ({ ...prev, rule_name: event.target.value }))
                }
              />
              <Textarea
                placeholder="规则描述，说明业务背景和作用"
                value={ruleForm.description}
                onChange={(event) =>
                  setRuleForm((prev) => ({ ...prev, description: event.target.value }))
                }
              />
              <Textarea
                placeholder="可选：粘贴对应的 SQL 片段或伪代码"
                className="font-mono text-xs"
                value={ruleForm.rule_sql_snippet ?? ''}
                onChange={(event) =>
                  setRuleForm((prev) => ({ ...prev, rule_sql_snippet: event.target.value }))
                }
              />
              <Button onClick={() => void handleSubmitRule()} disabled={ruleSubmitting}>
                {ruleSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {editingRuleId ? '更新规则' : '新增规则'}
              </Button>
              {editingRuleId && (
                <Button variant="ghost" size="sm" onClick={resetRuleForm}>
                  取消编辑
                </Button>
              )}
            </div>
          }
        />

        <KnowledgeAssetCard
          title="指标字典"
          description="统一口径的核心业务指标"
          items={metrics}
          renderItem={(metric) => (
            <div className="rounded-lg border border-border/60 bg-background p-3 text-sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{metric.name}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{metric.description}</div>
                  {metric.alias && metric.alias.length > 0 && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      别名：{metric.alias.join(' / ')}
                    </div>
                  )}
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      setEditingMetricId(metric.id)
                      setMetricForm({
                        name: metric.name,
                        aliasText: metric.alias?.join(',') ?? '',
                        description: metric.description,
                        definition_type: metric.definition_type,
                        definition_sql: metric.definition_sql ?? '',
                      })
                    }}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive"
                    onClick={() => handleMetricDelete(metric)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="mt-2 rounded-md bg-muted/40 p-2 text-xs text-muted-foreground">
                类型：{metric.definition_type}
                {metric.definition_sql && (
                  <pre className="mt-2 overflow-auto rounded bg-background/80 p-2 text-[11px]">
                    {metric.definition_sql}
                  </pre>
                )}
              </div>
            </div>
          )}
          emptyHint="暂无指标"
          form={
            <div className="space-y-3">
              <Input
                placeholder="指标名称，如「GMV」"
                value={metricForm.name}
                onChange={(event) =>
                  setMetricForm((prev) => ({ ...prev, name: event.target.value }))
                }
              />
              <Input
                placeholder="别名（可选），使用逗号分隔"
                value={metricForm.aliasText}
                onChange={(event) =>
                  setMetricForm((prev) => ({ ...prev, aliasText: event.target.value }))
                }
              />
              <Textarea
                placeholder="指标描述，解释业务含义与口径"
                value={metricForm.description}
                onChange={(event) =>
                  setMetricForm((prev) => ({ ...prev, description: event.target.value }))
                }
              />
              <div>
                <Label htmlFor="definition-type">定义方式</Label>
                <select
                  id="definition-type"
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
                  value={metricForm.definition_type}
                  onChange={(event) =>
                    setMetricForm((prev) => ({
                      ...prev,
                      definition_type: event.target.value as MetricDefinitionType,
                    }))
                  }
                >
                  {metricTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
              <Textarea
                placeholder="可选：SQL 定义或伪代码"
                className="font-mono text-xs"
                value={metricForm.definition_sql}
                onChange={(event) =>
                  setMetricForm((prev) => ({ ...prev, definition_sql: event.target.value }))
                }
              />
              <Button onClick={() => void handleSubmitMetric()} disabled={metricSubmitting}>
                {metricSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {editingMetricId ? '更新指标' : '新增指标'}
              </Button>
              {editingMetricId && (
                <Button variant="ghost" size="sm" onClick={resetMetricForm}>
                  取消编辑
                </Button>
              )}
            </div>
          }
        />

        <KnowledgeAssetCard
          title="样例问答"
          description="Few-shot 示例，帮助模型理解业务语义"
          items={examples}
          renderItem={(example) => (
            <div className="rounded-lg border border-border/60 bg-background p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-semibold">Q: {example.question}</div>
                  <pre className="mt-2 overflow-auto rounded-md bg-muted/40 p-2 text-xs text-muted-foreground">
                    {example.sql_logic}
                  </pre>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive"
                  onClick={() => handleExampleDelete(example)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
          emptyHint="暂无样例"
          form={
            <div className="space-y-3">
              <Textarea
                placeholder="示例问题，如：统计近 7 日 GMV"
                value={exampleForm.question}
                onChange={(event) =>
                  setExampleForm((prev) => ({ ...prev, question: event.target.value }))
                }
              />
              <Textarea
                placeholder="对应的 SQL 思路或完整 SQL"
                className="font-mono text-xs"
                value={exampleForm.sql_logic}
                onChange={(event) =>
                  setExampleForm((prev) => ({ ...prev, sql_logic: event.target.value }))
                }
              />
              <Button onClick={() => void handleSubmitExample()} disabled={exampleSubmitting}>
                {exampleSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                新增样例
              </Button>
            </div>
          }
        />
      </div>

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

interface KnowledgeAssetCardProps<T extends { id: string }> {
  title: string
  description: string
  items: T[]
  renderItem: (item: T) => ReactNode
  emptyHint: string
  form: ReactNode
}

function KnowledgeAssetCard<T extends { id: string }>({
  title,
  description,
  items,
  renderItem,
  emptyHint,
  form,
}: KnowledgeAssetCardProps<T>) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        <div className="space-y-3">
          {items.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title={emptyHint}
              description="立即创建一条，提升数据库知识覆盖率。"
              className="py-6"
            />
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div key={item.id}>{renderItem(item)}</div>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-lg border bg-muted/30 p-4">
          <div className="text-sm font-semibold">新建/编辑</div>
          <div className="mt-3 space-y-3">{form}</div>
        </div>
      </CardContent>
    </Card>
  )
}

interface StatisticCardProps {
  icon: ComponentType<{ className?: string }>
  label: string
  value: string
  helper: string
}

function StatisticCard({ icon: Icon, label, value, helper }: StatisticCardProps) {
  return (
    <div className="rounded-lg border bg-card/60 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
          <div className="mt-1 text-xl font-semibold text-foreground">{value}</div>
        </div>
        <div className="rounded-full bg-primary/10 p-2 text-primary">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-2 text-xs text-muted-foreground">{helper}</div>
    </div>
  )
}


