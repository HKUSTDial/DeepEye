import { useState, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Database,
  Code2,
  BarChart3,
  FileText,
  ChevronDown,
  ChevronRight,
  Plus,
  Workflow as WorkflowIcon,
  Trash2,
} from 'lucide-react'
import type { Workflow } from '../../types'
import { useWorkflowStore } from '../../stores/workflow'
import { Modal } from '../ui/Modal'

const nodeIcons: Record<string, any> = {
  'datasource.read': Database,
  'sql.execute': Code2,
  'stats.summary': FileText,
  'viz.bar': BarChart3,
}

interface WorkflowSidebarProps {
  workflows: Workflow[]
  nodeTypes: Record<string, { label: string }>
  onLoadWorkflow: (wf: Workflow) => void
  onDeleteWorkflow: (wf: Workflow) => void
  onAddNode: (type: string) => void
}

export function WorkflowSidebar({
  workflows,
  nodeTypes,
  onLoadWorkflow,
  onDeleteWorkflow,
  onAddNode,
}: WorkflowSidebarProps) {
  const [workflowsExpanded, setWorkflowsExpanded] = useState(true)
  const [nodesExpanded, setNodesExpanded] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<Workflow | null>(null)
  const workflowId = useWorkflowStore((state) => state.workflowId)
  const handleDragStart = (event: DragEvent<HTMLButtonElement>, type: string) => {
    event.dataTransfer.setData('application/reactflow', type)
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col overflow-hidden"
    >
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center gap-2 text-white">
          <WorkflowIcon className="w-5 h-5 text-blue-400" />
          <h2 className="font-semibold text-lg">Workflows</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {/* Workflows List */}
        <div className="p-3 border-b border-slate-800">
          <button
            onClick={() => setWorkflowsExpanded(!workflowsExpanded)}
            className="flex items-center justify-between w-full px-2 py-1.5 text-sm font-medium 
              text-slate-300 hover:text-white transition-colors"
          >
            <span className="uppercase tracking-wider text-xs">My Workflows</span>
            {workflowsExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          <AnimatePresence>
            {workflowsExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-2 space-y-1 overflow-hidden"
              >
                {workflows.length === 0 ? (
                  <div className="px-2 py-3 text-xs text-slate-500 text-center">No workflows yet</div>
                ) : (
                  workflows.map((wf) => (
                    <motion.div
                      key={wf.id}
                      whileHover={{ x: 4 }}
                      whileTap={{ scale: 0.98 }}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all 
                        ${
                          workflowId === wf.id
                            ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                            : 'text-slate-300 hover:bg-slate-800 border border-transparent'
                        }`}
                    >
                      <button
                        type="button"
                        onClick={() => onLoadWorkflow(wf)}
                        className="flex-1 min-w-0 text-left"
                      >
                        <div className="font-medium truncate">{wf.name}</div>
                        {wf.description && (
                          <div className="text-xs text-slate-500 truncate mt-0.5">{wf.description}</div>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          setDeleteTarget(wf)
                        }}
                        className="p-1 rounded-md text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 transition"
                        aria-label={`Delete workflow ${wf.name}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </motion.div>
                  ))
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Node Palette */}
        <div className="p-3">
          <button
            onClick={() => setNodesExpanded(!nodesExpanded)}
            className="flex items-center justify-between w-full px-2 py-1.5 text-sm font-medium 
              text-slate-300 hover:text-white transition-colors"
          >
            <span className="uppercase tracking-wider text-xs">Add Node</span>
            {nodesExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          <AnimatePresence>
            {nodesExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-2 space-y-1 overflow-hidden"
              >
                {Object.entries(nodeTypes).map(([type, def]) => {
                  const Icon = nodeIcons[type] || Plus
                  return (
                    <motion.button
                      key={type}
                      whileHover={{ x: 4, scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => onAddNode(type)}
                      draggable
                      onDragStart={(event) => handleDragStart(event, type)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm 
                        text-slate-300 hover:bg-slate-800 hover:text-white border border-slate-800 
                        hover:border-slate-700 transition-all group"
                    >
                      <Icon className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
                      <span className="flex-1 text-left">{def.label}</span>
                      <Plus className="w-3 h-3 text-slate-600 group-hover:text-slate-400 transition-colors" />
                    </motion.button>
                  )
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      <Modal
        open={!!deleteTarget}
        title="Delete workflow?"
        description={
          deleteTarget
            ? `This will permanently delete "${deleteTarget.name}" and its runs.`
            : undefined
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) {
            onDeleteWorkflow(deleteTarget)
          }
          setDeleteTarget(null)
        }}
      />
    </motion.aside>
  )
}

