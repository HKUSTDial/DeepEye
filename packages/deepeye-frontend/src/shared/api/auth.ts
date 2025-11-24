/**
 * 认证 API
 * 
 * 对接后端认证接口：
 * - POST /api/v1/auth/register - 用户注册
 * - POST /api/v1/auth/login - 用户登录
 * - GET /api/v1/auth/me - 获取当前用户
 * - POST /api/v1/auth/password/change - 修改密码
 * - POST /api/v1/auth/password-reset/request - 请求重置密码
 * - POST /api/v1/auth/password-reset - 重置密码
 */

import { apiClient } from './client'

// ============ 类型定义 ============

export interface RegisterData {
  username: string
  email: string
  password: string
  full_name?: string
}

export interface LoginData {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserProfile {
  id: string
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  created_at: string
}

export interface PasswordChangeData {
  old_password: string
  new_password: string
}

export interface PasswordResetRequestData {
  email: string
}

export interface PasswordResetData {
  email: string
  code: string
  new_password: string
}

// ============ API 函数 ============

export const authAPI = {
  register: (d: RegisterData) => apiClient.post<UserProfile>('/auth/register', d),

  async login(d: LoginData) {
    const res = await apiClient.post<TokenResponse>('/auth/login', d)
    apiClient.setToken(res.access_token)
    return res
  },

  logout: () => apiClient.clearAuth(),
  getCurrentUser: () => apiClient.get<UserProfile>('/auth/me'),
  changePassword: (d: PasswordChangeData) => apiClient.post('/auth/password/change', d),
  requestPasswordReset: (d: PasswordResetRequestData) => apiClient.post('/auth/password-reset/request', d),
  resetPassword: (d: PasswordResetData) => apiClient.post('/auth/password-reset', d),
  isAuthenticated: () => apiClient.getToken() !== null,
}

