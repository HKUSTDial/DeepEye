import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react'

import type { WorkflowRunPhaseState } from '../../features/workflow/runPhase'
import { useLocale } from '../../locale'

type WorkflowRunPhaseBannerProps = {
  phase: WorkflowRunPhaseState
  compact?: boolean
}

function getPhaseStatusLabel(status: WorkflowRunPhaseState['status'], t: (key: string) => string) {
  if (status === 'done') return t('common.ready')
  if (status === 'error') return t('common.needsAttention')
  return t('common.running')
}

export function WorkflowRunPhaseBanner({
  phase,
  compact = false,
}: WorkflowRunPhaseBannerProps) {
  const { t } = useLocale()
  const isError = phase.status === 'error'
  const isDone = phase.status === 'done'
  const containerClass = isError
    ? 'border-rose-200 bg-rose-50 text-rose-950'
    : isDone
      ? 'border-emerald-200 bg-emerald-50 text-emerald-950'
      : 'border-sky-200 bg-sky-50 text-slate-950'
  const badgeClass = isError
    ? 'bg-rose-100 text-rose-700'
    : isDone
      ? 'bg-emerald-100 text-emerald-700'
      : 'bg-sky-100 text-sky-700'

  return (
    <div className={`rounded-2xl border px-4 py-3 shadow-sm ${containerClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-current/65">
            {t('workflow.toolbarLabel')}
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            {isError ? (
              <AlertTriangle className="h-4 w-4 shrink-0" />
            ) : isDone ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
            )}
            <div className="min-w-0 text-sm font-semibold leading-5">{phase.label}</div>
          </div>
          {phase.detail ? (
            <div className="mt-1 text-sm leading-5 text-current/80">{phase.detail}</div>
          ) : null}
          {phase.suggestion && (isError || !compact) ? (
            <div className="mt-2 text-xs leading-5 text-current/70">
              {t('common.openWorkflow')}: {phase.suggestion}
            </div>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${badgeClass}`}>
            {getPhaseStatusLabel(phase.status, t)}
          </span>
          {phase.nodeId ? (
            <span className="text-[11px] font-medium text-current/65">
              {t('common.node')} {phase.nodeId}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}
