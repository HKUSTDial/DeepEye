import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Settings, AlertCircle, PlayCircle, CheckCircle2 } from 'lucide-react'
import { useWorkflowStore } from '../../stores/workflow'
import { useShallow } from 'zustand/react/shallow'
import type { Node } from 'reactflow'
import type { WorkflowRun } from '../../types'

interface WorkflowInspectorProps {
  selectedNodeId: string | null
  nodeDefs: Record<string, any>
  onUpdateParam: (nodeId: string, key: string, value: string) => void
  nodes?: Node[]
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

  // 当选中的节点改变时，重置本地参数状态
  useEffect(() => {
    if (resolvedSelectedNode) {
      const params = resolvedSelectedNode.data.params || {}
      setLocalParams(Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)])))
    } else {
      setLocalParams({})
    }
    setEditingParam(null)
  }, [selectedNodeId, resolvedSelectedNode?.id])

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
      className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col overflow-hidden"
    >
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center gap-2 text-white">
          <Settings className="w-5 h-5 text-purple-400" />
          <h3 className="font-semibold text-lg">Inspector</h3>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {resolvedSelectedNode ? (
          <>
            {/* Node Info */}
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="p-4 bg-slate-800/50 border border-slate-700 rounded-xl"
            >
              <div className="font-semibold text-white mb-1">{resolvedSelectedNode.data.label}</div>
              {nodeDef?.description && (
                <div className="mt-2 text-xs text-slate-300">{nodeDef.description}</div>
              )}
            </motion.div>

            {/* Parameters */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Parameters</h4>
              {Object.keys(resolvedSelectedNode.data.params || {}).length === 0 ? (
                <div className="text-sm text-slate-500 text-center py-4">No parameters</div>
              ) : (
                Object.keys(resolvedSelectedNode.data.params || {}).map((key) => {
                  const paramDef = nodeDef?.params?.[key]
                  const required = paramDef?.required
                  const displayValue = editingParam === key ? localParams[key] : String(resolvedSelectedNode.data.params[key] || '')

                  return (
                    <div key={`${resolvedSelectedNode.id}-${key}`} className="space-y-1.5">
                      <label className="flex items-center justify-between text-xs text-slate-300">
                        <span className="font-medium">{key}</span>
                        {required ? (
                          <span className="flex items-center gap-1 text-amber-400">
                            <AlertCircle className="w-3 h-3" />
                            required
                          </span>
                        ) : (
                          <span className="text-slate-500">optional</span>
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
                            [key]: String(resolvedSelectedNode.data.params[key] || ''),
                          }))
                        }}
                        onChange={(e) => handleParamChange(key, e.target.value)}
                        onBlur={() => handleParamBlur(key)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.currentTarget.blur()
                          }
                        }}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg 
                          text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 
                          focus:ring-2 focus:ring-blue-500/20 transition-all"
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
            className="flex flex-col items-center justify-center py-12 text-center"
          >
            <Settings className="w-12 h-12 text-slate-700 mb-3" />
            <p className="text-sm text-slate-500">Select a node to edit parameters</p>
          </motion.div>
        )}

        {/* Run Status */}
        {resolvedActiveRun && (
          <motion.div
            initial={{ y: 10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="mt-4 space-y-3"
          >
            <h4 className="text-sm font-medium text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <PlayCircle className="w-4 h-4" />
              Run Status
            </h4>

            <div className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-400">Status</span>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(resolvedActiveRun.status)}`}
                >
                  {resolvedActiveRun.status}
                </span>
              </div>

              {resolvedActiveRun.created_at && (
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>Started</span>
                  <span>{new Date(resolvedActiveRun.created_at).toLocaleTimeString()}</span>
                </div>
              )}
            </div>

            {resolvedRunOutput && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <CheckCircle2 className="w-3 h-3" />
                  Output
                </div>
                <pre
                  className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs 
                  text-slate-300 overflow-auto max-h-512 custom-scrollbar font-mono"
                >
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

function getStatusColor(status: string): string {
  switch (status) {
    case 'running':
      return 'bg-green-500/20 text-green-400 border border-green-500/30'
    case 'success':
    case 'completed':
      return 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
    case 'failed':
      return 'bg-red-500/20 text-red-400 border border-red-500/30'
    case 'pending':
      return 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
    default:
      return 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
  }
}

