/**
 * 路由守卫组件
 * 保护需要登录才能访问的路由
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    // 未登录，重定向到登录页并附带回跳地址
    const next = `${location.pathname}${location.search}`
    return <Navigate to={`/auth?next=${encodeURIComponent(next)}`} replace />
  }

  return <>{children}</>
}
