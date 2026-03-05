import type { ReactNode } from 'react'

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
    <div className="min-h-screen relative overflow-hidden bg-[var(--main-bg)] px-4 py-8 md:py-12">
      <div className="pointer-events-none absolute inset-0 opacity-65">
        <div className="absolute -top-16 left-[-8%] h-72 w-72 rounded-full bg-cyan-400/20 blur-3xl"></div>
        <div className="absolute top-1/3 right-[-12%] h-80 w-80 rounded-full bg-emerald-500/20 blur-3xl"></div>
      </div>

      <div className="relative mx-auto grid w-full max-w-5xl overflow-hidden rounded-3xl border border-[var(--input-border)] bg-[var(--main-bg-alt)] shadow-[0_30px_90px_rgba(0,0,0,0.2)] md:grid-cols-[1.1fr_1fr]">
        <section className="hidden md:flex flex-col justify-between bg-gradient-to-br from-cyan-700 via-cyan-600 to-emerald-600 p-10 text-white">
          <div>
            <div className="inline-flex items-center rounded-full bg-white/15 px-3 py-1 text-xs uppercase tracking-[0.2em]">
              DeepEye
            </div>
            <h1 className="mt-6 text-4xl font-semibold leading-tight">{leftTitle}</h1>
            <p className="mt-4 text-sm leading-relaxed text-white/85">{leftDescription}</p>
          </div>
          <div className="space-y-2 text-sm text-white/85">
            {points.map((point) => (
              <p key={point}>{point}</p>
            ))}
          </div>
        </section>

        <section className="p-6 sm:p-8 md:p-10">
          <div className="mx-auto w-full max-w-md space-y-6">
            <div>
              <h2 className="text-2xl font-semibold text-[var(--main-text)]">{title}</h2>
              <p className="mt-1 text-sm text-[var(--main-text-muted)]">{subtitle}</p>
            </div>

            {children}

            {footer && <div className="text-sm text-[var(--main-text-muted)]">{footer}</div>}
          </div>
        </section>
      </div>
    </div>
  )
}
