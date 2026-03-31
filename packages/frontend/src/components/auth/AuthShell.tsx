import type { ReactNode } from 'react'
import { useLocale } from '../../locale'
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

export default function AuthShell({
  title,
  subtitle,
  leftTitle,
  leftDescription,
  leftPoints,
  children,
  footer,
}: AuthShellProps) {
  const { t } = useLocale()
  const points =
    leftPoints && leftPoints.length > 0
      ? leftPoints
      : [t('auth.point1'), t('auth.point2'), t('auth.point3')]

  return (
    <div className="auth-shell">
      <div className="auth-shell__inner">
        <section className="auth-shell__aside">
          <div className="auth-shell__aside-top">
            <div className="auth-shell__badge">{t('auth.badge')}</div>
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
            <div className="auth-shell__kicker">{t('auth.kicker')}</div>
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
