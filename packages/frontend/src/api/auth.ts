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
    is_email_verified: boolean
  }
}

export interface GenericMessageResponse {
  message: string
  debug_token?: string | null
}

export interface VerifyEmailRequest {
  email: string
}

export interface VerifyEmailConfirmRequest {
  token: string
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirmRequest {
  token: string
  new_password: string
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
  },

  logout: () => {
    return authHttp.post<void>('/logout')
  },

  requestEmailVerification: (data: VerifyEmailRequest) => {
    return authHttp.post<GenericMessageResponse>('/verify-email/request', data)
  },

  confirmEmailVerification: (data: VerifyEmailConfirmRequest) => {
    return authHttp.post<GenericMessageResponse>('/verify-email/confirm', data)
  },

  requestPasswordReset: (data: PasswordResetRequest) => {
    return authHttp.post<GenericMessageResponse>('/password-reset/request', data)
  },

  confirmPasswordReset: (data: PasswordResetConfirmRequest) => {
    return authHttp.post<GenericMessageResponse>('/password-reset/confirm', data)
  }
}
