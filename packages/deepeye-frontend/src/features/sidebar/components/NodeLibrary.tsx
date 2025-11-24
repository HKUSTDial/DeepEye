/**
 * NodeLibrary - 节点库组件
 * 
 * 显示所有注册的节点，按分类组织
 * 支持拖拽节点到画布
 */

import { useState } from 'react'
import { registry } from '@/nodes/registry'
import { cn } from '@/shared/utils'
import { ChevronDown, ChevronRight, Search } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export function NodeLibrary() {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(registry.getCategories()) // 默认展开所有分类
  )

  // 获取所有分类
  const categories = registry.getCategories()

  // 切换分类展开/折叠
  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }

  // 处理拖拽开始
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType)
    event.dataTransfer.effectAllowed = 'move'
  }

  // 过滤节点
  const filterNodes = (category: string) => {
    const nodes = registry.getByCategory(category)
    if (!searchQuery) return nodes
    
    const query = searchQuery.toLowerCase()
    return nodes.filter(node => 
      node.label.toLowerCase().includes(query) ||
      node.type.toLowerCase().includes(query)
    )
  }

  return (
    <div className="w-64 border-r border-border bg-background flex flex-col h-full">
      {/* 标题 */}
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground">节点库</h2>
      </div>

      {/* 搜索框 */}
      <div className="px-3 py-2 border-b border-border">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="搜索节点..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm rounded border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[#007AFF] focus:border-transparent"
          />
        </div>
      </div>

      {/* 节点列表 */}
      <div className="flex-1 overflow-y-auto mac-scrollbar">
        {categories.map(category => {
          const nodes = filterNodes(category)
          if (nodes.length === 0) return null

          const isExpanded = expandedCategories.has(category)

          return (
            <div key={category} className="border-b border-border last:border-b-0">
              {/* 分类标题 */}
              <button
                onClick={() => toggleCategory(category)}
                className="w-full px-3 py-2 flex items-center gap-2 hover:bg-muted/50 transition-colors"
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
                <span className="text-sm font-medium text-foreground">{category}</span>
                <span className="ml-auto text-xs text-muted-foreground">{nodes.length}</span>
              </button>

              {/* 节点列表 */}
              {isExpanded && (
                <div className="pb-2">
                  {nodes.map(node => {
                    const Icon = node.icon as LucideIcon | undefined

                    return (
                      <div
                        key={node.type}
                        draggable
                        onDragStart={(e) => onDragStart(e, node.type)}
                        className={cn(
                          'mx-2 mb-1 px-3 py-2 rounded cursor-move',
                          'flex items-center gap-2',
                          'hover:bg-muted transition-colors',
                          'border border-transparent hover:border-border'
                        )}
                      >
                        {Icon && (
                          <div
                            className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: node.color || '#5856D6' }}
                          >
                            <Icon className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-foreground truncate">
                            {node.label}
                          </div>
                          <div className="text-xs text-muted-foreground truncate">
                            {node.type}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}

        {/* 无结果提示 */}
        {categories.every(cat => filterNodes(cat).length === 0) && (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-muted-foreground">未找到匹配的节点</p>
          </div>
        )}
      </div>

      {/* 底部统计 */}
      <div className="px-4 py-2 border-t border-border">
        <p className="text-xs text-muted-foreground">
          共 {registry.getAll().length} 个节点
        </p>
      </div>
    </div>
  )
}

