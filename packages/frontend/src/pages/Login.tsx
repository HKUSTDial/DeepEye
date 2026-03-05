/**
 * 兼容旧路由：重定向到统一 Auth 页面
 */
import { Navigate, useSearchParams } from 'react-router-dom'

export default function Login() {
  const [searchParams] = useSearchParams()
  const suffix = searchParams.toString()
  return <Navigate to={suffix ? `/auth?${suffix}` : '/auth'} replace />
}
