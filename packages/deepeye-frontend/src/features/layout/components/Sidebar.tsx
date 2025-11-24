/**
 * Sidebar - 左侧导航栏
 */

import { useState } from 'react'
import { Workflow, Settings, LogOut, ChevronLeft, ChevronRight, LucideIcon } from 'lucide-react'
import { useAuthStore } from '@/store'

interface SidebarProps {
  currentPage: string
  onNavigate: (page: string) => void
}

interface NavItem {
  id: string
  icon: LucideIcon
  label: string
  tooltip: string
}

const navItems: NavItem[] = [
  {
    id: 'workflows',
    icon: Workflow,
    label: '工作流',
    tooltip: '工作流管理',
  },
  {
    id: 'settings',
    icon: Settings,
    label: '设置',
    tooltip: '系统设置',
  },
]

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const { user, logout } = useAuthStore()
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div
      className={`flex h-screen flex-col border-r border bg-card transition-all duration-300 ease-in-out ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* 顶部：Logo 和折叠按钮 */}
      <div className="flex h-16 items-center justify-between border-b border px-4">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            D
          </div>
          <span
            className={`whitespace-nowrap text-lg font-semibold text-card-foreground transition-all duration-300 ${
              isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'
            }`}
          >
            DeepEye
          </span>
        </div>
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex-shrink-0 rounded-lg p-1.5 hover:bg-secondary"
          title={isCollapsed ? '展开侧边栏' : '折叠侧边栏'}
        >
          {isCollapsed ? (
            <ChevronRight size={20} className="text-muted-foreground" />
          ) : (
            <ChevronLeft size={20} className="text-muted-foreground" />
          )}
        </button>
      </div>

      {/* 中间：导航菜单 */}
      <nav className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = currentPage === item.id

            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`flex w-full items-center gap-3 overflow-hidden rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-foreground hover:bg-secondary'
                }`}
                title={isCollapsed ? item.tooltip : undefined}
              >
                <Icon size={20} className="flex-shrink-0" />
                <span
                  className={`whitespace-nowrap transition-all duration-300 ${
                    isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'
                  }`}
                >
                  {item.label}
                </span>
              </button>
            )
          })}
        </div>
      </nav>

      {/* 底部：用户信息和退出 */}
      <div className="border-t border p-2">
        {/* 用户信息 */}
        {user && !isCollapsed && (
          <div className="mb-2 animate-in fade-in slide-in-from-left-2 overflow-hidden rounded-lg bg-secondary p-3 duration-300">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                {user.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="truncate text-sm font-medium text-foreground">
                  {user.username}
                </p>
                <p className="truncate text-xs text-muted-foreground">{user.email}</p>
              </div>
            </div>
          </div>
        )}

        {/* 退出按钮 */}
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 overflow-hidden rounded-lg px-3 py-2.5 text-sm font-medium text-destructive hover:bg-destructive/10"
          title={isCollapsed ? '退出登录' : undefined}
        >
          <LogOut size={20} className="flex-shrink-0" />
          <span
            className={`whitespace-nowrap transition-all duration-300 ${
              isCollapsed ? 'w-0 opacity-0' : 'w-auto opacity-100'
            }`}
          >
            退出登录
          </span>
        </button>
      </div>
    </div>
  )
}

