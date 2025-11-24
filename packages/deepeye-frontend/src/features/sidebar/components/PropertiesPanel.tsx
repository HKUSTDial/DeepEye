/**
 * PropertiesPanel - 属性面板组件
 * 
 * 显示和编辑选中节点的属性
 */

import { useGraphStore, toast } from '@/store'
import { registry } from '@/nodes/registry'
import { SimpleExecutor } from '@/nodes/execution/SimpleExecutor'
import { Settings, Play, Clock, AlertCircle } from 'lucide-react'
import { useState } from 'react'
import { NodeHistoryPanel } from './NodeHistoryPanel'
import { cn } from '@/shared/utils'
import { EmptyState } from '@/shared/components'

export function PropertiesPanel() {
  const nodes = useGraphStore(state => state.nodes)
  const edges = useGraphStore(state => state.edges)
  const selectedNodeIds = useGraphStore(state => state.selectedNodes)
  const updateNodeData = useGraphStore(state => state.updateNodeData)

  // ⚠️ Hooks 必须在顶层调用，不能在条件语句中
  const [isExecuting, setIsExecuting] = useState(false)
  const [activeTab, setActiveTab] = useState<'properties' | 'history'>('properties')

  // 获取选中的节点对象
  const selectedNodes = nodes.filter(node => selectedNodeIds.includes(node.id))

  // 如果没有选中节点
  if (selectedNodes.length === 0) {
    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">属性面板</h2>
        </div>
        <EmptyState
          icon={Settings}
          title="未选中节点"
          description="选择一个节点以查看其属性"
        />
      </div>
    )
  }

  // 如果选中多个节点
  if (selectedNodes.length > 1) {
    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">属性面板</h2>
        </div>
        <EmptyState
          icon={Settings}
          title={`已选中 ${selectedNodes.length} 个节点`}
          description="请选择单个节点以编辑属性"
        />
      </div>
    )
  }

  // 单个节点
  const node = selectedNodes[0]
  const definition = registry.get(node.type || '')

  if (!definition) {
    return (
      <div className="w-80 border-l border-border bg-background flex flex-col h-full">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">属性面板</h2>
        </div>
        <EmptyState
          icon={AlertCircle}
          title={`未知节点类型: ${node.type}`}
        />
      </div>
    )
  }

  const properties = Object.entries(definition.properties || {})
  const attributes = node.data?.attributes || {}

  // 更新属性值
  const handlePropertyChange = (key: string, value: any) => {
    updateNodeData(node.id, {
      attributes: {
        ...attributes,
        [key]: value
      }
    })
  }

  // 渲染属性输入控件
  const renderPropertyInput = (key: string, prop: any, value: any) => {
    const inputClassName = "w-full px-3 py-1.5 text-sm rounded border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-[#007AFF] focus:border-transparent"

    // 文本输入（多行）
    if (((prop.type === 'text' || prop.type === 'string' || prop.type === 'textarea') && prop.multiline)) {
      return (
        <textarea
          value={value || ''}
          onChange={(e) => handlePropertyChange(key, e.target.value)}
          placeholder={prop.placeholder}
          rows={3}
          className={`${inputClassName} resize-none`}
        />
      )
    }

    // 文本输入（单行）
    if ((prop.type === 'text' || prop.type === 'string') && !prop.multiline) {
      return (
        <input
          type="text"
          value={value || ''}
          onChange={(e) => handlePropertyChange(key, e.target.value)}
          placeholder={prop.placeholder}
          className={inputClassName}
        />
      )
    }

    // 数字输入
    if (prop.type === 'number') {
      return (
        <input
          type="number"
          value={value ?? ''}
          onChange={(e) => handlePropertyChange(key, parseFloat(e.target.value) || 0)}
          min={prop.min}
          max={prop.max}
          placeholder={prop.placeholder}
          className={inputClassName}
        />
      )
    }

    // 布尔输入
    if (prop.type === 'boolean') {
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={value || false}
            onChange={(e) => handlePropertyChange(key, e.target.checked)}
            className="w-4 h-4 rounded border-border text-[#007AFF] focus:ring-2 focus:ring-[#007AFF]"
          />
          <span className="text-sm text-muted-foreground">
            {value ? '是' : '否'}
          </span>
        </label>
      )
    }

    // 下拉选择
    if (prop.type === 'select' && prop.options) {
      return (
        <select
          value={value || ''}
          onChange={(e) => handlePropertyChange(key, e.target.value)}
          className={inputClassName}
        >
          {prop.options.map((option: any) => {
            const optionValue = typeof option === 'string' ? option : option.value
            const optionLabel = typeof option === 'string' ? option : option.label
            return (
              <option key={optionValue} value={optionValue}>
                {optionLabel}
              </option>
            )
          })}
        </select>
      )
    }

    // 颜色选择
    if (prop.type === 'color') {
      return (
        <input
          type="color"
          value={value || '#000000'}
          onChange={(e) => handlePropertyChange(key, e.target.value)}
          className="w-full h-10 rounded border border-border cursor-pointer"
        />
      )
    }

    return null
  }

  // 执行节点（单节点测试，使用 SimpleExecutor）
  const handleExecute = async () => {
    try {
      setIsExecuting(true)

      console.log('🚀 开始执行节点:', node.type, node.id)

      // 创建执行器（单节点测试场景，保持使用 SimpleExecutor）
      const executor = new SimpleExecutor(nodes, edges)

      // 执行节点（会自动执行所有依赖的上游节点）
      // compute() 方法现在是 async 的，会调用后端 API
      const outputs = await executor.executeNode(node.id)

      // 更新节点数据（合并输出到 attributes）
      updateNodeData(node.id, {
        attributes: {
          ...attributes,
          ...outputs
        }
      })

      console.log('✅ 节点执行成功:', node.type, outputs)
      toast.success('节点执行成功')
    } catch (error: any) {
      console.error('❌ 节点执行失败:', error)
      toast.error(`执行失败: ${error.message || '未知错误'}`)
    } finally {
      setIsExecuting(false)
    }
  }

  return (
    <div className="w-80 border-l border-border bg-background flex flex-col h-full">
      {/* 标题 */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-foreground">属性面板</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{definition.label}</p>
          </div>
          <button
            onClick={handleExecute}
            disabled={isExecuting}
            className="px-3 py-1.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground text-xs font-medium rounded flex items-center gap-1.5 transition-colors"
            title="执行节点"
          >
            <Play className="w-3.5 h-3.5" />
            {isExecuting ? '执行中...' : '执行'}
          </button>
        </div>
      </div>

      {/* 标签页 */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setActiveTab('properties')}
          className={cn(
            'flex-1 px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'properties'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          <div className="flex items-center justify-center gap-2">
            <Settings className="w-4 h-4" />
            <span>属性</span>
          </div>
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={cn(
            'flex-1 px-4 py-2 text-sm font-medium transition-colors',
            activeTab === 'history'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          <div className="flex items-center justify-center gap-2">
            <Clock className="w-4 h-4" />
            <span>历史</span>
          </div>
        </button>
      </div>

      {/* 内容区域 */}
      {activeTab === 'properties' ? (
        /* 属性列表 */
        <div className="flex-1 overflow-y-auto mac-scrollbar">
          {properties.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-muted-foreground">此节点没有可编辑的属性</p>
            </div>
          ) : (
            <div className="p-4 space-y-4">
              {properties.map(([key, prop]) => {
                const value = attributes[key] ?? prop.default

                return (
                  <div key={key} className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground">
                      {prop.label || key}
                    </label>
                    {renderPropertyInput(key, prop, value)}
                    {prop.description && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {prop.description}
                      </p>
                    )}
                  </div>
                )
              })}
          </div>
        )}

          {/* 输入/输出显示 */}
          <div className="border-t border-border">
            {/* 输入 */}
            {Object.keys(definition.inputs).length > 0 && (
              <div className="px-4 py-3">
                <h3 className="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                  输入端口
                </h3>
                <div className="space-y-2.5">
                  {Object.entries(definition.inputs).map(([key, input]) => (
                    <div key={key} className="flex items-center justify-between gap-3 group">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-foreground truncate">
                          {input.label || key}
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                          {input.type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 输出 */}
            {Object.keys(definition.outputs).length > 0 && (
              <div className="px-4 py-3 border-t border-border">
                <h3 className="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                  输出端口
                </h3>
                <div className="space-y-2.5">
                  {Object.entries(definition.outputs).map(([key, output]) => (
                    <div key={key} className="flex items-center justify-between gap-3 group">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-foreground truncate">
                          {output.label || key}
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20">
                          {output.type}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <NodeHistoryPanel nodeId={node.id} nodeName={definition.label} />
      )}

      {/* 底部信息 */}
      <div className="px-4 py-2 border-t border-border">
        <p className="text-xs text-muted-foreground">
          节点 ID: {node.id}
        </p>
      </div>
    </div>
  )
}

