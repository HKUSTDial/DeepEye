import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Settings, PlayCircle, CheckCircle2 } from 'lucide-react'
import type { DataSource, WorkflowRun } from '../../types'
import { datasourceApi } from '../../api/datasource'
import type { Node as ReactFlowNode } from 'reactflow'
import { useShallow } from 'zustand/react/shallow'
import { useWorkflowStore } from '../../stores/workflow'
import type { NodeDef } from '../../stores/workflowNodes'
import { useLocale } from '../../locale'
import { deferEffectWork } from '../../utils/effects'
import { WorkflowInspectorOutputView } from './WorkflowInspectorOutput'
import { WorkflowInspectorParamField } from './WorkflowInspectorParamField'
import {
  asObjectRecord,
  getDatasourceCategoryForNodeType,
  getStatusClass,
  stringifyParams,
  type OutputRecord,
} from './workflowInspectorUtils'

interface WorkflowInspectorProps {
  selectedNodeId: string | null
  nodeDefs: Record<string, NodeDef>
  onUpdateParam: (nodeId: string, key: string, value: string) => void
  nodes?: ReactFlowNode[]
  activeRun?: WorkflowRun | null
  runOutput?: string
}

export function WorkflowInspector({
  selectedNodeId,
  nodeDefs,
  onUpdateParam,
  nodes,
  activeRun,
  runOutput,
}: WorkflowInspectorProps) {
  const { t } = useLocale()
  const { selectedNode, activeRun: storeActiveRun, runOutput: storeRunOutput } = useWorkflowStore(
    useShallow((state) => ({
      selectedNode: selectedNodeId ? state.nodes.find((n) => n.id === selectedNodeId) || null : null,
      activeRun: state.activeRun,
      runOutput: state.runOutput,
    })),
  )

  const resolvedSelectedNode =
    nodes && selectedNodeId ? nodes.find((node) => node.id === selectedNodeId) || null : selectedNode
  const resolvedActiveRun = activeRun ?? storeActiveRun
  const resolvedRunOutput = runOutput ?? storeRunOutput

  const nodeDef = resolvedSelectedNode ? nodeDefs[resolvedSelectedNode.data.type] : null

  // 本地状态缓冲参数值，避免每次输入都触发 store 更新导致重新渲染
  const [localParams, setLocalParams] = useState<Record<string, string>>({})
  const [editingParam, setEditingParam] = useState<string | null>(null)
  const [datasources, setDatasources] = useState<DataSource[]>([])
  const [isLoadingDatasources, setIsLoadingDatasources] = useState(false)
  const [datasourceError, setDatasourceError] = useState<string | null>(null)

  const selectedNodeParams = useMemo(
    () => (resolvedSelectedNode?.data.params as Record<string, unknown> | undefined) || {},
    [resolvedSelectedNode],
  )
  const hasDatasourceParam = Object.prototype.hasOwnProperty.call(selectedNodeParams, 'datasource_id')
  const datasourceCategory = getDatasourceCategoryForNodeType(resolvedSelectedNode?.data.type)

  const filteredDatasources = useMemo(
    () =>
      datasourceCategory
        ? datasources.filter((datasource) => datasource.category === datasourceCategory)
        : datasources,
    [datasourceCategory, datasources],
  )

  const selectedNodeRunDetails = useMemo(() => {
    if (!resolvedSelectedNode) {
      return null
    }
    const result = asObjectRecord(resolvedActiveRun?.result)
    if (!result) {
      return null
    }

    const directOutputs = asObjectRecord(result.outputs)
    const directNodeOutput = directOutputs ? asObjectRecord(directOutputs[resolvedSelectedNode.id]) : null
    if (directNodeOutput) {
      return {
        status: typeof directNodeOutput.status === 'string' ? directNodeOutput.status : null,
        output: directNodeOutput,
        raw: JSON.stringify(directNodeOutput, null, 2),
      }
    }

    const runs = asObjectRecord(result.runs)
    const nodeRun = runs ? asObjectRecord(runs[resolvedSelectedNode.id]) : null
    if (!nodeRun) {
      return null
    }

    const nodeOutputs = asObjectRecord(nodeRun.outputs) ?? {}
    const enrichedOutput: OutputRecord = { ...nodeOutputs }

    if (typeof nodeRun.error === 'string' && !('error' in enrichedOutput)) {
      enrichedOutput.error = nodeRun.error
    }
    if (typeof nodeRun.status === 'string' && !('status' in enrichedOutput)) {
      enrichedOutput.status = nodeRun.status
    }

    return {
      status: typeof nodeRun.status === 'string' ? nodeRun.status : null,
      output: enrichedOutput,
      raw: JSON.stringify(nodeRun, null, 2),
    }
  }, [resolvedActiveRun, resolvedSelectedNode])

  const displayRunStatus = selectedNodeRunDetails?.status ?? resolvedActiveRun?.status ?? ''
  const displayRunStatusLabel =
    displayRunStatus === 'running'
      ? t('common.running')
      : displayRunStatus === 'completed' || displayRunStatus === 'success'
        ? t('common.completed')
        : displayRunStatus === 'failed' || displayRunStatus === 'error'
          ? t('common.failed')
          : displayRunStatus

  // 当选中的节点改变时，重置本地参数状态
  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      if (resolvedSelectedNode) {
        const params = (resolvedSelectedNode.data.params as Record<string, unknown> | undefined) || {}
        setLocalParams(stringifyParams(params))
      } else {
        setLocalParams({})
      }
      setEditingParam(null)
    }, 0)
    return () => window.clearTimeout(timeoutId)
  }, [resolvedSelectedNode])

  const loadDatasources = useCallback(async () => {
    if (isLoadingDatasources) return
    setIsLoadingDatasources(true)
    setDatasourceError(null)
    try {
      const list = await datasourceApi.list()
      setDatasources(list)
    } catch (error) {
      setDatasourceError(error instanceof Error ? error.message : 'Failed to load datasources.')
    } finally {
      setIsLoadingDatasources(false)
    }
  }, [isLoadingDatasources])

  useEffect(() => {
    if (!hasDatasourceParam || datasources.length > 0 || datasourceError || isLoadingDatasources) {
      return
    }
    return deferEffectWork(() => {
      void loadDatasources()
    })
  }, [hasDatasourceParam, datasources.length, datasourceError, isLoadingDatasources, loadDatasources])

  // 处理参数更新
  const handleParamChange = useCallback((key: string, value: string) => {
    setLocalParams((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleParamFocus = useCallback(
    (key: string) => {
      setEditingParam(key)
      setLocalParams((prev) => ({
        ...prev,
        [key]: String(selectedNodeParams[key] ?? ''),
      }))
    },
    [selectedNodeParams],
  )

  const handleParamBlur = useCallback(
    (key: string) => {
      if (!resolvedSelectedNode) return
      const value = localParams[key] ?? ''
      onUpdateParam(resolvedSelectedNode.id, key, value)
      setEditingParam(null)
    },
    [resolvedSelectedNode, localParams, onUpdateParam],
  )

  const handleDatasourceSelect = useCallback(
    (key: string, value: string) => {
      if (!resolvedSelectedNode) return
      setLocalParams((prev) => ({ ...prev, [key]: value }))
      onUpdateParam(resolvedSelectedNode.id, key, value)
      setEditingParam(null)
    },
    [resolvedSelectedNode, onUpdateParam],
  )

  return (
    <motion.aside
      initial={{ x: 20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="workflow-inspector"
    >
      <div className="workflow-inspector-header">
        <div className="workflow-inspector-title-wrapper">
          <Settings className="workflow-inspector-icon" />
          <h3 className="workflow-inspector-title">Inspector</h3>
        </div>
      </div>

      <div className="workflow-inspector-content">
        {resolvedSelectedNode ? (
          <>
            {/* Node Info */}
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="workflow-inspector-node-info"
            >
              <div className="workflow-inspector-node-name">{resolvedSelectedNode.data.label}</div>
              {nodeDef?.description && (
                <div className="workflow-inspector-node-desc">{nodeDef.description}</div>
              )}
            </motion.div>

            {/* Parameters */}
            <div className="workflow-inspector-section">
              <h4 className="workflow-inspector-section-title">Parameters</h4>
              {Object.keys((resolvedSelectedNode.data.params as Record<string, unknown>) || {}).length === 0 ? (
                <div className="workflow-inspector-empty">No parameters</div>
              ) : (
                Object.keys((resolvedSelectedNode.data.params as Record<string, unknown>) || {}).map((key) => {
                  const paramDef = nodeDef?.params?.[key]
                  const displayValue =
                    editingParam === key ? (localParams[key] ?? '') : String(selectedNodeParams[key] ?? '')

                  return (
                    <WorkflowInspectorParamField
                      key={`${resolvedSelectedNode.id}-${key}`}
                      fieldKey={key}
                      nodeType={resolvedSelectedNode.data.type}
                      paramDef={paramDef}
                      displayValue={displayValue}
                      datasourceCategory={datasourceCategory}
                      filteredDatasources={filteredDatasources}
                      isLoadingDatasources={isLoadingDatasources}
                      datasourceError={datasourceError}
                      onRefreshDatasources={() => {
                        void loadDatasources()
                      }}
                      onStartEditing={handleParamFocus}
                      onChange={handleParamChange}
                      onBlur={handleParamBlur}
                      onDatasourceSelect={handleDatasourceSelect}
                    />
                  )
                })
              )}
            </div>
          </>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="workflow-inspector-placeholder"
          >
            <Settings className="workflow-inspector-placeholder-icon" />
            <p className="workflow-inspector-placeholder-text">Select a node to review parameters and run output</p>
          </motion.div>
        )}

        {/* Run Status */}
        {resolvedActiveRun && (
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="workflow-inspector-run-section"
          >
            <h4 className="workflow-inspector-section-title workflow-inspector-section-title--icon">
              <PlayCircle className="w-4 h-4" />
              {t('workflowInspector.runStatus')}
            </h4>

            <div className="workflow-inspector-run-info">
              <div className="workflow-inspector-run-row">
                <span className="workflow-inspector-run-label">{resolvedSelectedNode ? t('workflowInspector.nodeStatus') : t('workflowInspector.status')}</span>
                <span className={`workflow-inspector-run-badge ${getStatusClass(displayRunStatus)}`}>
                  {displayRunStatusLabel}
                </span>
              </div>

              {resolvedActiveRun.created_at && (
                <div className="workflow-inspector-run-row">
                  <span className="workflow-inspector-run-label">{t('workflowInspector.started')}</span>
                  <span className="workflow-inspector-run-value">
                    {new Date(resolvedActiveRun.created_at).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>

            {resolvedSelectedNode ? (
              <div className="workflow-inspector-output">
                <div className="workflow-inspector-output-header">
                  <CheckCircle2 className="w-3 h-3" />
                  {t('workflowInspector.nodeOutput')}
                </div>
                {selectedNodeRunDetails ? (
                  <WorkflowInspectorOutputView
                    output={selectedNodeRunDetails.output}
                    rawOutput={selectedNodeRunDetails.raw}
                  />
                ) : (
                  <div className="workflow-inspector-output-empty">
                    {t('workflowInspector.noExecutionRecord')}
                  </div>
                )}
              </div>
            ) : resolvedRunOutput ? (
              <div className="workflow-inspector-output">
                <div className="workflow-inspector-output-header">
                  <CheckCircle2 className="w-3 h-3" />
                  {t('workflowInspector.workflowOutput')}
                </div>
                <div className="workflow-inspector-output-empty">
                  {t('workflowInspector.selectNodeForOutput')}
                </div>
                <details className="workflow-inspector-output-raw">
                  <summary>{t('workflowInspector.rawJson')}</summary>
                  <pre className="workflow-inspector-output-content">{resolvedRunOutput}</pre>
                </details>
              </div>
            ) : null}
          </motion.div>
        )}
      </div>
    </motion.aside>
  )
}
