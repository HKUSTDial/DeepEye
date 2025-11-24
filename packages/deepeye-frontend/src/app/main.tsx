// Reflect metadata polyfill (必须在最前面)
import '@/nodes/polyfills/reflect-metadata'

// 导入所有节点定义（触发装饰器注册）
import '@/nodes/definitions'

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import '@/shared/styles/globals.css'

// 初始化主题
import { initTheme } from '@/store/themeStore'
initTheme()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

