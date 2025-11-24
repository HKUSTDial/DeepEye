/**
 * Router - 简单的路由管理器
 * 
 * 使用状态管理实现简单的路由功能，无需额外依赖
 */

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/store'
import { LoginPage } from '@/features/auth'
import { WorkflowListPage } from '@/features/workflows'
import { WorkflowEditor } from '@/features/editor'
import { MainLayout } from '@/features/layout'

type Route =
  | { type: 'login' }
  | { type: 'workflows' }
  | { type: 'settings' }
  | { type: 'editor'; workflowId?: string }

export function Router() {
  const { isAuthenticated, fetchCurrentUser } = useAuthStore()
  const [route, setRoute] = useState<Route>({ type: 'login' })
  const [isInitializing, setIsInitializing] = useState(true)

  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = async () => {
    try {
      await fetchCurrentUser()
      if (isAuthenticated) {
        setRoute({ type: 'workflows' })
      }
    } catch (error) {
      console.error('初始化认证失败:', error)
    } finally {
      setIsInitializing(false)
    }
  }

  const handleLoginSuccess = () => {
    setRoute({ type: 'workflows' })
  }

  const handleOpenWorkflow = (workflowId: string) => {
    setRoute({ type: 'editor', workflowId })
  }

  const handleBackToList = () => {
    setRoute({ type: 'workflows' })
  }

  const handleNavigate = (page: string) => {
    if (page === 'workflows') {
      setRoute({ type: 'workflows' })
    } else if (page === 'settings') {
      setRoute({ type: 'settings' })
    }
  }

  if (isInitializing) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="mb-4 text-4xl font-bold text-gray-900 dark:text-white">
            DeepEye
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            正在加载...
          </div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />
  }

  // 编辑器页面不使用主布局
  if (route.type === 'editor') {
    return (
      <WorkflowEditor
        workflowId={route.workflowId}
        onBack={handleBackToList}
      />
    )
  }

  // 其他页面使用主布局（侧边栏 + 内容区）
  return (
    <MainLayout currentPage={route.type} onNavigate={handleNavigate}>
      {route.type === 'workflows' && (
        <WorkflowListPage onOpenWorkflow={handleOpenWorkflow} />
      )}

      {route.type === 'settings' && (
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">设置</h1>
            <p className="mt-2 text-gray-600 dark:text-gray-400">功能开发中...</p>
          </div>
        </div>
      )}
    </MainLayout>
  )
}

