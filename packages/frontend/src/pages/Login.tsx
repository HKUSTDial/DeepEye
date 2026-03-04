/**
 * 登录页面
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'

export default function Login() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email, password)
      navigate('/')  // 登录成功，跳转到主页
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--main-bg)]">
      <div className="w-full max-w-md p-8 space-y-6 bg-[var(--main-bg-alt)] rounded-2xl border border-[var(--input-border)]">
        {/* Logo */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--main-text)]">DeepEye</h1>
          <p className="text-[var(--main-text-muted)] mt-2">Sign in to your account</p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* 登录表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-[var(--main-text)] mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--input-border)] rounded-xl text-[var(--main-text)] placeholder-[var(--main-text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              placeholder="you@example.com"
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-[var(--main-text)] mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 bg-[var(--input-bg)] border border-[var(--input-border)] rounded-xl text-[var(--main-text)] placeholder-[var(--main-text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              placeholder="••••••••"
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        {/* 注册链接 */}
        <div className="text-center text-sm text-[var(--main-text-muted)]">
          Don't have an account?{' '}
          <button
            onClick={() => navigate('/register')}
            className="text-[var(--accent)] hover:underline"
          >
            Create one
          </button>
        </div>
      </div>
    </div>
  )
}
