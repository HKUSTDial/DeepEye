import type { ReactNode } from 'react'
import './AuthShell.css'

interface AuthShellProps {
  title: string
  subtitle: string
  leftTitle: string
  leftDescription: string
  leftPoints?: string[]
  children: ReactNode
  footer?: ReactNode
}

const DEFAULT_POINTS = [
  'Single secure account for all DeepEye capabilities',
  'Clear, focused auth flows with minimal jumps',
  'Consistent UX across login, signup, and recovery',
]

export default function AuthShell({
  title,
  subtitle,
  leftTitle,
  leftDescription,
  leftPoints,
  children,
  footer,
}: AuthShellProps) {
  const points = leftPoints && leftPoints.length > 0 ? leftPoints : DEFAULT_POINTS

  return (
    <div className="auth-shell">
      <div className="auth-shell__inner">
        <section className="auth-shell__aside">
          <div className="auth-shell__aside-top">
            <div className="auth-shell__badge">DeepEye Workspace</div>
            <h1 className="auth-shell__headline">{leftTitle}</h1>
            <p className="auth-shell__lead">{leftDescription}</p>
          </div>

          <div className="auth-shell__points">
            {points.map((point) => (
              <div key={point} className="auth-shell__point">
                <span className="auth-shell__point-dot" aria-hidden="true"></span>
                <span>{point}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="auth-shell__card">
          <div className="auth-shell__form-shell">
            <div className="auth-shell__kicker">Account access</div>
            <div className="auth-shell__copy">
              <h2 className="auth-shell__title">{title}</h2>
              <p className="auth-shell__subtitle">{subtitle}</p>
            </div>

            <div className="auth-shell__content">{children}</div>

            {footer && <div className="auth-shell__footer">{footer}</div>}
          </div>
        </section>
      </div>
    </div>
  )
}
