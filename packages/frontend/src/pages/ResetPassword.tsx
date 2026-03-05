/**
 * 重置密码页面
 */
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { authApi } from '../api/auth'

const INPUT_CLASS =
  'w-full rounded-xl border border-[var(--input-border)] bg-[var(--input-bg)] px-4 py-3 text-[var(--main-text)] placeholder-[var(--main-text-muted)] transition-colors focus:border-[var(--accent)] focus:outline-none'

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const token = useMemo(() => searchParams.get('token')?.trim() ?? '', [searchParams])

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) return 'Password must be at least 8 characters'
    if (password.length > 64) return 'Password must be at most 64 characters'
    if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/\d/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      return 'Password must include uppercase, lowercase, digit, and special character'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')

    if (!token) {
      setError('Missing reset token in URL.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
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
      setError(err instanceof Error ? err.message : 'Reset failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title="Set a new password"
      subtitle="Use the one-time token from your reset email."
      leftTitle="Secure password reset"
      leftDescription="Reset is isolated as an explicit one-time operation with strict token checks."
    >
      {!token && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Invalid reset link. Please request a new one.
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {message && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
          {message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="newPassword" className="mb-2 block text-sm font-medium text-[var(--main-text)]">
            New password
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
            placeholder="8-64 chars with mixed complexity"
            disabled={isLoading || !token}
          />
        </div>

        <div>
          <label htmlFor="confirmPassword" className="mb-2 block text-sm font-medium text-[var(--main-text)]">
            Confirm password
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
            placeholder="Re-enter password"
            disabled={isLoading || !token}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !token}
          className="w-full rounded-xl bg-[var(--accent)] py-3 font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {isLoading ? 'Resetting...' : 'Reset password'}
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
