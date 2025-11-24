/**
 * WorkflowEditor - 工作流编辑器
 * 
 * 原 App.tsx 的编辑器部分
 */

import { ThemeProvider } from '@/app/providers/ThemeProvider'
import { NodeLibrary, PropertiesPanel } from '@/features/sidebar'
import { Canvas } from '@/features/canvas'
import { Toolbar } from '@/features/toolbar'
import { ReactFlowProvider } from 'reactflow'
import { useKeyboardShortcuts } from '@/shared/hooks/useKeyboardShortcuts'
import { HistoryDebugger } from '@/shared/components'
import { useState, useEffect } from 'react'
import { useGraphStore, toast } from '@/store'
import { workflowAPI } from '@/shared/api'
import { Loader2 } from 'lucide-react'

interface WorkflowEditorProps {
  workflowId?: string
  onBack: () => void
}

export function WorkflowEditor({ workflowId, onBack }: WorkflowEditorProps) {
  useKeyboardShortcuts()
  const [showDebugger, setShowDebugger] = useState(import.meta.env.DEV)
  const [workflowName, setWorkflowName] = useState('未命名工作流')
  const [isSaving, setIsSaving] = useState(false)
  const [isLoading, setIsLoading] = useState(!!workflowId)

  const { nodes, edges, viewport, setNodes, setEdges, setViewport } = useGraphStore()

  useEffect(() => {
    if (workflowId) {
      loadWorkflow(workflowId)
    }
  }, [workflowId])

  const loadWorkflow = async (id: string) => {
    setIsLoading(true)
    try {
      const workflow = await workflowAPI.get(id)
      setWorkflowName(workflow.name)
      setNodes(workflow.workflow_data.nodes)
      setEdges(workflow.workflow_data.edges)
      setViewport(workflow.workflow_data.viewport)
    } catch (error) {
      console.error('加载工作流失败:', error)
      toast.error('加载工作流失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    if (!workflowId) {
      toast.error('工作流 ID 不存在，无法保存')
      return
    }

    setIsSaving(true)
    try {
      await workflowAPI.update(workflowId, {
        workflow_data: { nodes, edges, viewport },
      })
      toast.success('保存成功！')
    } catch (error) {
      console.error('保存失败:', error)
      toast.error('保存失败')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <ThemeProvider>
      <div className="flex h-screen w-screen flex-col overflow-hidden bg-background text-foreground">
        <Toolbar
          showDebugger={showDebugger}
          onToggleDebugger={() => setShowDebugger(!showDebugger)}
          workflowName={workflowName}
          workflowId={workflowId}
          onBack={onBack}
          onSave={handleSave}
          isSaving={isSaving}
        />

        <ReactFlowProvider>
          <div className="flex flex-1 overflow-hidden">
            <NodeLibrary />
            <Canvas />
            <PropertiesPanel />
          </div>
        </ReactFlowProvider>

        {showDebugger && <HistoryDebugger />}
      </div>
    </ThemeProvider>
  )
}

