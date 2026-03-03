import { memo, useMemo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { useWorkflowNodesStore } from '../../stores/workflowNodes'

type Port = { id: string; label: string }

interface WorkflowNodeData {
  type: string
  label: string
  inputs: Port[]
  outputs: Port[]
  runStatus?: 'running' | 'success' | 'failed' | 'pending'
  isNew?: boolean
}

const statusIcons = {
  running: Loader2,
  success: CheckCircle2,
  failed: XCircle,
  pending: Clock,
}

const statusClasses = {
  running: 'workflow-node--running',
  success: 'workflow-node--success',
  failed: 'workflow-node--failed',
  pending: 'workflow-node--pending',
}

function WorkflowNodeComponent({ data }: NodeProps<WorkflowNodeData>) {
  const nodeDefs = useWorkflowNodesStore((state) => state.nodeDefs)
  const def = nodeDefs[data.type]

  const inputs = useMemo(() => {
    if (def?.inputs) {
      return def.inputs.map((p) => ({ id: p.id, label: p.label }))
    }
    return data.inputs || []
  }, [def, data.inputs])

  const outputs = useMemo(() => {
    if (def?.outputs) {
      return def.outputs.map((p) => ({ id: p.id, label: p.label }))
    }
    return data.outputs || []
  }, [def, data.outputs])

  const StatusIcon = data.runStatus ? statusIcons[data.runStatus] : null
  const statusClass = data.runStatus ? statusClasses[data.runStatus] : ''
  const handleOffset = 12
  const newClass = data.isNew ? 'workflow-node--new' : ''

  return (
    <div className={`workflow-node ${statusClass} ${newClass}`}>
      <div className="workflow-node-header">
        <div className="workflow-node-title">{data.label}</div>
        {StatusIcon && (
          <StatusIcon
            className={`workflow-node-status-icon ${data.runStatus === 'running' ? 'workflow-node-status-icon--spinning' : ''}`}
          />
        )}
      </div>

      <div className="workflow-node-ports-container">
        <div className="workflow-node-ports-left">
          {inputs.map((port) => (
            <div key={port.id} className="workflow-node-port-item">
              <Handle
                type="target"
                position={Position.Left}
                id={port.id}
                style={{ top: '50%', left: -handleOffset, transform: 'translateY(-50%)' }}
                className="workflow-node-handle workflow-node-handle-input"
              />
              <span className="workflow-node-port-label">{port.label}</span>
            </div>
          ))}
        </div>

        <div className="workflow-node-ports-right">
          {outputs.map((port) => (
            <div key={port.id} className="workflow-node-port-item workflow-node-port-item-right">
              <span className="workflow-node-port-label">{port.label}</span>
              <Handle
                type="source"
                position={Position.Right}
                id={port.id}
                style={{ top: '50%', right: -handleOffset, transform: 'translateY(-50%)' }}
                className="workflow-node-handle workflow-node-handle-output"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default memo(WorkflowNodeComponent)
