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
  KnowledgeBaseDetail,
  KnowledgeBases,
  Login,
  Register,
  ResetPassword,
  VerifyEmail,
  WorkflowsNew,
} from './pages'
import ProtectedRoute from './components/ProtectedRoute'
import { initTheme } from './hooks/useTheme'

initTheme()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route
          path="/workflows"
          element={
            <ProtectedRoute>
              <WorkflowsNew />
            </ProtectedRoute>
          }
        />
        <Route
          path="/knowledge-bases"
          element={
            <ProtectedRoute>
              <KnowledgeBases />
            </ProtectedRoute>
          }
        />
        <Route
          path="/knowledge-bases/:kbId"
          element={
            <ProtectedRoute>
              <KnowledgeBaseDetail />
            </ProtectedRoute>
          }
        />
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
  </StrictMode>,
)
