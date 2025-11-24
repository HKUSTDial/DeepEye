/**
 * MainLayout - 主布局（左侧边栏 + 右侧内容区）
 */

import { Sidebar } from './Sidebar'

interface MainLayoutProps {
  currentPage: string
  onNavigate: (page: string) => void
  children: React.ReactNode
}

export function MainLayout({ currentPage, onNavigate, children }: MainLayoutProps) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* 左侧边栏 */}
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} />

      {/* 右侧内容区 */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {children}
      </div>
    </div>
  )
}

