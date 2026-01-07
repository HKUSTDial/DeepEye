import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'

type Port = { id: string; label: string }

interface WorkflowNodeData {
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

const statusColors = {
  running: 'text-green-400',
  success: 'text-blue-400',
  failed: 'text-red-400',
  pending: 'text-amber-400',
}

const statusBorders = {
  running: 'border-green-500/50 shadow-green-500/20',
  success: 'border-blue-500/50 shadow-blue-500/20',
  failed: 'border-red-500/50 shadow-red-500/20',
  pending: 'border-amber-500/50 shadow-amber-500/20',
}

function WorkflowNodeComponent({ data }: NodeProps<WorkflowNodeData>) {
  const StatusIcon = data.runStatus ? statusIcons[data.runStatus] : null
  const statusColor = data.runStatus ? statusColors[data.runStatus] : ''
  const statusBorder = data.runStatus ? statusBorders[data.runStatus] : 'border-white/10'
  const handleOffset = 12

  const newClass = data.isNew ? 'workflow-node--new' : ''

  return (
    <div
      className={`min-w-[180px] bg-gradient-to-br from-slate-900 to-slate-800 border ${statusBorder} 
        rounded-xl p-3 text-white shadow-xl transition-all duration-200 hover:shadow-2xl ${newClass}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold text-sm">{data.label}</div>
        {StatusIcon && (
          <StatusIcon
            className={`w-4 h-4 ${statusColor} ${data.runStatus === 'running' ? 'animate-spin' : ''}`}
          />
        )}
      </div>

      <div className="flex justify-between gap-3 text-xs">
        <div className="flex flex-col gap-1 pr-2">
          {data.inputs.map((port, index) => (
            <div
              key={port.id}
              className="relative flex items-center gap-2 h-6 leading-6 overflow-visible"
            >
              <Handle
                type="target"
                position={Position.Left}
                id={port.id}
                style={{ top: '50%', left: -handleOffset, transform: 'translateY(-50%)' }}
                className="!absolute !w-2 !h-2 !border-2 !border-blue-400 !bg-blue-500"
              />
              <span className="text-slate-300">{port.label}</span>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-1 pl-2">
          {data.outputs.map((port, index) => (
            <div
              key={port.id}
              className="relative flex items-center justify-between gap-2 text-right w-full h-6 leading-6 overflow-visible"
            >
              <span className="text-slate-300">{port.label}</span>
              <Handle
                type="source"
                position={Position.Right}
                id={port.id}
                style={{ top: '50%', right: -handleOffset, transform: 'translateY(-50%)' }}
                className="!absolute !w-2 !h-2 !border-2 !border-purple-400 !bg-purple-500"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default memo(WorkflowNodeComponent)
