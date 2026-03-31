/**
 * 忘记密码页面
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { authApi } from '../api/auth'
import { useLocale } from '../locale'

const INPUT_CLASS = 'auth-input'

export default function ForgotPassword() {
  const { t } = useLocale()
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
      setError(err instanceof Error ? err.message : t('auth.forgot.failed'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.forgot.title')}
      subtitle={t('auth.forgot.subtitle')}
      leftTitle={t('auth.forgot.leftTitle')}
      leftDescription={t('auth.forgot.leftDescription')}
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
              {t('auth.verify.debugToken')}: <code>{debugToken}</code>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="auth-form-row">
          <label htmlFor="email" className="auth-form-label">
            {t('auth.email')}
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={INPUT_CLASS}
            placeholder={t('auth.placeholderEmail')}
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="auth-submit"
        >
          {isLoading ? t('auth.forgot.submitting') : t('auth.forgot.submit')}
        </button>
      </form>

      <div className="auth-muted-actions">
        <button type="button" onClick={() => navigate('/auth')} className="auth-link">
          {t('auth.forgot.backToLogin')}
        </button>
      </div>
    </AuthShell>
  )
}
