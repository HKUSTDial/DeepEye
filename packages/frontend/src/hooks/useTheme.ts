import { useSyncExternalStore } from 'react'

type Theme = 'light' | 'dark'

const THEME_KEY = 'theme'
const listeners = new Set<() => void>()

let currentTheme: Theme = 'light'

const applyTheme = (theme: Theme) => {
  const root = document.body
  if (theme === 'light') {
    root.classList.add('light-theme')
    root.classList.remove('dark-theme')
  } else {
    root.classList.add('dark-theme')
    root.classList.remove('light-theme')
  }
  localStorage.setItem(THEME_KEY, theme)
}

export const initTheme = () => {
  const saved = localStorage.getItem(THEME_KEY) as Theme | null
  currentTheme = saved || 'light'
  applyTheme(currentTheme)
  return currentTheme
}

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

const getSnapshot = () => currentTheme

const setTheme = (next: Theme) => {
  if (next === currentTheme) return
  currentTheme = next
  applyTheme(currentTheme)
  listeners.forEach((listener) => listener())
}

const toggleTheme = () => {
  setTheme(currentTheme === 'light' ? 'dark' : 'light')
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)

  return { theme, toggleTheme, setTheme }
}

