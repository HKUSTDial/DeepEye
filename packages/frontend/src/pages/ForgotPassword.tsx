/**
 * 忘记密码页面
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { authApi } from '../api/auth'

const INPUT_CLASS = 'auth-input'

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

      <form onSubmit={handleSubmit} className="auth-form">
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
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="auth-submit"
        >
          {isLoading ? 'Sending...' : 'Send reset link'}
        </button>
      </form>

      <div className="auth-muted-actions">
        <button type="button" onClick={() => navigate('/auth')} className="auth-link">
          Back to login
        </button>
      </div>
    </AuthShell>
  )
}
