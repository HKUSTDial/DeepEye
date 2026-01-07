import { useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import 'reactflow/dist/style.css'
import { useShallow } from 'zustand/react/shallow'

import { useWorkflowStore } from '../stores/workflow'
import { useWorkflow } from '../hooks/useWorkflow'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useWorkflowNodesStore } from '../stores/workflowNodes'

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
      className="flex h-screen bg-slate-950 text-white overflow-hidden"
    >
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

