/**
 * 主题切换按钮
 * 用于在 Light 和 Dark 模式之间切换
 */

import { Moon, Sun } from 'lucide-react'
import { useThemeStore } from '@/store/themeStore'

interface ThemeToggleProps {
  className?: string
  showLabel?: boolean
}

export function ThemeToggle({ className = '', showLabel = false }: ThemeToggleProps) {
  const { theme, toggleTheme } = useThemeStore()

  return (
    <button
      onClick={toggleTheme}
      className={`flex items-center gap-2 rounded-lg p-2 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 ${className}`}
      title={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}
    >
      {theme === 'light' ? (
        <>
          <Moon size={20} className="text-gray-600 dark:text-gray-300" />
          {showLabel && <span className="text-sm text-gray-600 dark:text-gray-300">深色模式</span>}
        </>
      ) : (
        <>
          <Sun size={20} className="text-gray-300" />
          {showLabel && <span className="text-sm text-gray-300">浅色模式</span>}
        </>
      )}
    </button>
  )
}

