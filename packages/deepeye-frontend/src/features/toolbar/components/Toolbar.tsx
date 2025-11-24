import { useThemeStore, useGraphStore, toast } from '@/store'
import { SimpleExecutor } from '@/nodes/execution'
import { Undo2, Redo2, Save, Moon, Sun, Play, Bug, Download, Upload, ArrowLeft, Loader2 } from 'lucide-react'
import { useState, useEffect } from 'react'

interface ToolbarProps {
  /** 调试器是否显示 */
  showDebugger: boolean

  /** 切换调试器显示 */
  onToggleDebugger: () => void

  /** 工作流名称 */
  workflowName?: string

  /** 工作流 ID */
  workflowId?: string

  /** 返回按钮回调 */
  onBack?: () => void

  /** 保存按钮回调 */
  onSave?: () => void

  /** 是否正在保存 */
  isSaving?: boolean
}

export function Toolbar({
  showDebugger,
  onToggleDebugger,
  workflowName,
  onBack,
  onSave,
  isSaving = false
}: ToolbarProps) {
  const { theme, toggleTheme } = useThemeStore()

  // ============ 历史记录管理 ============
  const { undo, redo, canUndo, canRedo, getHistoryInfo, nodes, edges, setNodes, setEdges, updateNodeData } = useGraphStore()

  // ============ 执行状态 ============
  const [isRunning, setIsRunning] = useState(false)
  const [executionProgress, setExecutionProgress] = useState(0)
  const [currentNode, setCurrentNode] = useState<string | null>(null)
  
  // 获取历史信息用于提示
  const historyInfo = getHistoryInfo()
  
  // 判断是否为 Mac
  const isMac = typeof navigator !== 'undefined' &&
                navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const modKey = isMac ? '⌘' : 'Ctrl'

  // ============ 事件处理 ============

  const handleUndo = () => {
    if (canUndo()) {
      undo()
    }
  }

  const handleRedo = () => {
    if (canRedo()) {
      redo()
    }
  }

  const handleSave = () => {
    if (onSave) {
      onSave()
    } else {
      console.log('💾 Save clicked - to be implemented')
    }
  }

  // ============ 键盘快捷键 ============
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S / Cmd+S - 保存
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        if (onSave && !isSaving) {
          handleSave()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onSave, isSaving])

  /**
   * 运行整个工作流（使用 SimpleExecutor）
   */
  const handleRun = async () => {
    try {
      setIsRunning(true)
      setExecutionProgress(0)
      setCurrentNode(null)

      if (nodes.length === 0) {
        toast.warning('工作流为空，没有可执行的节点')
        return
      }

      console.log('🚀 开始执行工作流')
      console.log(`📊 总共 ${nodes.length} 个节点，${edges.length} 条连接`)

      const executor = new SimpleExecutor(nodes, edges)

      // 找到所有叶子节点（没有输出连接的节点）
      const leafNodes = nodes.filter(node => {
        return !edges.some(edge => edge.source === node.id)
      })

      if (leafNodes.length === 0) {
        toast.warning('工作流中没有输出节点')
        return
      }

      console.log(`� 找到 ${leafNodes.length} 个叶子节点:`, leafNodes.map(n => n.id))

      // 执行所有叶子节点（会自动执行依赖的上游节点）
      let completedCount = 0
      const totalCount = leafNodes.length

      for (const leafNode of leafNodes) {
        setCurrentNode(leafNode.id)
        console.log(`🔄 执行节点: ${leafNode.type} (${leafNode.id})`)

        const outputs = await executor.executeNode(leafNode.id)

        // 更新节点数据
        const attributes = leafNode.data?.attributes || {}
        updateNodeData(leafNode.id, {
          attributes: {
            ...attributes,
            ...outputs
          }
        })

        completedCount++
        setExecutionProgress(Math.round((completedCount / totalCount) * 100))
        console.log(`✅ 节点完成: ${leafNode.type}`, outputs)
      }

      console.log('\n✅ 工作流执行完成')
      toast.success('工作流执行成功！')
    } catch (error: any) {
      console.error('❌ 执行失败:', error)
      toast.error(`执行失败: ${error.message || '未知错误'}`)
    } finally {
      setIsRunning(false)
      setExecutionProgress(0)
      setCurrentNode(null)
    }
  }

  /**
   * 导出当前图为 JSON 文件
   */
  const handleExport = () => {
    const graphData = {
      nodes,
      edges,
      version: '1.0.0',
      exportedAt: new Date().toISOString(),
    }

    const dataStr = JSON.stringify(graphData, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `graph-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    console.log('✅ Exported graph to JSON')
  }

  /**
   * 从 JSON 文件导入图
   */
  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      
      const reader = new FileReader()
      reader.onload = (event) => {
        try {
          const content = event.target?.result as string
          const graphData = JSON.parse(content)
          
          if (!graphData.nodes || !graphData.edges) {
            throw new Error('Invalid graph data format')
          }
          
          setNodes(graphData.nodes)
          setEdges(graphData.edges)
          
          console.log(`✅ Imported graph with ${graphData.nodes.length} nodes and ${graphData.edges.length} edges`)
        } catch (error) {
          console.error('❌ Failed to import graph:', error)
          alert('Failed to import graph. Please check the file format.')
        }
      }
      
      reader.readAsText(file)
    }
    
    input.click()
  }

  return (
    <div className="mac-toolbar h-14 px-4 flex items-center justify-between">
      {/* 左侧：返回按钮 + 工作流名称 */}
      <div className="flex items-center gap-3">
        {onBack && (
          <>
            <button
              onClick={onBack}
              className="mac-button px-3 flex items-center gap-1.5"
              title="返回工作流列表"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">返回</span>
            </button>
            <div className="mac-divider w-px h-5" />
          </>
        )}

        {/* 工作流名称 */}
        <div className="flex items-center gap-2.5">
          <h1 className="text-[15px] font-semibold text-foreground">
            {workflowName || 'Huan Graph Flow'}
          </h1>
        </div>
      </div>
      
      {/* 中间：操作按钮 */}
      <div className="flex items-center gap-1">
        {/* 历史记录 */}
        <button 
          className="mac-button px-3"
          disabled={!canUndo()}
          onClick={handleUndo}
          title={`Undo (${modKey}+Z)${historyInfo.current > 0 ? ` - ${historyInfo.current} steps` : ''}`}
          aria-label="Undo last action"
          aria-keyshortcuts={`${modKey}+Z`}
        >
          <Undo2 className="w-4 h-4" />
        </button>
        <button 
          className="mac-button px-3"
          disabled={!canRedo()}
          onClick={handleRedo}
          title={`Redo (${modKey}+Shift+Z)${canRedo() ? ` - ${historyInfo.total - historyInfo.current - 1} steps` : ''}`}
          aria-label="Redo last undone action"
          aria-keyshortcuts={`${modKey}+Shift+Z`}
        >
          <Redo2 className="w-4 h-4" />
        </button>
        
        <div className="mac-divider w-px h-5 mx-1" />

        {/* 执行控制 */}
        <button
          className="mac-button-primary flex items-center gap-1.5"
          onClick={handleRun}
          disabled={isRunning || nodes.length === 0}
          title={nodes.length === 0 ? "画布上没有节点" : "运行工作流"}
          aria-label="Run workflow"
        >
          {isRunning ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>运行中 {executionProgress > 0 ? `${executionProgress}%` : ''}</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              <span>运行</span>
            </>
          )}
        </button>

        <div className="mac-divider w-px h-5 mx-1" />
        
        {/* 导出/导入 */}
        <button 
          className="mac-button px-3"
          onClick={handleExport}
          title="Export to JSON"
          aria-label="Export graph to JSON file"
        >
          <Download className="w-4 h-4" />
        </button>
        <button 
          className="mac-button px-3"
          onClick={handleImport}
          title="Import from JSON"
          aria-label="Import graph from JSON file"
        >
          <Upload className="w-4 h-4" />
        </button>
        
        <div className="mac-divider w-px h-5 mx-1" />
        
        <button
          className="mac-button-primary flex items-center justify-center gap-1.5 min-w-[80px]"
          disabled={isSaving || !onSave}
          onClick={handleSave}
          title={`Save (${modKey}+S)`}
          aria-label="Save current work"
          aria-keyshortcuts={`${modKey}+S`}
        >
          {isSaving ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>保存</span>
            </>
          ) : (
            <>
              <Save className="h-3.5 w-3.5" />
              <span>保存</span>
            </>
          )}
        </button>
      </div>
      
      {/* 右侧：调试器和主题切换 */}
      <div className="flex items-center gap-1">
        <button 
          className={`mac-button px-3 ${showDebugger ? 'bg-primary/10' : ''}`}
          onClick={onToggleDebugger}
          title="Toggle Debugger Panel"
          aria-label="Toggle debugger panel"
        >
          <Bug className="w-4 h-4" />
        </button>
        <div className="mac-divider w-px h-5 mx-1" />
        <button 
          className="mac-button px-3"
          onClick={toggleTheme}
          title={theme === 'light' ? 'Dark Mode' : 'Light Mode'}
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </button>
      </div>
    </div>
  )
}

