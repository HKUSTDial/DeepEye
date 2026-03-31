import { useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { useLocale } from '../locale'
import { useAuthStore } from '../stores/auth'

const INPUT_CLASS = 'auth-input'

function sanitizeNextPath(raw: string | null): string {
  const value = (raw ?? '').trim()
  if (!value) return '/'
  if (!value.startsWith('/') || value.startsWith('//')) return '/'
  return value
}

export default function Auth() {
  const { t } = useLocale()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const login = useAuthStore((state) => state.login)

  const defaultEmail = useMemo(() => searchParams.get('email')?.trim() ?? '', [searchParams])
  const nextPath = useMemo(() => sanitizeNextPath(searchParams.get('next')), [searchParams])

  const [email, setEmail] = useState(defaultEmail)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)

  const requestFormSubmit = () => {
    if (isLoading) return
    formRef.current?.requestSubmit()
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email.trim(), password)
      navigate(nextPath)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('auth.login.failed'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.login.title')}
      subtitle={t('auth.login.subtitle')}
      leftTitle={t('auth.login.leftTitle')}
      leftDescription={t('auth.login.leftDescription')}
    >
      {error && (
        <div className="auth-feedback auth-feedback--error">
          {error}
        </div>
      )}

      <form ref={formRef} onSubmit={handleLogin} className="auth-form">
        <div className="auth-form-row">
          <label htmlFor="auth-email" className="auth-form-label">
            {t('auth.email')}
          </label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={isLoading}
            placeholder={t('auth.placeholderEmail')}
            className={INPUT_CLASS}
          />
        </div>

        <div className="auth-form-row">
          <label htmlFor="auth-password" className="auth-form-label">
            {t('auth.password')}
          </label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.nativeEvent.isComposing) {
                event.preventDefault()
                requestFormSubmit()
              }
            }}
            required
            disabled={isLoading}
            placeholder="••••••••"
            className={INPUT_CLASS}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="auth-submit"
        >
          {isLoading ? t('auth.login.submitting') : t('auth.login.submit')}
        </button>
      </form>

      <div className="auth-muted-actions">
        <div>
          {t('auth.login.newToDeepEye')}{' '}
          <button
            type="button"
            onClick={() => navigate('/register')}
            className="auth-link"
          >
            {t('auth.login.createAccount')}
          </button>
        </div>
        <div>
          {t('auth.login.forgotPassword')}{' '}
          <button
            type="button"
            onClick={() => navigate('/forgot-password')}
            className="auth-link"
          >
            {t('auth.login.recoverAccess')}
          </button>
        </div>
      </div>
    </AuthShell>
  )
}
