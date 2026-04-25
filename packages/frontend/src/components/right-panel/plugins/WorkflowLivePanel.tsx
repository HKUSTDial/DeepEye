import { useMemo, useState, type CSSProperties } from 'react'
import { BackgroundVariant } from 'reactflow'
import 'reactflow/dist/style.css'
import '../../workflow/Workflow.css'
import WorkflowNode from '../../workflow/WorkflowNode'
import { WorkflowGraph } from '../../workflow/WorkflowGraph'
import { WorkflowInspector } from '../../workflow/WorkflowInspector'
import { useTheme } from '../../../hooks/useTheme'
import { WorkflowLiveEmptyState } from './WorkflowLiveEmptyState'
import { WorkflowLiveToolbar } from './WorkflowLiveToolbar'
import { useTransientWorkflowHighlights } from './useTransientWorkflowHighlights'
import { useWorkflowLiveController } from './useWorkflowLiveController'
import { useWorkflowViewportFit } from './useWorkflowViewportFit'
import {
  getWorkflowMiniMapNodeColor,
  hasRenderableWorkflow,
  toFlow,
} from './workflowPanelUtils'

const NODE_TYPES = { workflowNode: WorkflowNode }

export function WorkflowLivePanel({ 
  sessionId, 
  dataSourceIds = [] 
}: { 
  sessionId: string | null,
  dataSourceIds?: string[]
}) {
  const {
    displaySessionId,
    isViewSwitching,
    isLoadingFiles,
    availableDrafts,
    isLoadingFile,
    isSaving,
    isRunning,
    isExporting,
    isStreaming,
    nodeDefs,
    definition,
    validatedNodes,
    validatedEdges,
    nodeStatus,
    runStatus,
    runError,
    error,
    displayFileError,
    activeRun,
    runOutput,
    activeDraftNodes,
    activeDraftEdges,
    activeDraft,
    activeDraftId,
    activeViewState,
    lastUpdated,
    loadWorkflowDraft,
    handleSave,
    handleExport,
    handleRun,
    updateWorkflowNodeParam,
  } = useWorkflowLiveController(sessionId)

  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const [selectedNodeState, setSelectedNodeState] = useState<{
    activeDraftId: string | null
    displaySessionId: string | null
    nodeId: string | null
  }>({ activeDraftId: null, displaySessionId: null, nodeId: null })
  const selectedNodeId =
    selectedNodeState.activeDraftId === activeDraftId && selectedNodeState.displaySessionId === displaySessionId
      ? selectedNodeState.nodeId
      : null

  const activeDraftNodeIds = useMemo(() => Object.keys(activeDraftNodes), [activeDraftNodes])
  const activeDraftEdgeIds = useMemo(() => Object.keys(activeDraftEdges), [activeDraftEdges])
  const { newNodeIds, newEdgeIds } = useTransientWorkflowHighlights(
    activeDraftNodeIds,
    activeDraftEdgeIds,
  )

  const flow = useMemo(() => {
    if (Object.keys(validatedNodes).length > 0 || Object.keys(validatedEdges).length > 0) {
      return toFlow({ root: { nodes: validatedNodes, edges: validatedEdges } }, nodeDefs)
    }
    if (!definition) return { nodes: [], edges: [] }
    if (typeof definition !== 'object' || definition === null) return { nodes: [], edges: [] }
    return toFlow(definition as Record<string, unknown>, nodeDefs)
  }, [definition, validatedNodes, validatedEdges, nodeDefs])

  const flowWithStatus = useMemo(() => {
    if (flow.nodes.length === 0) return flow
    return {
      nodes: flow.nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          runStatus: nodeStatus[node.id]?.status,
          isNew: newNodeIds.has(node.id),
        },
      })),
      edges: flow.edges.map((edge) => ({
        ...edge,
        animated: false,
        className: newEdgeIds.has(edge.id) ? 'workflow-edge--new' : '',
      })),
    }
  }, [flow, nodeStatus, newNodeIds, newEdgeIds])
  const { graphHostRef, handleGraphInit } = useWorkflowViewportFit({
    nodeCount: flowWithStatus.nodes.length,
    edgeCount: flowWithStatus.edges.length,
    displaySessionId,
    activeViewState,
    lastUpdated,
  })

  const nodeTypes = useMemo(() => NODE_TYPES, [])
  const workflowToneStyle = useMemo(
    () =>
      ({
        '--workflow-link': isDark ? '#49b6a6' : '#0f766e',
        '--workflow-link-active': isDark ? '#7ed9ca' : '#115e59',
        '--workflow-link-soft': isDark ? 'rgba(73, 182, 166, 0.18)' : 'rgba(15, 118, 110, 0.16)',
        '--workflow-port-input': isDark ? '#49b6a6' : '#0f766e',
        '--workflow-port-output': isDark ? '#f3b560' : '#c27a1a',
        '--workflow-grid': isDark ? '#29403d' : '#b7cfc8',
      }) as CSSProperties,
    [isDark],
  )

  if (!hasRenderableWorkflow(definition, validatedNodes, validatedEdges)) {
    return (
      <div
        className={`workflow-live-panel workflow-live-panel--${isDark ? 'dark' : 'light'} panel-view`}
        style={workflowToneStyle}
      >
        <WorkflowLiveEmptyState dataSourceCount={dataSourceIds.length} />
      </div>
    )
  }

  return (
    <div
      className={`workflow-live-panel workflow-live-panel--${isDark ? 'dark' : 'light'} panel-view`}
      style={workflowToneStyle}
    >
      <WorkflowLiveToolbar
        sessionId={sessionId}
        availableDrafts={availableDrafts}
        activeDraft={activeDraft}
        activeDraftId={activeDraftId}
        runStatus={runStatus}
        runError={runError}
        error={error}
        displayFileError={displayFileError}
        isViewSwitching={isViewSwitching}
        isLoadingFiles={isLoadingFiles}
        isLoadingFile={isLoadingFile}
        isSaving={isSaving}
        isStreaming={isStreaming}
        isExporting={isExporting}
        isRunning={isRunning}
        hasNodeDefinitions={Object.keys(nodeDefs).length > 0}
        hasFlowNodes={flow.nodes.length > 0}
        onSelectDraft={(draftId) => void loadWorkflowDraft(draftId)}
        onSave={async () => {
          await handleSave(flow.nodes, flow.edges)
        }}
        onExport={(filename) => {
          handleExport(filename, flow.nodes, flow.edges)
        }}
        onRun={async () => {
          await handleRun(flow.nodes, flow.edges)
        }}
      />
      <div className="flex min-h-0 flex-1">
        <div ref={graphHostRef} className="min-w-0 flex-1">
          <WorkflowGraph
            nodes={flowWithStatus.nodes}
            edges={flowWithStatus.edges}
            nodeTypes={nodeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            onNodeClick={(_, node) => setSelectedNodeState({ activeDraftId, displaySessionId, nodeId: node.id })}
            panOnScroll
            fitView
            fitViewOptions={{ padding: 0.22, minZoom: 0.55, maxZoom: 1.08 }}
            onInit={handleGraphInit}
            className="workflow-canvas workflow-canvas--panel"
            defaultEdgeOptions={{
              style: { stroke: 'var(--workflow-link)', strokeWidth: 2.25 },
              animated: false,
            }}
            backgroundVariant={BackgroundVariant.Dots}
            backgroundGap={20}
            backgroundSize={1.1}
            backgroundColor="var(--workflow-grid)"
            showControls
            showMiniMap
            miniMapNodeColor={(node) => getWorkflowMiniMapNodeColor(node.data.runStatus, isDark)}
          />
        </div>
        <WorkflowInspector
          selectedNodeId={selectedNodeId}
          nodeDefs={nodeDefs}
          nodes={flow.nodes}
          activeRun={activeRun}
          runOutput={runOutput}
          onUpdateParam={(nodeId, key, value) => {
            if (!sessionId) return
            updateWorkflowNodeParam(sessionId, nodeId, key, value)
          }}
        />
      </div>
    </div>
  )
}
