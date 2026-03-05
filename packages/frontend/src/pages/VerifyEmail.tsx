/**
 * 邮箱验证页面
 */
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'

export default function VerifyEmail() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentUser = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)

  const token = useMemo(() => searchParams.get('token')?.trim() ?? '', [searchParams])
  const emailFromQuery = useMemo(() => searchParams.get('email')?.trim() ?? '', [searchParams])

  const [email, setEmail] = useState(emailFromQuery || currentUser?.email || '')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [debugToken, setDebugToken] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setDebugToken(null)

    setIsSubmitting(true)
    try {
      const response = await authApi.requestEmailVerification({ email })
      setMessage(response.message)
      setDebugToken(response.debug_token ?? null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleConfirm = async () => {
    setError('')
    setMessage('')
    setDebugToken(null)

    if (!token) {
      setError('Missing verification token in URL.')
      return
    }

    setIsSubmitting(true)
    try {
      const response = await authApi.confirmEmailVerification({ token })
      setMessage(response.message)
      if (currentUser) {
        setUser({ ...currentUser, is_email_verified: true })
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--main-bg)] px-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-[var(--main-bg-alt)] rounded-2xl border border-[var(--input-border)]">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--main-text)]">DeepEye</h1>
          <p className="text-[var(--main-text-muted)] mt-2">Email verification</p>
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

        {token ? (
          <div className="space-y-4">
            <p className="text-sm text-[var(--main-text-muted)]">
              Click below to confirm your email with the verification token in this URL.
            </p>
            <button
              onClick={handleConfirm}
              disabled={isSubmitting}
              className="w-full py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Verifying...' : 'Verify email now'}
            </button>
          </div>
        ) : (
          <form onSubmit={handleResend} className="space-y-4">
            <p className="text-sm text-[var(--main-text-muted)]">
              Need a new verification email? Enter your account email below.
            </p>
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
                disabled={isSubmitting}
              />
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Sending...' : 'Send verification email'}
            </button>
          </form>
        )}

        <div className="text-center text-sm text-[var(--main-text-muted)] space-x-3">
          <button
            onClick={() => navigate('/login')}
            className="text-[var(--accent)] hover:underline"
          >
            Back to login
          </button>
          <button
            onClick={() => navigate('/forgot-password')}
            className="text-[var(--accent)] hover:underline"
          >
            Forgot password
          </button>
        </div>
      </div>
    </div>
  )
}
