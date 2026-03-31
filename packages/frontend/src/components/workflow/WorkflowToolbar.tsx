import { useCallback, useState } from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { Save, Play, Undo2, Redo2, Download } from 'lucide-react'
import type { Edge, Node } from 'reactflow'
import { useWorkflowStore } from '../../stores/workflow'
import { useShallow } from 'zustand/react/shallow'
import { useWorkflowNodesStore, type NodeDef } from '../../stores/workflowNodes'
import { useLocale } from '../../locale'

interface WorkflowToolbarProps {
  onSave: () => void
  onRun: () => void
  onUndo: () => void
  onRedo: () => void
}

type WorkflowCanvasNodeData = {
  type: string
  params?: Record<string, unknown>
}

type WorkflowCanvasNode = Node<WorkflowCanvasNodeData>

const MotionDiv = motion.div as React.ComponentType<HTMLMotionProps<'div'>>
const MotionButton = motion.button as React.ComponentType<HTMLMotionProps<'button'>>

export function WorkflowToolbar({ onSave, onRun, onUndo, onRedo }: WorkflowToolbarProps) {
  const { t } = useLocale()
  const {
    workflowId,
    workflowName,
    canUndo,
    canRedo,
    setWorkflowName,
    nodes,
    edges,
  } = useWorkflowStore(
    useShallow((state) => ({
      workflowId: state.workflowId,
      workflowName: state.workflowName,
      canUndo: state.canUndo,
      canRedo: state.canRedo,
      setWorkflowName: state.setWorkflowName,
      nodes: state.nodes,
      edges: state.edges,
    })),
  )
  const nodeDefs = useWorkflowNodesStore((state) => state.nodeDefs)
  const [isExporting, setIsExporting] = useState(false)

  const exportWorkflow = useCallback(() => {
    if (Object.keys(nodeDefs).length === 0) {
      return
    }
    setIsExporting(true)
    try {
      const definition = toDefinition(nodes, edges, nodeDefs)
      const name = (workflowName || 'workflow').trim() || 'workflow'
      const filename = name.toLowerCase().endsWith('.json') ? name : `${name}.json`
      const json = JSON.stringify(definition, null, 2)
      const blob = new Blob([json], { type: 'application/json;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } finally {
      setIsExporting(false)
    }
  }, [nodes, edges, nodeDefs, workflowName])

  return (
    <MotionDiv
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="workflow-toolbar-floating"
    >
      <div className="workflow-toolbar-inputs">
        <input
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
          className="workflow-toolbar-input workflow-toolbar-input-name"
          placeholder={t('workflow.legacyWorkflowNamePlaceholder')}
        />
      </div>

      <div className="workflow-toolbar-actions">
        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onUndo}
          disabled={!canUndo()}
          className="workflow-toolbar-btn workflow-toolbar-btn-icon"
          title={t('workflow.legacyUndoTitle')}
        >
          <Undo2 className="w-4 h-4" />
        </MotionButton>

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onRedo}
          disabled={!canRedo()}
          className="workflow-toolbar-btn workflow-toolbar-btn-icon"
          title={t('workflow.legacyRedoTitle')}
        >
          <Redo2 className="w-4 h-4" />
        </MotionButton>

        <div className="workflow-toolbar-divider" />

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onSave}
          className="workflow-toolbar-btn primary"
        >
          <Save className="w-4 h-4" />
          {t('common.save')}
        </MotionButton>

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={exportWorkflow}
          disabled={Object.keys(nodeDefs).length === 0 || isExporting}
          className="workflow-toolbar-btn"
        >
          <Download className="w-4 h-4" />
          {isExporting ? t('workflow.exporting') : t('common.export')}
        </MotionButton>

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onRun}
          disabled={!workflowId}
          className="workflow-toolbar-btn success"
        >
          <Play className="w-4 h-4" />
          {t('common.run')}
        </MotionButton>
      </div>
    </MotionDiv>
  )
}

function toDefinition(nodes: WorkflowCanvasNode[], edges: Edge[], nodeDefs: Record<string, NodeDef>) {
  const nodeMap: Record<string, Record<string, unknown>> = {}
  nodes.forEach((node) => {
    const def = nodeDefs[node.data.type]
    if (!def) return
    nodeMap[node.id] = {
      id: node.id,
      type: node.data.type,
      inputs: Object.fromEntries(
        def.inputs.map((p) => [p.id, { schema: p.schema, required: !!p.required, multiple: p.multiple }]),
      ),
      outputs: Object.fromEntries(def.outputs.map((p) => [p.id, { schema: p.schema }])),
      params: node.data.params || {},
      metadata: { position: node.position },
    }
  })

  const edgeMap: Record<string, Record<string, unknown>> = {}
  edges.forEach((edge) => {
    const id = edge.id || `${edge.source}-${edge.sourceHandle}-${edge.target}-${edge.targetHandle}`
    edgeMap[id] = {
      id,
      source: { node_id: edge.source, port_id: edge.sourceHandle || 'rows' },
      target: { node_id: edge.target, port_id: edge.targetHandle || 'rows' },
    }
  })

  return { root: { nodes: nodeMap, edges: edgeMap } }
}
