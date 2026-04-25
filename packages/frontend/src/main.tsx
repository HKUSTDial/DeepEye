import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import './styles/light-theme.css'
import './styles/dark-theme.css'
import App from './App'
import {
  Auth,
  ForgotPassword,
  Login,
  Register,
  ResetPassword,
  VerifyEmail,
} from './pages'
import ProtectedRoute from './components/ProtectedRoute'
import { initTheme } from './hooks/useTheme'
import { clearVideoCache } from './api/videoRegistration'
import { LocaleProvider } from './locale/LocaleProvider'

initTheme()

// 开发调试用：控制台执行 clearVideoCache() 可清除视频组件缓存，强制重新拉取 TSX
if (typeof window !== 'undefined') {
  ;(window as unknown as { clearVideoCache?: typeof clearVideoCache }).clearVideoCache = clearVideoCache
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LocaleProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <App />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </LocaleProvider>
  </StrictMode>,
)
