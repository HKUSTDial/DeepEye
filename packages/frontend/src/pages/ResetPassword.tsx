/**
 * 重置密码页面
 */
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { authApi } from '../api/auth'

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
    <div className="min-h-screen flex items-center justify-center bg-[var(--main-bg)] px-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-[var(--main-bg-alt)] rounded-2xl border border-[var(--input-border)]">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--main-text)]">DeepEye</h1>
          <p className="text-[var(--main-text-muted)] mt-2">Set a new password</p>
        </div>

        {!token && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            Invalid reset link. Please request a new one.
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {message && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="newPassword" className="block text-sm font-medium text-[var(--main-text)] mb-2">
              New Password
            </label>
            <input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              maxLength={64}
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--input-border)] rounded-xl text-[var(--main-text)] placeholder-[var(--main-text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              placeholder="8-64 chars with mixed complexity"
              disabled={isLoading || !token}
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-[var(--main-text)] mb-2">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              maxLength={64}
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--input-border)] rounded-xl text-[var(--main-text)] placeholder-[var(--main-text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              placeholder="Re-enter password"
              disabled={isLoading || !token}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !token}
            className="w-full py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Resetting...' : 'Reset password'}
          </button>
        </form>

        <div className="text-center text-sm text-[var(--main-text-muted)]">
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
