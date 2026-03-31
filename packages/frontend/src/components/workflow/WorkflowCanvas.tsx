import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react'
import {
  addEdge,
  useEdgesState,
  useNodesState,
  SelectionMode,
  type Connection,
  type NodeChange,
  type EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  BackgroundVariant,
  type ReactFlowInstance,
} from 'reactflow'
import { motion } from 'framer-motion'
import { useWorkflowStore } from '../../stores/workflow'
import { useLocale } from '../../locale'
import WorkflowNode from './WorkflowNode'
import { useShallow } from 'zustand/react/shallow'
import type { NodeDef } from '../../stores/workflowNodes'
import { WorkflowGraph } from './WorkflowGraph'

const NODE_TYPES = { workflowNode: WorkflowNode }

type ContextMenuState =
  | {
      type: 'node'
      x: number
      y: number
      nodeId: string
    }
  | {
      type: 'edge'
      x: number
      y: number
      edgeId: string
    }
  | {
      type: 'selection'
      x: number
      y: number
      nodeIds: string[]
    }
  | {
      type: 'canvas'
      x: number
      y: number
      position: { x: number; y: number }
    }

interface WorkflowCanvasProps {
  onSave: () => void
  nodeDefs: Record<string, NodeDef>
}

export function WorkflowCanvas({ onSave, nodeDefs }: WorkflowCanvasProps) {
  const { t } = useLocale()
  const { nodes, edges, setEdges, addToHistory, setSelectedNodeId, setNodes } = useWorkflowStore(
    useShallow((state) => ({
      nodes: state.nodes,
      edges: state.edges,
      setEdges: state.setEdges,
      addToHistory: state.addToHistory,
      setSelectedNodeId: state.setSelectedNodeId,
      setNodes: state.setNodes,
    })),
  )
  const reactFlowRef = useRef<ReactFlowInstance | null>(null)
  const draggingRef = useRef(false)
  const localNodesRef = useRef(nodes)
  const [localNodes, setLocalNodes] = useNodesState(nodes)
  const [localEdges, setLocalEdges] = useEdgesState(edges)
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)
  const canvasRef = useRef<HTMLDivElement | null>(null)
  const nodeTypes = useMemo(() => NODE_TYPES, [])

  useEffect(() => {
    if (!draggingRef.current) {
      setLocalNodes(nodes)
    }
  }, [nodes, setLocalNodes])

  useEffect(() => {
    setLocalEdges(edges)
  }, [edges, setLocalEdges])

  useEffect(() => {
    localNodesRef.current = localNodes
  }, [localNodes])

  const closeContextMenu = useCallback(() => setContextMenu(null), [])

  const updateSelection = useCallback((ids: string[]) => {
    const state = useWorkflowStore.getState()
    const isSameLength = state.selectedNodeIds.length === ids.length
    const isSame =
      isSameLength && state.selectedNodeIds.every((value, index) => value === ids[index])
    if (!isSame) {
      state.setSelectedNodeIds(ids)
    }
    if (ids.length === 1) {
      if (state.selectedNodeId !== ids[0]) {
        state.setSelectedNodeId(ids[0])
      }
    } else if (state.selectedNodeId !== null) {
      state.setSelectedNodeId(null)
    }
  }, [])


  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => {
        const nextEdges = addEdge(connection, eds)
        addToHistory(useWorkflowStore.getState().nodes, nextEdges)
        return nextEdges
      })
    },
    [setEdges, addToHistory],
  )

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const nextNodes = applyNodeChanges(changes, localNodes)
      setLocalNodes(nextNodes)
      const hasRemove = changes.some((c) => c.type === 'remove')
      if (hasRemove) {
        setNodes(nextNodes)
        addToHistory(nextNodes, useWorkflowStore.getState().edges)
      }
    },
    [localNodes, setLocalNodes, setNodes, addToHistory],
  )

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const nextEdges = applyEdgeChanges(changes, localEdges)
      setLocalEdges(nextEdges)
      setEdges(nextEdges)
      const hasRemove = changes.some((c) => c.type === 'remove')
      if (hasRemove) {
        addToHistory(useWorkflowStore.getState().nodes, nextEdges)
      }
    },
    [localEdges, setLocalEdges, setEdges, addToHistory],
  )

  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const getMenuPosition = useCallback((event: React.MouseEvent) => {
    const bounds = canvasRef.current?.getBoundingClientRect()
    const x = bounds ? event.clientX - bounds.left : event.clientX
    const y = bounds ? event.clientY - bounds.top : event.clientY
    return { x, y }
  }, [])

  const createNode = useCallback(
    (type: string, position: { x: number; y: number }) => {
      const def = nodeDefs[type]
      if (!def) return

      const id = `${type}-${Date.now()}`
      const newNode = {
        id,
        type: 'workflowNode',
        position,
        data: {
          type,
          label: def.label,
          inputs: def.inputs.map((p) => ({ id: p.id, label: p.label })),
          outputs: def.outputs.map((p) => ({ id: p.id, label: p.label })),
          params: Object.fromEntries(Object.entries(def.params).map(([key, param]) => [key, param.default])),
        },
      }

      const nextNodes = [...localNodesRef.current, newNode]
      setLocalNodes(nextNodes)
      setNodes(nextNodes)
      addToHistory(nextNodes, useWorkflowStore.getState().edges)
      setSelectedNodeId(id)
    },
    [nodeDefs, setLocalNodes, setNodes, addToHistory, setSelectedNodeId],
  )

  const duplicateNodes = useCallback(
    (nodeIds: string[]) => {
      const sourceNodes = localNodesRef.current.filter((node) => nodeIds.includes(node.id))
      if (sourceNodes.length === 0) return

      const clones = sourceNodes.map((node) => ({
        ...node,
        id: `${node.id}-copy-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`,
        position: { x: node.position.x + 24, y: node.position.y + 24 },
        selected: false,
      }))

      const nextNodes = [...localNodesRef.current, ...clones]
      setLocalNodes(nextNodes)
      setNodes(nextNodes)
      addToHistory(nextNodes, useWorkflowStore.getState().edges)
    },
    [setLocalNodes, setNodes, addToHistory],
  )

  const deleteNodes = useCallback(
    (nodeIds: string[]) => {
      if (nodeIds.length === 0) return
      const nextNodes = localNodesRef.current.filter((node) => !nodeIds.includes(node.id))
      const nextEdges = useWorkflowStore
        .getState()
        .edges.filter((edge) => !nodeIds.includes(edge.source) && !nodeIds.includes(edge.target))
      setLocalNodes(nextNodes)
      setLocalEdges(nextEdges)
      setNodes(nextNodes)
      setEdges(nextEdges)
      addToHistory(nextNodes, nextEdges)
      setSelectedNodeId(null)
    },
    [setLocalNodes, setLocalEdges, setNodes, setEdges, addToHistory, setSelectedNodeId],
  )

  const deleteEdges = useCallback(
    (edgeIds: string[]) => {
      if (edgeIds.length === 0) return
      const nextEdges = useWorkflowStore.getState().edges.filter((edge) => !edgeIds.includes(edge.id))
      setLocalEdges(nextEdges)
      setEdges(nextEdges)
      addToHistory(useWorkflowStore.getState().nodes, nextEdges)
    },
    [setLocalEdges, setEdges, addToHistory],
  )


  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault()
      const type = event.dataTransfer.getData('application/reactflow')
      if (!type) return

      const def = nodeDefs[type]
      if (!def) return

      if (!reactFlowRef.current) return
      const position = reactFlowRef.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })
      const id = `${type}-${Date.now()}`
      const newNode = {
        id,
        type: 'workflowNode',
        position,
        data: {
          type,
          label: def.label,
          inputs: def.inputs.map((p) => ({ id: p.id, label: p.label })),
          outputs: def.outputs.map((p) => ({ id: p.id, label: p.label })),
          params: Object.fromEntries(Object.entries(def.params).map(([key, param]) => [key, param.default])),
        },
      }

      const nextNodes = [...localNodesRef.current, newNode]
      setLocalNodes(nextNodes)
      setNodes(nextNodes)
      addToHistory(nextNodes, useWorkflowStore.getState().edges)
      setSelectedNodeId(id)
    },
    [nodeDefs, setLocalNodes, setNodes, addToHistory, setSelectedNodeId],
  )

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="workflow-canvas-container"
      ref={canvasRef}
      onClick={closeContextMenu}
    >
      <WorkflowGraph
        nodes={localNodes}
        edges={localEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node) => setSelectedNodeId(node.id)}
        isValidConnection={(connection) => {
          return !!connection.source && !!connection.target && connection.source !== connection.target
        }}
        onNodeContextMenu={(event, node) => {
          event.preventDefault()
          setSelectedNodeId(node.id)
          const { x, y } = getMenuPosition(event)
          setContextMenu({ type: 'node', x, y, nodeId: node.id })
        }}
        onSelectionChange={(selection) => {
          updateSelection(selection.nodes.map((node) => node.id))
        }}
        onEdgeContextMenu={(event, edge) => {
          event.preventDefault()
          const { x, y } = getMenuPosition(event)
          setContextMenu({ type: 'edge', x, y, edgeId: edge.id })
        }}
        onSelectionContextMenu={(event, selection) => {
          event.preventDefault()
          const nodeIds = selection.map((node) => node.id)
          const { x, y } = getMenuPosition(event)
          setContextMenu({ type: 'selection', x, y, nodeIds })
        }}
        onPaneContextMenu={(event) => {
          event.preventDefault()
          const { x, y } = getMenuPosition(event)
          if (reactFlowRef.current) {
            const position = reactFlowRef.current.screenToFlowPosition({
              x: event.clientX,
              y: event.clientY,
            })
            setContextMenu({ type: 'canvas', x, y, position })
          }
        }}
        onNodeDragStart={() => {
          draggingRef.current = true
        }}
        onNodeDragStop={() => {
          draggingRef.current = false
          setNodes(localNodesRef.current)
          addToHistory(localNodesRef.current, useWorkflowStore.getState().edges)
        }}
        onSelectionDragStart={() => {
          draggingRef.current = true
        }}
        onSelectionDragStop={() => {
          draggingRef.current = false
          setNodes(localNodesRef.current)
          addToHistory(localNodesRef.current, useWorkflowStore.getState().edges)
        }}
        onInit={(instance) => {
          reactFlowRef.current = instance
        }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodesDraggable={true}
        panOnDrag={[1]}
        selectionOnDrag
        selectionMode={SelectionMode.Partial}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        className="workflow-canvas"
        defaultEdgeOptions={{
          style: { stroke: 'var(--accent)', strokeWidth: 2 },
          animated: true,
        }}
        backgroundVariant={BackgroundVariant.Dots}
        backgroundGap={20}
        backgroundSize={1}
        backgroundColor="var(--main-bg)"
        showMiniMap
        miniMapNodeColor={(node) => {
          switch (node.data.runStatus) {
            case 'running':
              return '#22c55e'
            case 'success':
              return '#3b82f6'
            case 'failed':
              return '#ef4444'
            case 'pending':
              return '#f59e0b'
            default:
              return '#475569'
          }
        }}
      />
      {contextMenu && (
        <div
          className="workflow-context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(event) => event.stopPropagation()}
        >
          <div className="workflow-context-menu-header">
            {contextMenu.type === 'node' && t('workflow.legacyNodeMenu')}
            {contextMenu.type === 'edge' && t('workflow.legacyEdgeMenu')}
            {contextMenu.type === 'selection' &&
              t('workflow.legacySelectionMenu', { count: contextMenu.nodeIds.length })}
            {contextMenu.type === 'canvas' && t('workflow.legacyCanvasMenu')}
          </div>
          <div className="workflow-context-menu-body">
            <button
              className="workflow-context-menu-item"
              onClick={() => {
                onSave()
                closeContextMenu()
              }}
            >
              {t('workflow.legacySaveWorkflow')}
            </button>
            {contextMenu.type === 'node' && (
              <>
                <button
                  className="workflow-context-menu-item"
                  onClick={() => {
                    duplicateNodes([contextMenu.nodeId])
                    closeContextMenu()
                  }}
                >
                  {t('workflow.legacyDuplicate')}
                </button>
                <button
                  className="workflow-context-menu-item danger"
                  onClick={() => {
                    deleteNodes([contextMenu.nodeId])
                    closeContextMenu()
                  }}
                >
                  {t('common.delete')}
                </button>
              </>
            )}
            {contextMenu.type === 'edge' && (
              <button
                className="workflow-context-menu-item danger"
                onClick={() => {
                  deleteEdges([contextMenu.edgeId])
                  closeContextMenu()
                }}
              >
                {t('workflow.legacyDeleteEdge')}
              </button>
            )}
            {contextMenu.type === 'selection' && (
              <>
                <button
                  className="workflow-context-menu-item"
                  onClick={() => {
                    duplicateNodes(contextMenu.nodeIds)
                    closeContextMenu()
                  }}
                >
                  {t('workflow.legacyDuplicateSelection')}
                </button>
                <button
                  className="workflow-context-menu-item danger"
                  onClick={() => {
                    deleteNodes(contextMenu.nodeIds)
                    closeContextMenu()
                  }}
                >
                  {t('workflow.legacyDeleteSelection')}
                </button>
              </>
            )}
            {contextMenu.type === 'canvas' && (
              <>
                {Object.entries(nodeDefs).map(([type, def]) => (
                  <button
                    key={type}
                    className="workflow-context-menu-item"
                    onClick={() => {
                      createNode(type, contextMenu.position)
                      closeContextMenu()
                    }}
                  >
                    {t('workflow.legacyAddNodeLabel', { label: def.label })}
                  </button>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </motion.div>
  )
}
