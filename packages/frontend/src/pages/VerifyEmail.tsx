/**
 * 邮箱验证页面
 */
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { authApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const INPUT_CLASS = 'auth-input'

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
        <div className="auth-feedback auth-feedback--error">
          {error}
        </div>
      )}

      {message && (
        <div className="auth-feedback auth-feedback--success break-words">
          {message}
          {debugToken && (
            <div className="auth-feedback-meta">
              Debug token: <code>{debugToken}</code>
            </div>
          )}
        </div>
      )}

      {token ? (
        <div className="auth-form">
          <p className="text-sm text-[var(--main-text-muted)]">
            Click below to confirm your email with the verification token in this URL.
          </p>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="auth-submit"
          >
            {isSubmitting ? 'Verifying...' : 'Verify email now'}
          </button>
        </div>
      ) : (
        <form onSubmit={handleResend} className="auth-form">
          <p className="text-sm text-[var(--main-text-muted)]">
            Need a new verification email? Enter your account email below.
          </p>
          <div className="auth-form-row">
            <label htmlFor="email" className="auth-form-label">
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
            className="auth-submit"
          >
            {isSubmitting ? 'Sending...' : 'Send verification email'}
          </button>
        </form>
      )}

      <div className="auth-inline-actions">
        <button type="button" onClick={() => navigate('/auth')} className="auth-link">
          Back to login
        </button>
        <button type="button" onClick={() => navigate('/forgot-password')} className="auth-link">
          Forgot password
        </button>
      </div>
    </AuthShell>
  )
}
