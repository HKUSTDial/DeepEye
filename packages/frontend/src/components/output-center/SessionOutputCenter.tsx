import {
  ArrowUpRight,
  FileText,
  LayoutDashboard,
  Video,
  Workflow as WorkflowIcon,
} from 'lucide-react'
import { useMemo, type ReactNode } from 'react'

import { useWorkflowSessionsStore } from '../../stores/workflowSessions'
import {
  getArtifactError,
  getArtifactFileName,
  getArtifactPreviewUrl,
  getArtifactStatus,
  getArtifactTaskId,
  latestArtifactByKind,
} from '../../utils/artifactUtils'

type PanelTarget = {
  pluginId: string
  params?: Record<string, unknown>
}

type SessionOutputCenterProps = {
  sessionId: string | null
  onOpenPanel: (pluginId: string, params?: Record<string, unknown>) => void
}

type OutputCardStatus = 'running' | 'ready' | 'error' | 'idle'

type OutputCard = {
  id: string
  title: string
  detail: string
  status: OutputCardStatus
  icon: ReactNode
  target: PanelTarget
}

function getStatusClasses(status: OutputCardStatus) {
  if (status === 'error') {
    return {
      badge: 'bg-rose-100 text-rose-700',
      card: 'border-rose-200 bg-rose-50/70 hover:bg-rose-50',
    }
  }
  if (status === 'ready') {
    return {
      badge: 'bg-emerald-100 text-emerald-700',
      card: 'border-emerald-200 bg-emerald-50/70 hover:bg-emerald-50',
    }
  }
  if (status === 'running') {
    return {
      badge: 'bg-sky-100 text-sky-700',
      card: 'border-sky-200 bg-sky-50/70 hover:bg-sky-50',
    }
  }
  return {
    badge: 'bg-slate-200 text-slate-700',
    card: 'border-slate-200 bg-white hover:bg-slate-50',
  }
}

function getStatusLabel(status: OutputCardStatus) {
  if (status === 'error') return 'Needs attention'
  if (status === 'ready') return 'Ready'
  if (status === 'running') return 'Running'
  return 'Available'
}

export function SessionOutputCenter({
  sessionId,
  onOpenPanel,
}: SessionOutputCenterProps) {
  const sessionState = useWorkflowSessionsStore((state) =>
    sessionId ? state.sessions[sessionId] : undefined,
  )

  const cards = useMemo<OutputCard[]>(() => {
    if (!sessionState) return []

    const nextCards: OutputCard[] = []
    const workflowAvailable =
      !!sessionState.definition ||
      !!sessionState.activeRun ||
      sessionState.viewState === 'ready' ||
      sessionState.viewState === 'error'

    if (workflowAvailable) {
      const workflowStatus: OutputCardStatus =
        sessionState.runPhase?.status === 'error'
          ? 'error'
          : sessionState.runStatus === 'running' || sessionState.runPhase?.status === 'running'
            ? 'running'
            : sessionState.runStatus === 'failed'
              ? 'error'
              : 'ready'
      nextCards.push({
        id: 'workflow',
        title: 'Workflow',
        detail:
          sessionState.runPhase?.detail ??
          sessionState.runPhase?.label ??
          (sessionState.runStatus ? `Latest run: ${sessionState.runStatus}` : 'Draft available'),
        status: workflowStatus,
        icon: <WorkflowIcon className="h-4 w-4" />,
        target: { pluginId: 'workflow' },
      })
    }

    const reportArtifact = latestArtifactByKind(sessionState.artifacts, 'report')
    if (reportArtifact) {
      const filename = getArtifactFileName(reportArtifact, 'report') ?? 'Generated report available'
      nextCards.push({
        id: 'report',
        title: 'Report',
        detail: filename,
        status: getArtifactError(reportArtifact) || getArtifactStatus(reportArtifact) === 'failed' ? 'error' : 'ready',
        icon: <FileText className="h-4 w-4" />,
        target: { pluginId: 'report' },
      })
    }

    const dashboardArtifact = latestArtifactByKind(sessionState.artifacts, 'dashboard')
    if (dashboardArtifact) {
      const dashboardUrl = getArtifactPreviewUrl(dashboardArtifact)
      nextCards.push({
        id: 'dashboard',
        title: 'Dashboard',
        detail: dashboardUrl ? 'Latest dashboard preview is ready to open.' : 'Dashboard artifact is available.',
        status: getArtifactStatus(dashboardArtifact) === 'failed' ? 'error' : 'ready',
        icon: <LayoutDashboard className="h-4 w-4" />,
        target: { pluginId: 'dashboard' },
      })
    }

    const videoArtifact = latestArtifactByKind(sessionState.artifacts, 'video')
    if (videoArtifact) {
      const taskId = getArtifactTaskId(videoArtifact)
      nextCards.push({
        id: 'video',
        title: 'Video',
        detail: taskId ? `Preview ready for task ${taskId}` : 'Latest video preview is ready to open.',
        status: getArtifactStatus(videoArtifact) === 'failed' ? 'error' : 'ready',
        icon: <Video className="h-4 w-4" />,
        target: {
          pluginId: 'video-preview',
          params: taskId ? { taskId } : undefined,
        },
      })
    }

    return nextCards
  }, [sessionState])

  if (!sessionId || sessionId === 'draft') {
    return null
  }

  if (cards.length === 0) {
    return (
      <section className="mb-4 rounded-3xl border border-dashed border-slate-300 bg-white/80 px-5 py-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Latest Outputs
        </div>
        <div className="mt-2 text-sm font-medium text-slate-900">
          Results from this thread will appear here.
        </div>
        <div className="mt-1 text-sm text-slate-600">
          Generated workflows, reports, dashboards, and video previews stay grouped by session.
        </div>
      </section>
    )
  }

  return (
    <section className="mb-4 rounded-3xl border border-slate-200 bg-white/90 px-4 py-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Latest Outputs
          </div>
          <div className="mt-1 text-sm text-slate-600">
            Everything produced in this thread, grouped in one place.
          </div>
        </div>
        <div className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
          {cards.length} item{cards.length === 1 ? '' : 's'}
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const styles = getStatusClasses(card.status)
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => onOpenPanel(card.target.pluginId, card.target.params)}
              className={`group rounded-2xl border px-4 py-3 text-left transition-colors ${styles.card}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-slate-700 shadow-sm">
                    {card.icon}
                  </span>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-slate-950">{card.title}</div>
                    <div className="mt-1 text-sm leading-5 text-slate-600">{card.detail}</div>
                  </div>
                </div>
                <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0 text-slate-400 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </div>
              <div className="mt-3">
                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${styles.badge}`}>
                  {getStatusLabel(card.status)}
                </span>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
