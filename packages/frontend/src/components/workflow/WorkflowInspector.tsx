import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Settings, AlertCircle, PlayCircle, CheckCircle2 } from 'lucide-react'
import { useWorkflowStore } from '../../stores/workflow'
import type { NodeDef } from '../../stores/workflowNodes'
import { useShallow } from 'zustand/react/shallow'
import type { Node } from 'reactflow'
import type { WorkflowRun } from '../../types'

interface WorkflowInspectorProps {
  selectedNodeId: string | null
  nodeDefs: Record<string, NodeDef>
  onUpdateParam: (nodeId: string, key: string, value: string) => void
  nodes?: Node[]
  activeRun?: WorkflowRun | null
  runOutput?: string
}

function stringifyParams(params: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)]))
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

  // 处理参数更新
  const handleParamChange = useCallback((key: string, value: string) => {
    setLocalParams((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleParamBlur = useCallback(
    (key: string) => {
      if (!resolvedSelectedNode) return
      const value = localParams[key]
      onUpdateParam(resolvedSelectedNode.id, key, value)
      setEditingParam(null)
    },
    [resolvedSelectedNode, localParams, onUpdateParam],
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
                  const selectedParams = (resolvedSelectedNode.data.params as Record<string, unknown>) || {}
                  const displayValue = editingParam === key ? localParams[key] : String(selectedParams[key] || '')

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
                      <input
                        type="text"
                        value={displayValue}
                        placeholder={paramDef?.placeholder}
                        onFocus={() => {
                          setEditingParam(key)
                          setLocalParams((prev) => ({
                            ...prev,
                            [key]: String(selectedParams[key] || ''),
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
            <p className="workflow-inspector-placeholder-text">Select a node to edit parameters</p>
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
                <span className="workflow-inspector-run-label">Status</span>
                <span className={`workflow-inspector-run-badge ${getStatusClass(resolvedActiveRun.status)}`}>
                  {resolvedActiveRun.status}
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

            {resolvedRunOutput && (
              <div className="workflow-inspector-output">
                <div className="workflow-inspector-output-header">
                  <CheckCircle2 className="w-3 h-12" />
                  Output
                </div>
                <pre className="workflow-inspector-output-content">
                  {resolvedRunOutput}
                </pre>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </motion.aside>
  )
}

function getStatusClass(status: string): string {
  switch (status) {
    case 'running':
      return 'running'
    case 'success':
    case 'completed':
      return 'success'
    case 'failed':
      return 'failed'
    case 'pending':
      return 'pending'
    default:
      return ''
  }
}
