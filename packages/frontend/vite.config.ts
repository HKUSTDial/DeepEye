import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // 包含 @babel/standalone，让 Vite 预构建它，以便浏览器中的动态 import 能正常工作
    include: ['@babel/standalone'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    clearMocks: true,
    restoreMocks: true,
  },
})
