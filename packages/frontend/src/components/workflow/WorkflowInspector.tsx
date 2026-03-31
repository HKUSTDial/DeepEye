import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { motion } from 'framer-motion'
import { Settings, AlertCircle, PlayCircle, CheckCircle2 } from 'lucide-react'
import type { DataSource, WorkflowRun } from '../../types'
import { datasourceApi } from '../../api/datasource'
import type { Node as ReactFlowNode } from 'reactflow'
import { useShallow } from 'zustand/react/shallow'
import { useWorkflowStore } from '../../stores/workflow'
import type { NodeDef } from '../../stores/workflowNodes'
import { WorkflowInspectorOutputView } from './WorkflowInspectorOutput'
import {
  asObjectRecord,
  formatDatasourceOptionLabel,
  getDatasourceCategoryForNodeType,
  getDatasourcePlaceholder,
  getEmptyDatasourceMessage,
  getStatusClass,
  isMultilineParam,
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
  const [datasourceMenuOpen, setDatasourceMenuOpen] = useState(false)
  const datasourcePickerRef = useRef<HTMLDivElement | null>(null)

  const selectedNodeParams = (resolvedSelectedNode?.data.params as Record<string, unknown> | undefined) || {}
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

  useEffect(() => {
    setDatasourceMenuOpen(false)
  }, [resolvedSelectedNode?.id])

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
    void loadDatasources()
  }, [hasDatasourceParam, datasources.length, datasourceError, isLoadingDatasources, loadDatasources])

  useEffect(() => {
    if (!datasourceMenuOpen) return

    const onMouseDown = (event: MouseEvent) => {
      if (!datasourcePickerRef.current?.contains(event.target as globalThis.Node)) {
        setDatasourceMenuOpen(false)
      }
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDatasourceMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [datasourceMenuOpen])

  // 处理参数更新
  const handleParamChange = useCallback((key: string, value: string) => {
    setLocalParams((prev) => ({ ...prev, [key]: value }))
  }, [])

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
                  const required = paramDef?.required
                  const displayValue =
                    editingParam === key ? (localParams[key] ?? '') : String(selectedNodeParams[key] ?? '')
                  const isDatasourceIdField = key === 'datasource_id'
                  const isMultilineField = isMultilineParam(resolvedSelectedNode.data.type, key)
                  const selectedDatasource =
                    filteredDatasources.find((datasource) => datasource.id === displayValue) || null
                  const datasourcePlaceholder = getDatasourcePlaceholder(datasourceCategory)
                  const datasourceTriggerLabel = selectedDatasource
                    ? formatDatasourceOptionLabel(selectedDatasource)
                    : displayValue
                      ? 'Current value not in list'
                      : datasourcePlaceholder
                  const datasourceHint = selectedDatasource
                    ? `${selectedDatasource.name} · ${selectedDatasource.category.toUpperCase()} · ${selectedDatasource.id}`
                    : displayValue
                      ? 'Current value is not in the loaded datasource list. You can still paste a valid UUID manually.'
                      : getEmptyDatasourceMessage(datasourceCategory)

                  return (
                    <div key={`${resolvedSelectedNode.id}-${key}`} className="workflow-inspector-field">
                      <label className="workflow-inspector-label">
                        <span className="workflow-inspector-label-text">{key}</span>
                        {required ? (
                          <span className="workflow-inspector-label-required">
                            <AlertCircle className="w-3 h-3" />
                            required
                          </span>
                        ) : (
                          <span className="workflow-inspector-label-optional">optional</span>
                        )}
                      </label>
                      {isDatasourceIdField ? (
                        <div className="workflow-inspector-datasource-picker">
                          <div
                            ref={datasourcePickerRef}
                            className={`workflow-inspector-select-shell ${datasourceMenuOpen ? 'is-open' : ''}`}
                          >
                            <button
                              type="button"
                              className={`workflow-inspector-select-trigger ${datasourceMenuOpen ? 'is-open' : ''}`}
                              onClick={() => {
                                if (!isLoadingDatasources && filteredDatasources.length > 0) {
                                  setDatasourceMenuOpen((current) => !current)
                                }
                              }}
                              aria-haspopup="listbox"
                              aria-expanded={datasourceMenuOpen}
                              disabled={isLoadingDatasources || filteredDatasources.length === 0}
                            >
                              <span className="workflow-inspector-select-trigger-value">
                                {isLoadingDatasources ? 'Loading datasources...' : datasourceTriggerLabel}
                              </span>
                              <span className="workflow-inspector-select-chevron" aria-hidden="true">
                                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                                  <path d="m5.5 7.5 4.5 5 4.5-5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              </span>
                            </button>

                            {datasourceMenuOpen && (
                              <div className="workflow-inspector-select-menu" role="listbox" aria-label="Datasource">
                                {filteredDatasources.map((datasource) => {
                                  const isSelected = datasource.id === displayValue
                                  return (
                                    <button
                                      key={datasource.id}
                                      type="button"
                                      role="option"
                                      aria-selected={isSelected}
                                      className={`workflow-inspector-select-option ${isSelected ? 'is-selected' : ''}`}
                                      onClick={() => {
                                        handleDatasourceSelect(key, datasource.id)
                                        setDatasourceMenuOpen(false)
                                      }}
                                    >
                                      <span className="workflow-inspector-select-option-copy">
                                        <span className="workflow-inspector-select-option-label">
                                          {datasource.name}
                                        </span>
                                        <span className="workflow-inspector-select-option-meta">
                                          {datasource.category === 'file' ? 'FILE' : 'DATABASE'} · {datasource.id.slice(0, 8)}
                                        </span>
                                      </span>
                                      {isSelected && (
                                        <span className="workflow-inspector-select-option-check" aria-hidden="true">
                                          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
                                            <path d="m4.5 10 3.2 3.2L15.5 5.8" strokeLinecap="round" strokeLinejoin="round" />
                                          </svg>
                                        </span>
                                      )}
                                    </button>
                                  )
                                })}
                              </div>
                            )}
                          </div>
                          <input
                            type="text"
                            value={displayValue}
                            placeholder={paramDef?.placeholder}
                            onFocus={() => {
                              setEditingParam(key)
                              setLocalParams((prev) => ({
                                ...prev,
                                [key]: String(selectedNodeParams[key] ?? ''),
                              }))
                            }}
                            onChange={(e) => handleParamChange(key, e.target.value)}
                            onBlur={() => handleParamBlur(key)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.currentTarget.blur()
                              }
                            }}
                            className="workflow-inspector-input workflow-inspector-input--mono"
                          />
                          <div className="workflow-inspector-datasource-row">
                            <div className={`workflow-inspector-field-hint ${datasourceError ? 'is-error' : ''}`}>
                              {datasourceError || datasourceHint}
                            </div>
                            <button
                              type="button"
                              onClick={() => void loadDatasources()}
                              disabled={isLoadingDatasources}
                              className="workflow-inspector-field-action"
                            >
                              {isLoadingDatasources ? 'Loading...' : 'Refresh'}
                            </button>
                          </div>
                        </div>
                      ) : (
                        isMultilineField ? (
                          <textarea
                            value={displayValue}
                            placeholder={paramDef?.placeholder}
                            onFocus={() => {
                              setEditingParam(key)
                              setLocalParams((prev) => ({
                                ...prev,
                                [key]: String(selectedNodeParams[key] ?? ''),
                              }))
                            }}
                            onChange={(e) => handleParamChange(key, e.target.value)}
                            onBlur={() => handleParamBlur(key)}
                            className={`workflow-inspector-input workflow-inspector-textarea ${key === 'code' || key === 'query' ? 'workflow-inspector-input--mono' : ''}`}
                            rows={key === 'code' ? 18 : key === 'query' ? 10 : 7}
                            spellCheck={false}
                          />
                        ) : (
                          <input
                            type="text"
                            value={displayValue}
                            placeholder={paramDef?.placeholder}
                            onFocus={() => {
                              setEditingParam(key)
                              setLocalParams((prev) => ({
                                ...prev,
                                [key]: String(selectedNodeParams[key] ?? ''),
                              }))
                            }}
                            onChange={(e) => handleParamChange(key, e.target.value)}
                            onBlur={() => handleParamBlur(key)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.currentTarget.blur()
                              }
                            }}
                            className="workflow-inspector-input"
                          />
                        )
                      )}
                    </div>
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
              Run Status
            </h4>

            <div className="workflow-inspector-run-info">
              <div className="workflow-inspector-run-row">
                <span className="workflow-inspector-run-label">{resolvedSelectedNode ? 'Node Status' : 'Status'}</span>
                <span className={`workflow-inspector-run-badge ${getStatusClass(displayRunStatus)}`}>
                  {displayRunStatus}
                </span>
              </div>

              {resolvedActiveRun.created_at && (
                <div className="workflow-inspector-run-row">
                  <span className="workflow-inspector-run-label">Started</span>
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
                  Node Output
                </div>
                {selectedNodeRunDetails ? (
                  <WorkflowInspectorOutputView
                    output={selectedNodeRunDetails.output}
                    rawOutput={selectedNodeRunDetails.raw}
                  />
                ) : (
                  <div className="workflow-inspector-output-empty">
                    No execution record for the selected node in the latest run yet.
                  </div>
                )}
              </div>
            ) : resolvedRunOutput ? (
              <div className="workflow-inspector-output">
                <div className="workflow-inspector-output-header">
                  <CheckCircle2 className="w-3 h-3" />
                  Workflow Output
                </div>
                <div className="workflow-inspector-output-empty">
                  Select a node to inspect a friendlier output view. Raw workflow output is still available below.
                </div>
                <details className="workflow-inspector-output-raw">
                  <summary>Raw JSON</summary>
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
