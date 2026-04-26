import { useState, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import {
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
import { useLocale } from '../../locale'
import { Modal } from '../ui/Modal'

const nodeIcons: Record<string, LucideIcon> = {
  'datasource.read': FileText,
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
  const { t } = useLocale()
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
      className="workflow-sidebar"
    >
      <div className="workflow-sidebar-header">
        <div className="workflow-sidebar-title-wrapper">
          <WorkflowIcon className="workflow-sidebar-icon" />
          <h2 className="workflow-sidebar-title">{t('workflow.legacySidebarTitle')}</h2>
        </div>
      </div>

      <div className="workflow-sidebar-content">
        {/* Workflows List */}
        <div className="workflow-sidebar-section">
          <button
            onClick={() => setWorkflowsExpanded(!workflowsExpanded)}
            className="workflow-sidebar-section-toggle"
          >
            <span className="workflow-sidebar-section-title">{t('workflow.legacyMyWorkflows')}</span>
            {workflowsExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          <AnimatePresence>
            {workflowsExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="workflow-sidebar-list"
              >
                {workflows.length === 0 ? (
                  <div className="workflow-sidebar-empty">{t('workflow.legacyNoWorkflows')}</div>
                ) : (
                  workflows.map((wf) => (
                    <motion.div
                      key={wf.id}
                      whileHover={{ x: 4 }}
                      whileTap={{ scale: 0.98 }}
                      className={`workflow-sidebar-item ${workflowId === wf.id ? 'active' : ''}`}
                    >
                      <button
                        type="button"
                        onClick={() => onLoadWorkflow(wf)}
                        className="workflow-sidebar-item-content"
                      >
                        <div className="workflow-sidebar-item-name">{wf.name}</div>
                        {wf.description && (
                          <div className="workflow-sidebar-item-desc">{wf.description}</div>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          setDeleteTarget(wf)
                        }}
                        className="workflow-sidebar-item-delete"
                        aria-label={t('workflow.legacyDeleteWorkflowTitle')}
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
        <div className="workflow-sidebar-section">
          <button
            onClick={() => setNodesExpanded(!nodesExpanded)}
            className="workflow-sidebar-section-toggle"
          >
            <span className="workflow-sidebar-section-title">{t('workflow.legacyAddNode')}</span>
            {nodesExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          <AnimatePresence>
            {nodesExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="workflow-node-palette"
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
                      onDragStartCapture={(event) => handleDragStart(event, type)}
                      className="workflow-node-palette-item"
                    >
                      <Icon className="workflow-node-palette-icon-small" />
                      <span className="workflow-node-palette-name">{def.label}</span>
                      <Plus className="workflow-node-palette-plus" />
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
        title={t('workflow.legacyDeleteWorkflowTitle')}
        description={
          deleteTarget
            ? t('workflow.legacyDeleteWorkflowDescription', { name: deleteTarget.name })
            : undefined
        }
        confirmLabel={t('common.delete')}
        cancelLabel={t('common.cancel')}
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
