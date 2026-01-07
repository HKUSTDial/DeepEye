import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import './styles/light-theme.css'
import './styles/dark-theme.css'
import App from './App'
import { Login, Register, WorkflowsNew, KnowledgeBases, KnowledgeBaseDetail } from './pages'
import ProtectedRoute from './components/ProtectedRoute'

// Apply theme from localStorage or default to light
const savedTheme = localStorage.getItem('theme') || 'light'
document.body.classList.add(savedTheme === 'light' ? 'light-theme' : 'dark-theme')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
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
