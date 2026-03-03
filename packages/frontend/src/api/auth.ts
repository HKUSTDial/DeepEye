/**
 * 认证相关 API
 */
import { authHttp } from './client'

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: {
    id: string
    email: string
    username: string
    is_superuser: boolean
  }
}

export const authApi = {
  /**
   * 用户登录
   */
  login: (data: LoginRequest) => {
    return authHttp.post<AuthResponse>('/login', data)
  },
  
  /**
   * 用户注册
   */
  register: (data: RegisterRequest) => {
    return authHttp.post<AuthResponse>('/register', data)
  },
  
  /**
   * 刷新 token
   */
  refresh: () => {
    return authHttp.post<{ access_token: string; token_type: string }>('/refresh')
  }
}

