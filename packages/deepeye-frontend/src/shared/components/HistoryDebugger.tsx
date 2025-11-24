/**
 * 历史记录调试工具
 * 仅在开发模式下显示，帮助开发者调试撤销/重做系统
 */

import { useState } from 'react'
import { useGraphStore } from '@/store'
import { History, ChevronUp, ChevronDown, X } from 'lucide-react'
import { cn } from '@/shared/utils'

export function HistoryDebugger() {
  const [isOpen, setIsOpen] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)
  
  const { history, currentHistoryIndex, getHistoryInfo, canUndo, canRedo } = useGraphStore()
  const historyInfo = getHistoryInfo()

  // 只在开发模式下渲染
  if (!import.meta.env.DEV) {
    return null
  }

  // 快捷键提示：Ctrl/Cmd + Shift + H 切换显示
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          "fixed bottom-4 right-4 z-50",
          "p-3 rounded-lg shadow-lg",
          "bg-primary text-primary-foreground",
          "hover:scale-105 transition-transform",
          "flex items-center gap-2"
        )}
        title="Open History Debugger (Dev Only)"
      >
        <History className="w-5 h-5" />
        <span className="text-xs font-mono">
          {historyInfo.current}/{historyInfo.total}
        </span>
      </button>
    )
  }

  return (
    <div
      className={cn(
        "fixed bottom-4 right-4 z-50",
        "w-96 max-h-[600px] flex flex-col",
        "bg-background border-2 border-primary rounded-lg shadow-2xl",
        "overflow-hidden"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-primary text-primary-foreground">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5" />
          <h3 className="text-sm font-bold">History Debugger</h3>
          <span className="text-xs opacity-75">(Dev Only)</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-primary-foreground/20 rounded"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronUp className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 hover:bg-primary-foreground/20 rounded"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {isExpanded && (
        <>
          {/* Stats */}
          <div className="p-3 bg-muted/50 border-b border-border">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div className="text-muted-foreground">Total History</div>
                <div className="text-lg font-bold">{historyInfo.total}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Current Index</div>
                <div className="text-lg font-bold">{historyInfo.current}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Can Undo</div>
                <div className={cn(
                  "font-bold",
                  canUndo() ? "text-green-600" : "text-red-600"
                )}>
                  {canUndo() ? '✓ Yes' : '✗ No'}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">Can Redo</div>
                <div className={cn(
                  "font-bold",
                  canRedo() ? "text-green-600" : "text-red-600"
                )}>
                  {canRedo() ? '✓ Yes' : '✗ No'}
                </div>
              </div>
            </div>
          </div>

          {/* History List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-1">
            {history.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">
                No history yet. Start creating nodes!
              </div>
            ) : (
              history.map((state, index) => {
                const isCurrent = index === currentHistoryIndex
                const isPast = index < currentHistoryIndex
                const isFuture = index > currentHistoryIndex

                return (
                  <div
                    key={`${state.timestamp}-${index}`}
                    className={cn(
                      "p-2 rounded text-xs border",
                      isCurrent && "bg-primary/20 border-primary font-bold",
                      isPast && "bg-muted/30 border-muted opacity-70",
                      isFuture && "bg-muted/10 border-muted/50 opacity-40"
                    )}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono">
                        {isCurrent && '▶ '}
                        #{index}
                        {isCurrent && ' (current)'}
                      </span>
                      <span className="text-muted-foreground">
                        {new Date(state.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="flex gap-3 text-muted-foreground">
                      <span>Nodes: {state.nodes.length}</span>
                      <span>Edges: {state.edges.length}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Keyboard Shortcuts */}
          <div className="p-3 bg-muted/30 border-t border-border">
            <div className="text-xs font-semibold mb-2">Keyboard Shortcuts</div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span>Undo</span>
                <code className="font-mono bg-background px-1 rounded">Ctrl+Z</code>
              </div>
              <div className="flex justify-between">
                <span>Redo</span>
                <code className="font-mono bg-background px-1 rounded">Ctrl+Shift+Z</code>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

