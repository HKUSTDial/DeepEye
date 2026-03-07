/**
 * 认证 Store
 * 管理用户登录状态、token、用户信息
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { config } from '../config'

interface User {
  id: string
  email: string
  username: string
  is_superuser: boolean
  is_email_verified?: boolean
}

interface AuthState {
  // 状态
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  
  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  setAccessToken: (token: string) => void
  setUser: (user: User) => void
}

async function authRequest<T>(path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const res = await fetch(`${config.api.authBaseUrl}${path}`, {
    method: 'POST',
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })

  if (!res.ok) {
    let message = `Request failed: ${res.statusText}`
    try {
      const errorData = await res.json()
      if (typeof errorData?.detail === 'string') {
        message = errorData.detail
      } else if (typeof errorData?.message === 'string') {
        message = errorData.message
      }
    } catch {
      // ignore parse error
    }
    throw new Error(message)
  }

  return res.status === 204 ? (undefined as T) : res.json()
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      accessToken: null,
      user: null,
      isAuthenticated: false,
      
      // 登录
      login: async (email: string, password: string) => {
        try {
          const response = await authRequest<{
            access_token: string
            user: User
          }>('/login', { email, password })
          
          set({
            accessToken: response.access_token,
            user: response.user,
            isAuthenticated: true
          })
        } catch (error) {
          console.error('[Auth] Login failed:', error)
          throw error
        }
      },
      
      // 注册
      register: async (email: string, username: string, password: string) => {
        try {
          const response = await authRequest<{
            access_token: string
            user: User
          }>('/register', { email, username, password })
          
          set({
            accessToken: response.access_token,
            user: response.user,
            isAuthenticated: true
          })
        } catch (error) {
          console.error('[Auth] Register failed:', error)
          throw error
        }
      },
      
      // 登出
      logout: () => {
        void authRequest<void>('/logout').catch((error) => {
          console.warn('[Auth] Logout request failed:', error)
        })

        set({
          accessToken: null,
          user: null,
          isAuthenticated: false
        })
        
        // 清除持久化数据
        localStorage.removeItem('auth-storage')
      },
      
      // 刷新 token
      refreshToken: async () => {
        try {
          // 通过 HttpOnly refresh cookie 刷新
          const response = await authRequest<{
            access_token: string
          }>('/refresh')
          
          set({ accessToken: response.access_token, isAuthenticated: true })
        } catch (error) {
          console.error('[Auth] Token refresh failed:', error)
          // 刷新失败，清除状态
          get().logout()
          throw error
        }
      },
      
      // 设置 token
      setAccessToken: (token: string) => {
        set({ accessToken: token })
      },
      
      // 设置用户信息
      setUser: (user: User) => {
        set({ user, isAuthenticated: true })
      }
    }),
    {
      name: 'auth-storage',
      // 仅持久化身份态，不持久化 access token
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated
      }),
    }
  )
)

if (typeof window !== 'undefined') {
  const state = useAuthStore.getState()
  if (state.isAuthenticated) {
    void state.refreshToken().catch(() => {
      // ignore: refreshToken 内部会执行 logout
    })
  }
}
