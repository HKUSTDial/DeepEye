import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { useAuthStore } from '../stores/auth'

const INPUT_CLASS =
  'w-full rounded-xl border border-[var(--input-border)] bg-[var(--input-bg)] px-4 py-3 text-[var(--main-text)] placeholder-[var(--main-text-muted)] transition-colors focus:border-[var(--accent)] focus:outline-none'

function sanitizeNextPath(raw: string | null): string {
  const value = (raw ?? '').trim()
  if (!value) return '/'
  if (!value.startsWith('/') || value.startsWith('//')) return '/'
  return value
}

export default function Auth() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const login = useAuthStore((state) => state.login)

  const defaultEmail = useMemo(() => searchParams.get('email')?.trim() ?? '', [searchParams])
  const nextPath = useMemo(() => sanitizeNextPath(searchParams.get('next')), [searchParams])

  const [email, setEmail] = useState(defaultEmail)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email.trim(), password)
      navigate(nextPath)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Use your DeepEye account to continue."
      leftTitle="Sign in to your workspace"
      leftDescription="Standard entry point with separated signup and recovery flows."
    >
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleLogin} className="space-y-4">
        <div>
          <label htmlFor="auth-email" className="mb-2 block text-sm font-medium text-[var(--main-text)]">
            Email
          </label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
            placeholder="you@example.com"
            className={INPUT_CLASS}
          />
        </div>

        <div>
          <label htmlFor="auth-password" className="mb-2 block text-sm font-medium text-[var(--main-text)]">
            Password
          </label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            placeholder="••••••••"
            className={INPUT_CLASS}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-xl bg-[var(--accent)] py-3 font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {isLoading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>

      <div className="space-y-2 text-sm text-[var(--main-text-muted)]">
        <div>
          New to DeepEye?{' '}
          <button
            type="button"
            onClick={() => navigate('/register')}
            className="text-[var(--accent)] hover:underline"
          >
            Create account
          </button>
        </div>
        <div>
          Forgot password?{' '}
          <button
            type="button"
            onClick={() => navigate('/forgot-password')}
            className="text-[var(--accent)] hover:underline"
          >
            Recover access
          </button>
        </div>
      </div>
    </AuthShell>
  )
}
