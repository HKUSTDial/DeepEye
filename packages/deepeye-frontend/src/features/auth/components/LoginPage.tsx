/**
 * LoginPage - 登录页面
 */

import { useState } from 'react'
import { useAuthStore, toast } from '@/store'
import { Eye, EyeOff, Loader2 } from 'lucide-react'

interface LoginPageProps {
  onLoginSuccess: () => void
}

export function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const [isLogin, setIsLogin] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
  })

  const { login, register, isLoading, error, clearError } = useAuthStore()

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) {
      return '密码至少需要8个字符'
    }
    if (!/[A-Z]/.test(password)) {
      return '密码必须包含至少一个大写字母'
    }
    if (!/[a-z]/.test(password)) {
      return '密码必须包含至少一个小写字母'
    }
    if (!/[0-9]/.test(password)) {
      return '密码必须包含至少一个数字'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    // 注册时验证密码强度
    if (!isLogin) {
      const passwordError = validatePassword(formData.password)
      if (passwordError) {
        toast.error(passwordError)
        return
      }
    }

    try {
      if (isLogin) {
        await login({
          username: formData.username,
          password: formData.password,
        })
        toast.success('登录成功')
      } else {
        await register({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name || undefined,
        })
        toast.success('注册成功')
      }
      onLoginSuccess()
    } catch (err) {
      console.error('认证失败:', err)
      // authStore 已经设置了 error，这里不需要再显示 toast
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary/5 to-primary/10">
      <div className="w-full max-w-md space-y-8 rounded-2xl bg-card p-8 shadow-2xl">
        {/* Logo 和标题 */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-card-foreground">
            DeepEye
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            AI 驱动的数据分析与可视化平台
          </p>
        </div>

        {/* 切换登录/注册 */}
        <div className="flex rounded-lg bg-secondary p-1">
          <button
            type="button"
            onClick={() => setIsLogin(true)}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
              isLogin
                ? 'bg-background text-foreground shadow'
                : 'text-muted-foreground'
            }`}
          >
            登录
          </button>
          <button
            type="button"
            onClick={() => setIsLogin(false)}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
              !isLogin
                ? 'bg-background text-foreground shadow'
                : 'text-muted-foreground'
            }`}
          >
            注册
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 用户名或邮箱 */}
          <div>
            <label className="block text-sm font-medium text-foreground">
              {isLogin ? '用户名或邮箱' : '用户名'}
            </label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder={isLogin ? '请输入用户名或邮箱' : '请输入用户名'}
            />
          </div>

          {/* 邮箱（仅注册） */}
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-foreground">
                邮箱
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="请输入邮箱"
              />
            </div>
          )}

          {/* 全名（仅注册，可选） */}
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-foreground">
                全名（可选）
              </label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className="mt-1 block w-full rounded-lg border bg-background px-3 py-2 text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="请输入全名"
              />
            </div>
          )}

          {/* 密码 */}
          <div>
            <label className="block text-sm font-medium text-foreground">
              密码
            </label>
            <div className="relative mt-1">
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                minLength={8}
                className="block w-full rounded-lg border bg-background px-3 py-2 pr-10 text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="请输入密码"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            {!isLogin && (
              <p className="mt-1 text-xs text-muted-foreground">
                密码要求：至少8位，包含大小写字母和数字
              </p>
            )}
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            disabled={isLoading}
            className="flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isLogin ? '登录中...' : '注册中...'}
              </>
            ) : (
              <>{isLogin ? '登录' : '注册'}</>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}

