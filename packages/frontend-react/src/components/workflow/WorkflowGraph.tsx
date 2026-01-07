import { useMemo } from 'react'
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type Connection,
  type Edge,
  type EdgeChange,
  type EdgeOptions,
  type FitViewOptions,
  type Node,
  type NodeChange,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
  type OnSelectionChangeParams,
  type ReactFlowInstance,
  SelectionMode,
} from 'reactflow'

type WorkflowGraphProps = {
  nodes: Node[]
  edges: Edge[]
  nodeTypes: Record<string, unknown>
  className?: string
  onNodesChange?: OnNodesChange
  onEdgesChange?: OnEdgesChange
  onConnect?: OnConnect
  onNodeClick?: (event: React.MouseEvent, node: Node) => void
  onSelectionChange?: (selection: OnSelectionChangeParams) => void
  onNodeContextMenu?: (event: React.MouseEvent, node: Node) => void
  onSelectionContextMenu?: (event: React.MouseEvent, nodes: Node[]) => void
  onPaneContextMenu?: (event: React.MouseEvent) => void
  onEdgeContextMenu?: (event: React.MouseEvent, edge: Edge) => void
  onNodeDragStart?: (event: React.MouseEvent, node: Node) => void
  onNodeDragStop?: (event: React.MouseEvent, node: Node) => void
  onSelectionDragStart?: (event: React.MouseEvent) => void
  onSelectionDragStop?: (event: React.MouseEvent) => void
  onInit?: (instance: ReactFlowInstance) => void
  onDrop?: (event: React.DragEvent<HTMLDivElement>) => void
  onDragOver?: (event: React.DragEvent<HTMLDivElement>) => void
  isValidConnection?: (connection: Connection) => boolean
  nodesDraggable?: boolean
  nodesConnectable?: boolean
  elementsSelectable?: boolean
  panOnDrag?: boolean | number[]
  panOnScroll?: boolean
  selectionOnDrag?: boolean
  selectionMode?: SelectionMode
  fitView?: boolean
  fitViewOptions?: FitViewOptions
  defaultEdgeOptions?: EdgeOptions
  showMiniMap?: boolean
  miniMapNodeColor?: (node: Node) => string
  showControls?: boolean
  backgroundVariant?: BackgroundVariant
  backgroundGap?: number
  backgroundSize?: number
  backgroundColor?: string
}

export function WorkflowGraph({
  nodes,
  edges,
  nodeTypes,
  className,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onSelectionChange,
  onNodeContextMenu,
  onSelectionContextMenu,
  onPaneContextMenu,
  onEdgeContextMenu,
  onNodeDragStart,
  onNodeDragStop,
  onSelectionDragStart,
  onSelectionDragStop,
  onInit,
  onDrop,
  onDragOver,
  isValidConnection,
  nodesDraggable,
  nodesConnectable,
  elementsSelectable,
  panOnDrag,
  panOnScroll,
  selectionOnDrag,
  selectionMode,
  fitView,
  fitViewOptions,
  defaultEdgeOptions,
  showMiniMap = false,
  miniMapNodeColor,
  showControls = true,
  backgroundVariant = BackgroundVariant.Dots,
  backgroundGap = 20,
  backgroundSize = 1,
  backgroundColor = '#334155',
}: WorkflowGraphProps) {
  const stableNodeTypes = useMemo(() => nodeTypes, [])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={stableNodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={onNodeClick}
      onSelectionChange={onSelectionChange}
      onNodeContextMenu={onNodeContextMenu}
      onSelectionContextMenu={onSelectionContextMenu}
      onPaneContextMenu={onPaneContextMenu}
      onEdgeContextMenu={onEdgeContextMenu}
      onNodeDragStart={onNodeDragStart}
      onNodeDragStop={onNodeDragStop}
      onSelectionDragStart={onSelectionDragStart}
      onSelectionDragStop={onSelectionDragStop}
      onInit={onInit}
      onDrop={onDrop}
      onDragOver={onDragOver}
      isValidConnection={isValidConnection}
      nodesDraggable={nodesDraggable}
      nodesConnectable={nodesConnectable}
      elementsSelectable={elementsSelectable}
      panOnDrag={panOnDrag}
      panOnScroll={panOnScroll}
      selectionOnDrag={selectionOnDrag}
      selectionMode={selectionMode}
      fitView={fitView}
      fitViewOptions={fitViewOptions}
      defaultEdgeOptions={defaultEdgeOptions}
      className={className}
    >
      <Background
        variant={backgroundVariant}
        gap={backgroundGap}
        size={backgroundSize}
        color={backgroundColor}
        className="bg-slate-950"
      />
      {showControls && (
        <Controls
          className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl overflow-hidden"
          showInteractive={false}
        />
      )}
      {showMiniMap && (
        <MiniMap
          className="bg-slate-900 border border-slate-800 rounded-lg shadow-xl"
          nodeColor={miniMapNodeColor}
          maskColor="rgba(15, 23, 42, 0.8)"
        />
      )}
    </ReactFlow>
  )
}
