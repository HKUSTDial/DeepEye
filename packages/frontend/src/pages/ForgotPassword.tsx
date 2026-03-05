/**
 * 忘记密码页面
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { authApi } from '../api/auth'

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
    <div className="min-h-screen flex items-center justify-center bg-[var(--main-bg)] px-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-[var(--main-bg-alt)] rounded-2xl border border-[var(--input-border)]">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--main-text)]">DeepEye</h1>
          <p className="text-[var(--main-text-muted)] mt-2">Reset your password</p>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {message && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm break-words">
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
            <label htmlFor="email" className="block text-sm font-medium text-[var(--main-text)] mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--input-border)] rounded-xl text-[var(--main-text)] placeholder-[var(--main-text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              placeholder="you@example.com"
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Sending...' : 'Send reset link'}
          </button>
        </form>

        <div className="text-center text-sm text-[var(--main-text-muted)] space-y-2">
          <button
            onClick={() => navigate('/login')}
            className="text-[var(--accent)] hover:underline"
          >
            Back to login
          </button>
        </div>
      </div>
    </div>
  )
}
