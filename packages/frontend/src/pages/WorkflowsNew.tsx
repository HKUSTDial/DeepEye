import { useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import 'reactflow/dist/style.css'
import { useShallow } from 'zustand/react/shallow'

import { useWorkflowStore } from '../stores/workflow'
import { useWorkflow } from '../hooks/useWorkflow'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useWorkflowNodesStore } from '../stores/workflowNodes'
import '../components/workflow/Workflow.css'

import { WorkflowToolbar } from '../components/workflow/WorkflowToolbar'
import { WorkflowSidebar } from '../components/workflow/WorkflowSidebar'
import { WorkflowCanvas } from '../components/workflow/WorkflowCanvas'
import { WorkflowInspector } from '../components/workflow/WorkflowInspector'

export default function WorkflowsNew() {
  const { workflows, selectedNodeId, selectedNodeIds, undo, redo, setSelectedNodeId } = useWorkflowStore(
    useShallow((state) => ({
      workflows: state.workflows,
      selectedNodeId: state.selectedNodeId,
      selectedNodeIds: state.selectedNodeIds,
      undo: state.undo,
      redo: state.redo,
      setSelectedNodeId: state.setSelectedNodeId,
    })),
  )
  const {
    loadWorkflows,
    loadWorkflow,
    saveWorkflow,
    deleteWorkflow,
    runWorkflow,
    addNode,
    deleteNode,
    deleteNodes,
    updateNodeParam,
    cleanup,
    nodeDefs,
  } = useWorkflow()
  const loadNodeDefs = useWorkflowNodesStore((state) => state.loadNodeDefs)

  useEffect(() => {
    loadWorkflows()
    loadNodeDefs()
    return cleanup
  }, [loadWorkflows, loadNodeDefs, cleanup])

  const handleDeleteSelected = useCallback(() => {
    if (selectedNodeIds.length > 0) {
      deleteNodes(selectedNodeIds)
      return
    }
    if (selectedNodeId) {
      deleteNode(selectedNodeId)
    }
  }, [selectedNodeIds, selectedNodeId, deleteNodes, deleteNode])

  useKeyboardShortcuts({
    save: saveWorkflow,
    undo,
    redo,
    delete: handleDeleteSelected,
    escape: () => setSelectedNodeId(null),
  })

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex h-screen overflow-hidden"
      style={{ background: 'var(--main-bg)', color: 'var(--main-text)' }}
    >
      <div className="pointer-events-none absolute left-1/2 top-4 z-20 w-[min(720px,calc(100%-2rem))] -translate-x-1/2 px-4">
        <div className="pointer-events-auto rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 shadow-sm backdrop-blur">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700 dark:text-amber-300">
            Legacy Workflow Editor
          </div>
          <div className="mt-1 text-sm text-[var(--muted-text)]">
            Session workspace is the primary workflow surface. Keep this page for manual debugging or migration only.
          </div>
          <Link to="/" className="mt-3 inline-flex text-sm font-medium text-[var(--accent)] hover:underline">
            Open main workspace
          </Link>
        </div>
      </div>
      <WorkflowSidebar
        workflows={workflows}
        nodeTypes={nodeDefs}
        onLoadWorkflow={loadWorkflow}
        onDeleteWorkflow={(wf) => deleteWorkflow(wf.id)}
        onAddNode={addNode}
      />

      <div className="flex-1 flex flex-col relative">
        <WorkflowToolbar onSave={saveWorkflow} onRun={runWorkflow} onUndo={undo} onRedo={redo} />
        <WorkflowCanvas onSave={saveWorkflow} nodeDefs={nodeDefs} />
      </div>

      <WorkflowInspector
        selectedNodeId={selectedNodeId}
        nodeDefs={nodeDefs}
        onUpdateParam={updateNodeParam}
      />
    </motion.div>
  )
}
