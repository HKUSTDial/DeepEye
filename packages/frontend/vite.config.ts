import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // 包含 @babel/standalone，让 Vite 预构建它，以便浏览器中的动态 import 能正常工作
    include: ['@babel/standalone'],
  },
})
