/**
 * 重置密码页面
 */
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { authApi } from '../api/auth'
import { useLocale } from '../locale'

const INPUT_CLASS = 'auth-input'

export default function ResetPassword() {
  const { t } = useLocale()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const token = useMemo(() => searchParams.get('token')?.trim() ?? '', [searchParams])

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) return t('auth.passwordMin')
    if (password.length > 64) return t('auth.passwordMax')
    if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/\d/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      return t('auth.passwordComplexity')
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')

    if (!token) {
      setError(t('auth.reset.missingToken'))
      return
    }

    if (newPassword !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }

    const passwordError = validatePassword(newPassword)
    if (passwordError) {
      setError(passwordError)
      return
    }

    setIsLoading(true)
    try {
      const response = await authApi.confirmPasswordReset({
        token,
        new_password: newPassword,
      })
      setMessage(response.message)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('auth.reset.failed'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.reset.title')}
      subtitle={t('auth.reset.subtitle')}
      leftTitle={t('auth.reset.leftTitle')}
      leftDescription={t('auth.reset.leftDescription')}
    >
      {!token && (
        <div className="auth-feedback auth-feedback--error">
          {t('auth.reset.invalidLink')}
        </div>
      )}

      {error && (
        <div className="auth-feedback auth-feedback--error">
          {error}
        </div>
      )}

      {message && (
        <div className="auth-feedback auth-feedback--success">
          {message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="auth-form-row">
          <label htmlFor="newPassword" className="auth-form-label">
            {t('auth.newPassword')}
          </label>
          <input
            id="newPassword"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            maxLength={64}
            className={INPUT_CLASS}
            placeholder={t('auth.placeholderPassword')}
            disabled={isLoading || !token}
          />
        </div>

        <div className="auth-form-row">
          <label htmlFor="confirmPassword" className="auth-form-label">
            {t('auth.confirmPassword')}
          </label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={8}
            maxLength={64}
            className={INPUT_CLASS}
            placeholder={t('auth.placeholderPasswordResetConfirm')}
            disabled={isLoading || !token}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !token}
          className="auth-submit"
        >
          {isLoading ? t('auth.reset.submitting') : t('auth.reset.submit')}
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
