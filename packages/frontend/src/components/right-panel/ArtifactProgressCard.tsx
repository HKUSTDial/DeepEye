import type { CSSProperties, ReactNode } from 'react'

export type ArtifactProgressStatus = 'running' | 'waiting' | 'ready' | 'failed'
export type ArtifactProgressStepStatus = 'done' | 'active' | 'warning' | 'pending'
export type ArtifactProgressVariant = 'report' | 'dashboard' | 'video'

export interface ArtifactProgressMetric {
  label: string
  value: string
}

export interface ArtifactProgressStep {
  id?: string
  label: string
  detail?: string
  icon?: ReactNode
  status: ArtifactProgressStepStatus
}

interface ArtifactProgressCardProps {
  artifact: string
  title: string
  description: string
  icon: ReactNode
  variant?: ArtifactProgressVariant
  signature?: string
  status: ArtifactProgressStatus
  statusLabel: string
  percent: number
  currentLabel?: string
  metrics?: ArtifactProgressMetric[]
  steps: ArtifactProgressStep[]
  tone?: string
}

const STEP_STATUS_COPY: Record<ArtifactProgressStepStatus, string> = {
  done: 'Completed',
  active: 'In progress',
  warning: 'Needs review',
  pending: 'Queued',
}

function clampPercent(value: number) {
  if (Number.isNaN(value)) return 0
  return Math.min(100, Math.max(0, Math.round(value)))
}

export function ArtifactProgressCard({
  artifact,
  title,
  description,
  icon,
  variant,
  signature,
  status,
  statusLabel,
  percent,
  currentLabel,
  metrics = [],
  steps,
  tone,
}: ArtifactProgressCardProps) {
  const normalizedPercent = clampPercent(percent)
  const progressLabel = status === 'failed' ? 'Failed' : `${normalizedPercent}%`
  const style = tone
    ? ({ ['--artifact-progress-tone' as string]: tone } as CSSProperties)
    : undefined

  return (
    <section
      className={[
        'artifact-progress-card',
        `artifact-progress-card--${status}`,
        variant ? `artifact-progress-card--${variant}` : '',
      ].filter(Boolean).join(' ')}
      style={style}
    >
      <div className="artifact-progress-head">
        <div className="artifact-progress-identity">
          <div className="artifact-progress-icon">{icon}</div>
          <div className="artifact-progress-copy">
            <div className="artifact-progress-kicker-row">
              <div className="artifact-progress-kicker">{artifact}</div>
              {signature ? <div className="artifact-progress-signature">{signature}</div> : null}
            </div>
            <div className="artifact-progress-title">{title}</div>
            <div className="artifact-progress-description">{description}</div>
          </div>
        </div>

        <div className="artifact-progress-meter">
          <div className={`artifact-progress-status artifact-progress-status--${status}`}>
            <span className="artifact-progress-status-dot" />
            <span>{statusLabel}</span>
          </div>
          <div className="artifact-progress-value tabular-nums">{progressLabel}</div>
          {currentLabel ? <div className="artifact-progress-caption">{currentLabel}</div> : null}
        </div>
      </div>

      <div
        className="artifact-progress-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={normalizedPercent}
      >
        <div className="artifact-progress-track-fill" style={{ width: `${normalizedPercent}%` }} />
      </div>

      {metrics.length > 0 ? (
        <div className="artifact-progress-metrics">
          {metrics.map((metric) => (
            <div key={`${metric.label}-${metric.value}`} className="artifact-progress-metric">
              <span className="artifact-progress-metric-label">{metric.label}</span>
              <span className="artifact-progress-metric-value">{metric.value}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="artifact-progress-steps">
        {steps.map((step, index) => (
          <div
            key={step.id ?? `${step.label}-${index}`}
            className={`artifact-progress-step artifact-progress-step--${step.status}`}
          >
            <div className="artifact-progress-step-head">
              <div className="artifact-progress-step-icon">
                {step.icon ?? <span>{String(index + 1).padStart(2, '0')}</span>}
              </div>
              <div className={`artifact-progress-step-badge artifact-progress-step-badge--${step.status}`}>
                {step.detail ?? STEP_STATUS_COPY[step.status]}
              </div>
            </div>
            <div className="artifact-progress-step-label">{step.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
