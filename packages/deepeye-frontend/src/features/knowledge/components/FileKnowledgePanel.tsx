import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ColumnMetadata, FileMetadata, FileMetadataPayload, StoredFile } from '@/shared/api'
import { filesAPI, knowledgeAPI } from '@/shared/api'
import { EmptyState } from '@/shared/components'
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
  Download,
  FileQuestion,
  Loader2,
  NotebookPen,
  RefreshCw,
  Save,
  Search,
} from 'lucide-react'
import { downloadFileFromUrl } from '@/shared/utils'

interface StructuredFieldSchema {
  name: string
  type?: string
  sample?: string
}

interface StructuredSchemaResult {
  fields: StructuredFieldSchema[]
}

type FileCategory = 'structured' | 'unstructured'

export function FileKnowledgePanel() {
  const [files, setFiles] = useState<StoredFile[]>([])
  const [filesLoading, setFilesLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [metadata, setMetadata] = useState<FileMetadata | null>(null)
  const [summary, setSummary] = useState('')
  const [annotations, setAnnotations] = useState('')
  const [isMetadataLoading, setIsMetadataLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [structuredSchema, setStructuredSchema] = useState<StructuredFieldSchema[]>([])
  const [structuredDescriptions, setStructuredDescriptions] = useState<Record<string, string>>({})

  const loadFiles = useCallback(async () => {
    setFilesLoading(true)
    try {
      const data = await filesAPI.list()
      const sorted = sortByCreatedAt(data)
      setFiles(sorted)
      setSelectedFileId((prev) => prev ?? sorted[0]?.id ?? null)
    } catch (error) {
      console.error('加载文件失败:', error)
      toast.error('加载文件失败，请稍后重试')
    } finally {
      setFilesLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadFiles()
  }, [loadFiles])

  const selectedFile = useMemo(
    () => files.find((file) => file.id === selectedFileId) ?? null,
    [files, selectedFileId]
  )

  const fileCategory: FileCategory | null = useMemo(() => {
    if (!selectedFile) return null
    return classifyFile(selectedFile)
  }, [selectedFile])

  useEffect(() => {
    if (!selectedFile) {
      setMetadata(null)
      setSummary('')
      setAnnotations('')
      setStructuredSchema([])
      setStructuredDescriptions({})
      setDownloadUrl(null)
      return
    }

    let cancelled = false
    const hydrate = async () => {
      setIsMetadataLoading(true)
      try {
        const metaResult = await knowledgeAPI.getFileMetadata(selectedFile.id)

        if (cancelled || !metaResult) {
          setMetadata(null)
          setSummary('')
          setAnnotations('')
          setStructuredDescriptions({})
          setStructuredSchema([])
          return
        }

        setMetadata(metaResult)
        setSummary(metaResult.summary ?? '')
        setAnnotations(metaResult.annotations ?? '')
        if (metaResult.column_metadata) {
          setStructuredDescriptions(
            Object.entries(metaResult.column_metadata).reduce<Record<string, string>>(
              (acc, [key, value]) => {
                acc[key] = typeof value?.description === 'string' ? (value.description as string) : ''
                return acc
              },
              {}
            )
          )
          setStructuredSchema(
            Object.entries(metaResult.column_metadata).map(([name, info]) => ({
              name,
              type: typeof info?.type === 'string' ? (info.type as string) : undefined,
              sample: typeof info?.sample === 'string' ? (info.sample as string) : undefined,
            }))
          )
        } else {
          setStructuredDescriptions({})
          setStructuredSchema([])
        }

        if (classifyFile(selectedFile) === 'structured') {
          try {
            const { url } = await filesAPI.getDownloadUrl(selectedFile.id)
            if (cancelled) {
              return
            }
            setDownloadUrl(url)
            const parsed = await buildStructuredSchema(url, selectedFile)
            if (!cancelled) {
              if (parsed?.fields?.length) {
                setStructuredSchema(parsed.fields)
              } else {
                setStructuredSchema([])
              }
            }
          } catch (error) {
            if (!cancelled) {
              console.warn('解析结构化文件失败:', error)
              setStructuredSchema([])
            }
          }
        } else {
          setStructuredSchema([])
        }
      } finally {
        if (!cancelled) {
          setIsMetadataLoading(false)
        }
      }
    }

    void hydrate()
    return () => {
      cancelled = true
    }
  }, [selectedFile])

  useEffect(() => {
    setStructuredDescriptions((prev) => {
      const next: Record<string, string> = {}
      structuredSchema.forEach((field) => {
        next[field.name] = prev[field.name] ?? ''
      })
      return next
    })
  }, [structuredSchema])

  const filteredFiles = useMemo(() => {
    if (!searchQuery) return files
    const keyword = searchQuery.toLowerCase()
    return files.filter((file) =>
      [file.filename, file.original_name, file.content_type]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(keyword))
    )
  }, [files, searchQuery])

  const handleSaveMetadata = async () => {
    if (!selectedFile) {
      toast.info('请先选择一个文件')
      return
    }

    let columnMetadata: ColumnMetadata | null = null
    if (fileCategory === 'structured') {
      columnMetadata = structuredSchema.reduce<ColumnMetadata>((acc, field) => {
        acc[field.name] = {
          description: structuredDescriptions[field.name]?.trim() || undefined,
          type: field.type,
          sample: field.sample,
        }
        return acc
      }, {})
    }

    const payload: FileMetadataPayload = {
      summary: summary.trim() || null,
      annotations: annotations.trim() || null,
      column_metadata: columnMetadata,
    }

    setIsSaving(true)
    try {
      const updated = await knowledgeAPI.upsertFileMetadata(selectedFile.id, payload)
      setMetadata(updated)
      toast.success('文件知识已保存')
    } catch (error) {
      console.error('保存文件知识失败:', error)
      toast.error('保存失败，请稍后再试')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDirectDownload = async () => {
    if (!selectedFile) return
    try {
      let url = downloadUrl
      if (!url) {
        const result = await filesAPI.getDownloadUrl(selectedFile.id)
        url = result.url
        setDownloadUrl(url)
      }
      if (!url) {
        throw new Error('无法生成下载链接')
      }
      await downloadFileFromUrl(url, selectedFile.original_name || selectedFile.filename || 'download')
    } catch (error) {
      console.error('获取下载链接失败:', error)
      toast.error('下载失败，请稍后重试')
    }
  }

  const fileCategoryDescription =
    fileCategory === 'structured'
      ? '自动识别为结构化数据，可维护字段的业务含义'
      : '识别为非结构化文件，可通过批注沉淀语义'

  return (
    <div className="grid gap-6 lg:grid-cols-[320px,1fr]">
      <Card className="h-full">
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle>知识源文件</CardTitle>
              <CardDescription>选择需要沉淀知识的文件，支持关键词筛选</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => void loadFiles()} disabled={filesLoading}>
              <RefreshCw className={`h-4 w-4 ${filesLoading ? 'animate-spin' : ''}`} />
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
        <CardContent className="max-h-[calc(100vh-320px)] overflow-y-auto">
          {filesLoading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            </div>
          ) : filteredFiles.length === 0 ? (
            <EmptyState
              icon={FileQuestion}
              title={searchQuery ? '没有匹配的文件' : '当前暂无文件'}
              description={
                searchQuery
                  ? '试着更换关键字，或清空搜索条件'
                  : '去文件空间上传素材，即可在此沉淀知识'
              }
              className="py-8"
            />
          ) : (
            <div className="space-y-2">
              {filteredFiles.map((file) => {
                const isActive = file.id === selectedFileId
                return (
                  <button
                    key={file.id}
                    type="button"
                    onClick={() => setSelectedFileId(file.id)}
                    className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                      isActive
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border hover:border-primary/40'
                    }`}
                  >
                    <div className="text-sm font-semibold">
                      {file.original_name || file.filename}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {file.content_type || '未知类型'} · {(file.size / 1024).toFixed(0)} KB
                    </div>
                    <div className="mt-1 text-[11px] text-muted-foreground/80">
                      上传于 {formatRelativeTime(file.created_at)}
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
          <CardTitle>文件知识编辑</CardTitle>
          <CardDescription>补充摘要、结构化字段与业务批注</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!selectedFile ? (
            <EmptyState
              icon={NotebookPen}
              title="请选择一个文件"
              description="从左侧列表选择文件，系统会自动载入历史知识"
              className="py-16"
            />
          ) : (
            <div className="space-y-6">
              <div className="rounded-2xl border bg-muted/30 p-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {selectedFile.original_name || selectedFile.filename}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {selectedFile.content_type || '未知类型'} · {(selectedFile.size / 1024).toFixed(0)} KB
                    </p>
                    <p className="text-xs text-muted-foreground/80">{fileCategoryDescription}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDirectDownload}
                    disabled={isMetadataLoading && !downloadUrl}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    下载文件
                  </Button>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="file-summary">内容摘要</Label>
                  <Textarea
                    id="file-summary"
                    placeholder="概括文件包含的核心信息，方便下游引用"
                    value={summary}
                    disabled={isMetadataLoading}
                    className="mt-2 min-h-[120px]"
                    onChange={(event) => setSummary(event.target.value)}
                  />
                </div>

                {fileCategory === 'structured' && (
                  <div>
                    <div className="flex items-center justify-between">
                      <Label>字段描述</Label>
                      <span className="text-xs text-muted-foreground">自动提取列名，可补充业务含义</span>
                    </div>
                    {structuredSchema.length === 0 ? (
                      <div className="mt-3 rounded-xl border border-dashed border-muted bg-muted/20 p-4 text-sm text-muted-foreground">
                        暂未识别出字段结构，可尝试刷新或先上传 CSV / JSON 文件。
                      </div>
                    ) : (
                      <div className="mt-3 max-h-[320px] space-y-3 overflow-y-auto pr-2">
                        {structuredSchema.map((field) => (
                          <div
                            key={field.name}
                            className="rounded-xl border border-border/60 bg-background/80 p-3 shadow-sm"
                          >
                            <div className="flex items-center justify-between gap-3 text-sm font-semibold">
                              <span>{field.name}</span>
                              <span className="text-xs text-muted-foreground">
                                {field.type || '类型未识别'}
                              </span>
                            </div>
                            {field.sample && (
                              <p className="mt-1 text-xs text-muted-foreground">
                                示例：{field.sample}
                              </p>
                            )}
                            <Input
                              className="mt-3"
                              placeholder="请输入字段的业务口径 / 说明"
                              value={structuredDescriptions[field.name] ?? ''}
                              onChange={(event) =>
                                setStructuredDescriptions((prev) => ({
                                  ...prev,
                                  [field.name]: event.target.value,
                                }))
                              }
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div>
                  <Label htmlFor="file-annotations">
                    {fileCategory === 'structured' ? '业务批注（可选）' : '业务批注'}
                  </Label>
                  <Textarea
                    id="file-annotations"
                    placeholder="记录业务背景、使用场景、注意事项等"
                    value={annotations}
                    disabled={isMetadataLoading}
                    className="mt-2 min-h-[140px]"
                    onChange={(event) => setAnnotations(event.target.value)}
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4 border-t pt-4 text-xs text-muted-foreground">
                <div>
                  {metadata
                    ? `上次保存：${formatDateTime(metadata.updated_at)}`
                    : '尚未写入知识，可立即保存'}
                </div>
                <Button onClick={handleSaveMetadata} disabled={isSaving || isMetadataLoading}>
                  {(isSaving || isMetadataLoading) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <Save className="mr-2 h-4 w-4" />
                  保存知识
                </Button>
              </div>

            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

const structuredMimeTypes = ['text/csv', 'application/json']
const structuredExtensions = ['.csv', '.tsv', '.json', '.ndjson']

function classifyFile(file: StoredFile): FileCategory {
  const extension = getFileExtension(file)
  const mime = file.content_type?.toLowerCase() ?? ''
  if (structuredExtensions.includes(extension) || structuredMimeTypes.includes(mime)) {
    return 'structured'
  }
  return 'unstructured'
}

function sortByCreatedAt(items: StoredFile[]) {
  return [...items].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
}

function formatDateTime(value?: string | null) {
  if (!value) return '--'
  return new Date(value).toLocaleString()
}

function formatRelativeTime(value?: string | null) {
  if (!value) return '--'
  const diff = Date.now() - new Date(value).getTime()
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`
  return `${Math.floor(diff / 86400000)} 天前`
}

function getFileExtension(file: StoredFile): string {
  const name = (file.original_name || file.filename || '').toLowerCase()
  const dot = name.lastIndexOf('.')
  if (dot === -1) return ''
  return name.slice(dot)
}

async function buildStructuredSchema(
  downloadUrl: string,
  file: StoredFile
): Promise<StructuredSchemaResult | null> {
  try {
    const extension = getFileExtension(file)
    const contentType = file.content_type?.toLowerCase() ?? ''
    const response = await fetch(downloadUrl)
    if (!response.ok) return null

    const text = await response.text()

    if (
      extension === '.json' ||
      extension === '.ndjson' ||
      contentType.includes('json')
    ) {
      return { fields: parseJsonSample(text) }
    }

    if (
      extension === '.csv' ||
      extension === '.tsv' ||
      contentType.includes('csv') ||
      contentType === 'text/plain'
    ) {
      return { fields: parseDelimitedSample(text) }
    }
  } catch (error) {
    console.warn('无法解析结构化字段', error)
  }
  return null
}

function parseDelimitedSample(sample: string): StructuredFieldSchema[] {
  const [headerLine, firstRow] = sample.split(/\r?\n/)
  if (!headerLine) return []
  const delimiter = headerLine.includes('\t') ? '\t' : ','
  const headers = headerLine.split(delimiter).map((item) => item.trim())
  const values = firstRow ? firstRow.split(delimiter).map((item) => item.trim()) : []

  return headers.map((name, index) => ({
    name: name || `column_${index + 1}`,
    type: inferValueType(values[index]),
    sample: values[index],
  }))
}

function parseJsonSample(sample: string): StructuredFieldSchema[] {
  try {
    const data = JSON.parse(sample)
    const target = Array.isArray(data) ? data[0] : data
    if (!target || typeof target !== 'object') {
      return []
    }
    return Object.entries(target).map(([key, value]) => ({
      name: key,
      type: inferValueType(value),
      sample: formatPrimitive(value),
    }))
  } catch {
    return []
  }
}

function inferValueType(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined
  if (Array.isArray(value)) return 'array'
  return typeof value
}

function formatPrimitive(value: unknown) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') {
    return JSON.stringify(value).slice(0, 120)
  }
  return String(value)
}

