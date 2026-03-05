/**
 * 邮箱验证页面
 */
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const INPUT_CLASS =
  'w-full rounded-xl border border-[var(--input-border)] bg-[var(--input-bg)] px-4 py-3 text-[var(--main-text)] placeholder-[var(--main-text-muted)] transition-colors focus:border-[var(--accent)] focus:outline-none'

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
    <AuthShell
      title="Email verification"
      subtitle="Verify from your email link, or resend a new verification message."
      leftTitle="Confirm account ownership"
      leftDescription="Verification remains a dedicated trust step, not a primary entry point."
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

      {token ? (
        <div className="space-y-4">
          <p className="text-sm text-[var(--main-text-muted)]">
            Click below to confirm your email with the verification token in this URL.
          </p>
          <button
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="w-full rounded-xl bg-[var(--accent)] py-3 font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-55"
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
              disabled={isSubmitting}
            />
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl bg-[var(--accent)] py-3 font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            {isSubmitting ? 'Sending...' : 'Send verification email'}
          </button>
        </form>
      )}

      <div className="space-x-3 text-sm text-[var(--main-text-muted)]">
        <button onClick={() => navigate('/auth')} className="text-[var(--accent)] hover:underline">
          Back to login
        </button>
        <button onClick={() => navigate('/forgot-password')} className="text-[var(--accent)] hover:underline">
          Forgot password
        </button>
      </div>
    </AuthShell>
  )
}
