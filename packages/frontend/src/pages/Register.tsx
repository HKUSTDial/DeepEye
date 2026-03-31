/**
 * 注册页面
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { useLocale } from '../locale'
import { useAuthStore } from '../stores/auth'

const INPUT_CLASS = 'auth-input'

export default function Register() {
  const { t } = useLocale()
  const navigate = useNavigate()
  const register = useAuthStore((state) => state.register)

  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }

    if (password.length < 8) {
      setError(t('auth.passwordMin'))
      return
    }

    if (password.length > 64) {
      setError(t('auth.passwordMax'))
      return
    }

    if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/\d/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      setError(t('auth.passwordComplexity'))
      return
    }

    setIsLoading(true)

    try {
      await register(email, username, password)
      navigate(`/verify-email?email=${encodeURIComponent(email)}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('auth.register.failed'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.register.title')}
      subtitle={t('auth.register.subtitle')}
      leftTitle={t('auth.register.leftTitle')}
      leftDescription={t('auth.register.leftDescription')}
    >
      {error && (
        <div className="auth-feedback auth-feedback--error">
          {error}
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

        <div className="auth-form-row">
          <label htmlFor="username" className="auth-form-label">
            {t('auth.username')}
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={2}
            className={INPUT_CLASS}
            placeholder={t('auth.placeholderUsername')}
            disabled={isLoading}
          />
        </div>

        <div className="auth-form-row">
          <label htmlFor="password" className="auth-form-label">
            {t('auth.password')}
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            maxLength={64}
            className={INPUT_CLASS}
            placeholder={t('auth.placeholderPassword')}
            disabled={isLoading}
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
            placeholder={t('auth.placeholderPasswordConfirm')}
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="auth-submit"
        >
          {isLoading ? t('auth.register.submitting') : t('auth.register.submit')}
        </button>
      </form>

      <div className="auth-muted-actions">
        <div>
          {t('auth.register.haveAccount')}{' '}
          <button type="button" onClick={() => navigate('/auth')} className="auth-link">
            {t('auth.register.signIn')}
          </button>
        </div>
      </div>
    </AuthShell>
  )
}
