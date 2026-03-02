import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // 容器启动时传入 VITE_BASE_PATH=/video-previews/deepeye-video-xxx/，使 /node_modules/ 等请求也走预览路径
  base: process.env.VITE_BASE_PATH || './',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
