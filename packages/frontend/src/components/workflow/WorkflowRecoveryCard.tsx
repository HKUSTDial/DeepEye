import { AlertTriangle, Copy, Database, FolderOpen, RotateCcw } from 'lucide-react'
import { useState } from 'react'

import type {
  WorkflowRecoveryAction,
  WorkflowRecoveryState,
} from '../../features/workflow/recovery'

interface WorkflowRecoveryCardProps {
  recovery: WorkflowRecoveryState
  canRetry?: boolean
  onRetry: () => Promise<void> | void
  onOpenDataSources: () => void
  onOpenFiles: () => void
}

function getActionIcon(kind: WorkflowRecoveryAction['kind']) {
  if (kind === 'open-datasources') return <Database className="h-4 w-4" />
  if (kind === 'open-related-file' || kind === 'open-files') return <FolderOpen className="h-4 w-4" />
  if (kind === 'copy-diagnostics') return <Copy className="h-4 w-4" />
  return <RotateCcw className="h-4 w-4" />
}

export function WorkflowRecoveryCard({
  recovery,
  canRetry = true,
  onRetry,
  onOpenDataSources,
  onOpenFiles,
}: WorkflowRecoveryCardProps) {
  const [isRetrying, setIsRetrying] = useState(false)
  const [copied, setCopied] = useState(false)

  const visibleActions = recovery.actions.filter(
    (action) => !(action.kind === 'retry-run' && !canRetry),
  )

  const handleAction = async (action: WorkflowRecoveryAction) => {
    if (action.kind === 'open-datasources') {
      onOpenDataSources()
      return
    }
    if (action.kind === 'open-related-file' || action.kind === 'open-files') {
      onOpenFiles()
      return
    }
    if (action.kind === 'copy-diagnostics') {
      try {
        await navigator.clipboard.writeText(recovery.diagnostics)
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1400)
      } catch {
        setCopied(false)
      }
      return
    }

    try {
      setIsRetrying(true)
      await onRetry()
    } finally {
      setIsRetrying(false)
    }
  }

  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-amber-700 shadow-sm">
          <AlertTriangle className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-800/80">
            Recovery
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">{recovery.title}</div>
          <div className="mt-1 text-sm leading-5 text-slate-700">{recovery.detail}</div>
          {recovery.suggestion ? (
            <div className="mt-2 text-xs leading-5 text-slate-600">
              Next: {recovery.suggestion}
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {visibleActions.map((action) => {
          const isCopyAction = action.kind === 'copy-diagnostics'
          const label = isCopyAction && copied ? 'Copied' : action.label
          const isDisabled = action.kind === 'retry-run' && isRetrying

          return (
            <button
              key={action.kind}
              type="button"
              disabled={isDisabled}
              onClick={() => void handleAction(action)}
              className="inline-flex items-center gap-2 rounded-full border border-amber-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 transition-colors hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {getActionIcon(action.kind)}
              <span>{isDisabled ? 'Retrying...' : label}</span>
            </button>
          )
        })}
      </div>
    </section>
  )
}
