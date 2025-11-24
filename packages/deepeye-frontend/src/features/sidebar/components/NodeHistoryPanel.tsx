/**
 * NodeHistoryPanel - 节点历史记录面板
 * 
 * 显示选中节点的历史执行记录，支持：
 * - 查看历史记录列表
 * - 回退到某个历史状态
 * - 清空历史记录
 */

import { useState } from 'react'
import { Clock, RotateCcw, Trash2, CheckCircle2, XCircle, Sparkles, Play } from 'lucide-react'
import { useGraphStore } from '@/store'
import { cn } from '@/shared/utils'
import type { NodeHistoryEntry } from '@/shared/types'
import { EmptyState } from '@/shared/components'

interface NodeHistoryPanelProps {
  nodeId: string
  nodeName: string
}

export function NodeHistoryPanel({ nodeId }: NodeHistoryPanelProps) {
  const getNodeHistory = useGraphStore(state => state.getNodeHistory)
  const restoreNodeHistory = useGraphStore(state => state.restoreNodeHistory)
  const clearNodeHistory = useGraphStore(state => state.clearNodeHistory)
  
  const [expandedId, setExpandedId] = useState<string | null>(null)
  
  const history = getNodeHistory(nodeId)
  
  // 格式化时间
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    // 小于 1 分钟
    if (diff < 60000) {
      return '刚刚'
    }
    // 小于 1 小时
    if (diff < 3600000) {
      return `${Math.floor(diff / 60000)} 分钟前`
    }
    // 小于 24 小时
    if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)} 小时前`
    }
    // 显示日期时间
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  
  // 获取操作类型图标和文本
  const getTypeInfo = (type: NodeHistoryEntry['type']) => {
    switch (type) {
      case 'ai_request':
        return { icon: Sparkles, text: 'AI 请求', color: 'text-purple-500' }
      case 'compute':
        return { icon: Play, text: '执行', color: 'text-blue-500' }
      case 'manual':
        return { icon: Clock, text: '手动', color: 'text-gray-500' }
    }
  }
  
  // 处理恢复
  const handleRestore = (historyId: string) => {
    restoreNodeHistory(nodeId, historyId)
  }
  
  // 处理清空
  const handleClear = () => {
    if (confirm('确定要清空所有历史记录吗？')) {
      clearNodeHistory(nodeId)
    }
  }
  
  if (history.length === 0) {
    return <EmptyState icon={Clock} title="暂无历史记录" />
  }
  
  return (
    <div className="flex flex-col h-full">
      {/* 头部 */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">历史记录</span>
          <span className="text-xs text-muted-foreground">({history.length})</span>
        </div>
        <button
          onClick={handleClear}
          className="p-1.5 hover:bg-destructive/10 text-destructive rounded transition-colors"
          title="清空历史"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      
      {/* 历史记录列表 */}
      <div className="flex-1 overflow-y-auto">
        {history.slice().reverse().map((entry) => {
          const typeInfo = getTypeInfo(entry.type)
          const TypeIcon = typeInfo.icon
          const isExpanded = expandedId === entry.id
          
          return (
            <div
              key={entry.id}
              className="border-b last:border-b-0 hover:bg-accent/50 transition-colors"
            >
              {/* 记录头部 */}
              <div
                className="p-3 cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : entry.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <TypeIcon className={cn('w-4 h-4 mt-0.5 flex-shrink-0', typeInfo.color)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">
                          {entry.prompt || typeInfo.text}
                        </span>
                        {entry.success ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-destructive flex-shrink-0" />
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {formatTime(entry.timestamp)}
                        {entry.modelId && ` · ${entry.modelId}`}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRestore(entry.id)
                    }}
                    className="p-1.5 hover:bg-primary/10 text-primary rounded transition-colors flex-shrink-0"
                    title="恢复到此状态"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

