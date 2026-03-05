/**
 * 忘记密码页面
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { authApi } from '../api/auth'

const INPUT_CLASS =
  'w-full rounded-xl border border-[var(--input-border)] bg-[var(--input-bg)] px-4 py-3 text-[var(--main-text)] placeholder-[var(--main-text-muted)] transition-colors focus:border-[var(--accent)] focus:outline-none'

export default function ForgotPassword() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [debugToken, setDebugToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setDebugToken(null)
    setIsLoading(true)

    try {
      const response = await authApi.requestPasswordReset({ email })
      setMessage(response.message)
      setDebugToken(response.debug_token ?? null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title="Recover access"
      subtitle="Send a reset link to your account email."
      leftTitle="Password recovery"
      leftDescription="Generate a one-time reset link and continue in a dedicated reset screen."
    >
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {message && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300 break-words">
          {message}
          {debugToken && (
            <div className="mt-2 text-xs text-emerald-200/90">
              Debug token: <code>{debugToken}</code>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-medium text-[var(--main-text)]">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={INPUT_CLASS}
            placeholder="you@example.com"
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-xl bg-[var(--accent)] py-3 font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {isLoading ? 'Sending...' : 'Send reset link'}
        </button>
      </form>

      <div className="text-sm text-[var(--main-text-muted)]">
        <button onClick={() => navigate('/auth')} className="text-[var(--accent)] hover:underline">
          Back to login
        </button>
      </div>
    </AuthShell>
  )
}
