/**
 * 上下文菜单组件
 * 支持画布、节点、边的右键菜单
 */

import { useEffect, useRef } from 'react'
import { cn } from '@/shared/utils'
import { LucideIcon } from 'lucide-react'

// ============ 类型定义 ============

export interface MenuItem {
  id: string
  label: string
  icon?: LucideIcon
  shortcut?: string
  disabled?: boolean
  danger?: boolean
  divider?: boolean
  onClick?: () => void
}

export interface MenuSection {
  title?: string
  items: MenuItem[]
}

export interface ContextMenuProps {
  x: number
  y: number
  sections: MenuSection[]
  onClose: () => void
}

// ============ 组件 ============

export function ContextMenu({ x, y, sections, onClose }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)

  // ============ 处理点击外部关闭 ============
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    // 延迟绑定，避免立即触发
    setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleEscape)
    }, 0)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [onClose])

  // ============ 计算菜单位置（防止溢出） ============
  const menuStyle = {
    left: x,
    top: y,
  }

  useEffect(() => {
    if (!menuRef.current) return

    const rect = menuRef.current.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight

    // 调整水平位置
    if (rect.right > viewportWidth) {
      menuRef.current.style.left = `${viewportWidth - rect.width - 10}px`
    }

    // 调整垂直位置
    if (rect.bottom > viewportHeight) {
      menuRef.current.style.top = `${viewportHeight - rect.height - 10}px`
    }
  }, [])

  return (
    <>
      {/* 半透明遮罩 */}
      <div className="fixed inset-0 z-[100]" onClick={onClose} />

      {/* 菜单 */}
      <div
        ref={menuRef}
        className={cn(
          "fixed z-[101]",
          "min-w-[200px] max-w-[280px]",
          "bg-background border border-border",
          "rounded-lg shadow-2xl",
          "py-1.5",
          "animate-in fade-in-0 zoom-in-95 duration-100"
        )}
        style={menuStyle}
      >
        {sections.map((section, sectionIndex) => (
          <div key={sectionIndex}>
            {/* 分组标题 */}
            {section.title && (
              <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {section.title}
              </div>
            )}

            {/* 菜单项 */}
            {section.items.map((item) => {
              if (item.divider) {
                return (
                  <div
                    key={item.id}
                    className="my-1.5 h-px bg-border"
                  />
                )
              }

              return (
                <button
                  key={item.id}
                  onClick={() => {
                    if (!item.disabled && item.onClick) {
                      item.onClick()
                      onClose()
                    }
                  }}
                  disabled={item.disabled}
                  className={cn(
                    "w-full px-3 py-2",
                    "flex items-center gap-3",
                    "text-sm text-left",
                    "transition-colors",
                    !item.disabled && "hover:bg-muted cursor-pointer",
                    item.disabled && "opacity-50 cursor-not-allowed",
                    item.danger && !item.disabled && "text-destructive hover:bg-destructive/10"
                  )}
                >
                  {/* 图标 */}
                  {item.icon && (
                    <item.icon className="w-4 h-4 flex-shrink-0" strokeWidth={2} />
                  )}

                  {/* 标签 */}
                  <span className="flex-1">{item.label}</span>

                  {/* 快捷键 */}
                  {item.shortcut && (
                    <span className="text-xs text-muted-foreground font-mono">
                      {item.shortcut}
                    </span>
                  )}
                </button>
              )
            })}

            {/* 分组分隔线 */}
            {sectionIndex < sections.length - 1 && (
              <div className="my-1.5 h-px bg-border" />
            )}
          </div>
        ))}
      </div>
    </>
  )
}

