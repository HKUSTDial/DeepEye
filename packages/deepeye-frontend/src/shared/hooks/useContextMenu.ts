/**
 * 上下文菜单 Hook
 * 管理右键菜单的显示、隐藏和位置
 */

import { useState, useCallback, MouseEvent as ReactMouseEvent } from 'react'

export interface ContextMenuState {
  visible: boolean
  x: number
  y: number
  data?: any // 菜单相关的数据（如节点 ID、边 ID 等）
}

export interface UseContextMenuReturn {
  menuState: ContextMenuState
  showMenu: (event: ReactMouseEvent, data?: any) => void
  hideMenu: () => void
}

/**
 * 上下文菜单 Hook
 * 
 * @example
 * const { menuState, showMenu, hideMenu } = useContextMenu()
 * 
 * <div onContextMenu={(e) => showMenu(e, { type: 'canvas' })}>
 *   ...
 * </div>
 * 
 * {menuState.visible && (
 *   <ContextMenu
 *     x={menuState.x}
 *     y={menuState.y}
 *     sections={sections}
 *     onClose={hideMenu}
 *   />
 * )}
 */
export function useContextMenu(): UseContextMenuReturn {
  const [menuState, setMenuState] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    data: null,
  })

  /**
   * 显示菜单
   */
  const showMenu = useCallback((event: ReactMouseEvent, data?: any) => {
    event.preventDefault()
    event.stopPropagation()

    setMenuState({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      data,
    })

    if (import.meta.env.DEV) {
      console.log('🖱️ Context menu opened:', {
        x: event.clientX,
        y: event.clientY,
        data,
      })
    }
  }, [])

  /**
   * 隐藏菜单
   */
  const hideMenu = useCallback(() => {
    setMenuState((prev) => ({
      ...prev,
      visible: false,
    }))

    if (import.meta.env.DEV) {
      console.log('🖱️ Context menu closed')
    }
  }, [])

  return {
    menuState,
    showMenu,
    hideMenu,
  }
}

