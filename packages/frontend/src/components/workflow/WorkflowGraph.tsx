import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type Connection,
  type Edge,
  type FitViewOptions,
  type Node,
  type NodeTypes,
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
  nodeTypes: NodeTypes
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
  defaultEdgeOptions?: Partial<Edge>
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
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
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
      style={{ width: '100%', height: '100%' }}
    >
      <Background
        variant={backgroundVariant}
        gap={backgroundGap}
        size={backgroundSize}
        color={backgroundColor}
        className="workflow-canvas-background"
      />
      {showControls && (
        <Controls
          className="workflow-canvas-controls"
          showInteractive={false}
        />
      )}
      {showMiniMap && (
        <MiniMap
          className="workflow-canvas-minimap"
          nodeColor={miniMapNodeColor}
          maskColor="rgba(0, 0, 0, 0.6)"
        />
      )}
    </ReactFlow>
  )
}
