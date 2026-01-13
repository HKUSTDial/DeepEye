/**
 * 路由守卫组件
 * 保护需要登录才能访问的路由
 */
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    // 未登录，重定向到登录页
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

