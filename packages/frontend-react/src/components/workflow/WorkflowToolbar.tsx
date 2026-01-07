import { useCallback, useState } from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { Save, Play, Undo2, Redo2, FileText, Download } from 'lucide-react'
import type { Edge, Node } from 'reactflow'
import { useWorkflowStore } from '../../stores/workflow'
import { useShallow } from 'zustand/react/shallow'
import { useWorkflowNodesStore, type NodeDef } from '../../stores/workflowNodes'

interface WorkflowToolbarProps {
  onSave: () => void
  onRun: () => void
  onUndo: () => void
  onRedo: () => void
}

const MotionDiv = motion.div as React.ComponentType<HTMLMotionProps<'div'>>
const MotionButton = motion.button as React.ComponentType<HTMLMotionProps<'button'>>
const MotionSpan = motion.span as React.ComponentType<HTMLMotionProps<'span'>>

export function WorkflowToolbar({ onSave, onRun, onUndo, onRedo }: WorkflowToolbarProps) {
  const {
    workflowId,
    workflowName,
    description,
    isDirty,
    status,
    canUndo,
    canRedo,
    setWorkflowName,
    setDescription,
    nodes,
    edges,
  } = useWorkflowStore(
    useShallow((state) => ({
      workflowId: state.workflowId,
      workflowName: state.workflowName,
      description: state.description,
      isDirty: state.isDirty,
      status: state.status,
      canUndo: state.canUndo,
      canRedo: state.canRedo,
      setWorkflowName: state.setWorkflowName,
      setDescription: state.setDescription,
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
      className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between gap-3 
        bg-slate-900/90 backdrop-blur-xl border border-white/10 rounded-xl p-3 shadow-2xl"
    >
      <div className="flex items-center gap-2 flex-1">
        <FileText className="w-5 h-5 text-slate-400" />
        <input
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
          className="flex-1 max-w-xs px-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg 
            text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 
            focus:ring-2 focus:ring-blue-500/20 transition-all"
          placeholder="Workflow name"
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="flex-1 max-w-md px-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg 
            text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 
            focus:ring-2 focus:ring-blue-500/20 transition-all"
          placeholder="Description"
        />
      </div>

      <div className="flex items-center gap-2">
        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onUndo}
          disabled={!canUndo()}
          className="p-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed 
            border border-slate-700 rounded-lg text-slate-300 transition-colors"
          title="Undo (Ctrl+Z)"
        >
          <Undo2 className="w-4 h-4" />
        </MotionButton>

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onRedo}
          disabled={!canRedo()}
          className="p-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed 
            border border-slate-700 rounded-lg text-slate-300 transition-colors"
          title="Redo (Ctrl+Shift+Z)"
        >
          <Redo2 className="w-4 h-4" />
        </MotionButton>

        <div className="w-px h-6 bg-slate-700" />

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onSave}
          className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 
            rounded-lg text-white text-sm font-medium transition-colors shadow-lg shadow-blue-500/20"
        >
          <Save className="w-4 h-4" />
          Save
        </MotionButton>

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={exportWorkflow}
          disabled={Object.keys(nodeDefs).length === 0 || isExporting}
          className="flex items-center gap-2 px-4 py-1.5 bg-slate-800 hover:bg-slate-700 
            disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-white text-sm 
            font-medium transition-colors"
        >
          <Download className="w-4 h-4" />
          {isExporting ? 'Exporting...' : 'Export'}
        </MotionButton>

        <MotionButton
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onRun}
          disabled={!workflowId}
          className="flex items-center gap-2 px-4 py-1.5 bg-green-600 hover:bg-green-700 
            disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-white text-sm 
            font-medium transition-colors shadow-lg shadow-green-500/20"
        >
          <Play className="w-4 h-4" />
          Run
        </MotionButton>

        {isDirty && (
          <MotionSpan
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="px-2 py-1 bg-amber-500/20 border border-amber-500/30 rounded-md 
              text-xs text-amber-400 font-medium"
          >
            Unsaved
          </MotionSpan>
        )}

        {status && (
          <MotionSpan
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="px-2 py-1 bg-slate-800/80 border border-slate-700 rounded-md 
              text-xs text-slate-300"
          >
            {status}
          </MotionSpan>
        )}
      </div>
    </MotionDiv>
  )
}

function toDefinition(nodes: Node[], edges: Edge[], nodeDefs: Record<string, NodeDef>) {
  const nodeMap: Record<string, any> = {}
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

  const edgeMap: Record<string, any> = {}
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
