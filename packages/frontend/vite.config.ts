import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

function manualChunks(id: string) {
  if (!id.includes('node_modules')) {
    return undefined
  }

  if (id.includes('reactflow')) {
    return 'workflow-vendor'
  }
  if (id.includes('framer-motion')) {
    return 'motion-vendor'
  }
  if (
    id.includes('@babel/standalone') ||
    id.includes('/remotion/') ||
    id.includes('/d3/')
  ) {
    return 'video-vendor'
  }
  if (id.includes('/xlsx/')) {
    return 'file-vendor'
  }
  if (
    id.includes('/@shikijs/core/') ||
    id.includes('/engine-javascript.mjs') ||
    id.includes('/shiki/dist/core') ||
    id.includes('/shiki/dist/engine-javascript')
  ) {
    return 'highlight-core'
  }
  if (
    id.includes('/react-markdown/') ||
    id.includes('/remark-gfm/') ||
    id.includes('/rehype-raw/')
  ) {
    return 'content-vendor'
  }
  if (
    id.includes('/react/') ||
    id.includes('/react-dom/') ||
    id.includes('/react-router-dom/')
  ) {
    return 'react-vendor'
  }

  return undefined
}

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    // 包含 @babel/standalone，让 Vite 预构建它，以便浏览器中的动态 import 能正常工作
    include: ['@babel/standalone'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    clearMocks: true,
    restoreMocks: true,
  },
})
