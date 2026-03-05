/**
 * 注册页面
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AuthShell from '../components/auth/AuthShell'
import { useAuthStore } from '../stores/auth'

const INPUT_CLASS =
  'w-full rounded-xl border border-[var(--input-border)] bg-[var(--input-bg)] px-4 py-3 text-[var(--main-text)] placeholder-[var(--main-text-muted)] transition-colors focus:border-[var(--accent)] focus:outline-none'

export default function Register() {
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
      setError('Passwords do not match')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    if (password.length > 64) {
      setError('Password must be at most 64 characters')
      return
    }

    if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/\d/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      setError('Password must include uppercase, lowercase, digit, and special character')
      return
    }

    setIsLoading(true)

    try {
      await register(email, username, password)
      navigate(`/verify-email?email=${encodeURIComponent(email)}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthShell
      title="Create account"
      subtitle="Set up your DeepEye account in one minute."
      leftTitle="Build your workspace identity"
      leftDescription="Keep authentication and verification as focused, independent steps."
    >
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
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
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="username" className="mb-2 block text-sm font-medium text-[var(--main-text)]">
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={2}
            className={INPUT_CLASS}
            placeholder="johndoe"
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-2 block text-sm font-medium text-[var(--main-text)]">
            Password
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
            placeholder="8-64 chars with mixed complexity"
            disabled={isLoading}
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
            placeholder="Re-enter your password"
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-xl bg-[var(--accent)] py-3 font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-55"
        >
          {isLoading ? 'Creating account...' : 'Register'}
        </button>
      </form>

      <div className="text-sm text-[var(--main-text-muted)]">
        Already have an account?{' '}
        <button onClick={() => navigate('/auth')} className="text-[var(--accent)] hover:underline">
          Sign in
        </button>
      </div>
    </AuthShell>
  )
}
