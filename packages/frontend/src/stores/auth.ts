/**
 * 认证 Store
 * 管理用户登录状态、token、用户信息
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authHttp } from '../api/client'

interface User {
  id: string
  email: string
  username: string
  is_superuser: boolean
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
          const response = await authHttp.post<{
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
          const response = await authHttp.post<{
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
          const currentToken = get().accessToken
          if (!currentToken) {
            throw new Error('No token to refresh')
          }
          
          // 使用当前 token 刷新（后端会验证并返回新 token）
          const response = await authHttp.post<{
            access_token: string
          }>('/refresh')
          
          set({ accessToken: response.access_token })
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
      // 持久化用户信息和 access token，避免刷新后退回登录页
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)

