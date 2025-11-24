/**
 * 认证状态管理
 * 
 * 管理用户登录状态、用户信息等
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authAPI, UserProfile, LoginData, RegisterData } from '@/shared/api'

interface AuthStore {
  // 状态
  user: UserProfile | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // 操作
  login: (data: LoginData) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  fetchCurrentUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      // 初始状态
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // 登录
      login: async (data: LoginData) => {
        set({ isLoading: true, error: null })
        
        try {
          // 调用登录 API
          await authAPI.login(data)
          
          // 获取用户信息
          const user = await authAPI.getCurrentUser()
          
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '登录失败',
            isLoading: false,
          })
          throw error
        }
      },

      // 注册
      register: async (data: RegisterData) => {
        set({ isLoading: true, error: null })
        
        try {
          // 调用注册 API
          const user = await authAPI.register(data)
          
          // 注册成功后自动登录
          await authAPI.login({
            username: data.username,
            password: data.password,
          })
          
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '注册失败',
            isLoading: false,
          })
          throw error
        }
      },

      // 登出
      logout: () => {
        authAPI.logout()
        set({
          user: null,
          isAuthenticated: false,
          error: null,
        })
      },

      // 获取当前用户信息
      fetchCurrentUser: async () => {
        // 检查是否有 Token
        if (!authAPI.isAuthenticated()) {
          set({ isAuthenticated: false, user: null })
          return
        }

        set({ isLoading: true, error: null })
        
        try {
          const user = await authAPI.getCurrentUser()
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          // Token 可能已过期
          authAPI.logout()
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: error instanceof Error ? error.message : '获取用户信息失败',
          })
        }
      },

      // 清除错误
      clearError: () => {
        set({ error: null })
      },
    }),
    {
      name: 'auth-storage',
      // 只持久化用户信息和认证状态
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

