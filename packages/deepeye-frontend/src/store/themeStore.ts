/**
 * 主题状态管理
 * 使用 Zustand 管理 dark/light 模式
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ThemeMode = 'light' | 'dark'

interface ThemeStore {
  theme: ThemeMode
  toggleTheme: () => void
  setTheme: (theme: ThemeMode) => void
}

/**
 * 应用主题到 DOM
 */
function applyTheme(theme: ThemeMode) {
  const root = document.documentElement

  if (theme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'light',

      toggleTheme: () => {
        set((state) => {
          const newTheme = state.theme === 'light' ? 'dark' : 'light'
          applyTheme(newTheme)
          return { theme: newTheme }
        })
      },

      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },
    }),
    {
      name: 'deepeye-theme',
      onRehydrateStorage: () => (state) => {
        // 恢复主题时应用到 DOM
        if (state) {
          applyTheme(state.theme)
        }
      },
    }
  )
)

/**
 * 初始化主题
 * 在应用启动时调用
 */
export function initTheme() {
  const state = useThemeStore.getState()
  applyTheme(state.theme)
}

