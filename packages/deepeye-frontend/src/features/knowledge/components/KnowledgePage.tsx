import { useMemo, useState } from 'react'
import { ThemeToggle } from '@/shared/components'
import { BookCopy, Database, FileText } from 'lucide-react'
import { FileKnowledgePanel } from './FileKnowledgePanel'
import { DatabaseKnowledgePanel } from './DatabaseKnowledgePanel'

const tabs = [
  { id: 'file', label: '文件知识', description: '总结、批注和结构化字段', icon: FileText },
  {
    id: 'database',
    label: '数据库知识',
    description: '表字段、业务指标、规则与样例',
    icon: Database,
  },
] as const

type KnowledgeTab = (typeof tabs)[number]['id']

export function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<KnowledgeTab>('file')

  const ActivePanel = useMemo(() => {
    return activeTab === 'file' ? <FileKnowledgePanel /> : <DatabaseKnowledgePanel />
  }, [activeTab])

  return (
    <div className="flex h-full flex-col bg-background">
      <header className="border-b bg-card px-6 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground">知识库</p>
            <h1 className="mt-1 text-2xl font-bold text-foreground">知识资产管理中心</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              统一维护文件与数据库知识，让智能体快速调用可信上下文。
            </p>
          </div>
          <ThemeToggle />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = tab.id === activeTab
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 rounded-xl border px-4 py-2 text-left text-sm transition ${
                  isActive
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-foreground hover:border-primary/40'
                }`}
              >
                <Icon className="h-4 w-4" />
                <div>
                  <p className="font-medium">{tab.label}</p>
                  <p className="text-xs text-muted-foreground">{tab.description}</p>
                </div>
                {isActive && <BookCopy className="ml-auto h-4 w-4 text-primary" />}
              </button>
            )
          })}
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-6">{ActivePanel}</main>
    </div>
  )
}


