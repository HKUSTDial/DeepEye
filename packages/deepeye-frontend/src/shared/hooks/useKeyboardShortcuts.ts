/**
 * 键盘快捷键系统
 * 提供全局的键盘快捷键支持
 */

import { useEffect } from 'react'
import { useGraphStore } from '@/store'

/**
 * 检测是否为 Mac 系统
 */
const isMac = typeof navigator !== 'undefined' && 
              navigator.platform.toUpperCase().indexOf('MAC') >= 0

/**
 * 键盘快捷键 Hook
 * 
 * 支持的快捷键：
 * - Ctrl/Cmd + Z: 撤销
 * - Ctrl/Cmd + Shift + Z: 重做
 * - Ctrl/Cmd + Y: 重做（Windows 风格）
 * - Ctrl/Cmd + S: 保存（TODO）
 * - Delete/Backspace: 删除选中节点
 * - Escape: 清除选择
 * - Ctrl/Cmd + A: 全选（TODO）
 */
export function useKeyboardShortcuts() {
  const { 
    undo, 
    redo, 
    canUndo, 
    canRedo, 
    selectedNodes, 
    removeNode, 
    clearSelection,
    copyNodes,
    cutNodes,
    pasteNodes,
    selectAll,
    duplicateNodes,
  } = useGraphStore()

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 获取修饰键（Mac 用 Cmd，Windows/Linux 用 Ctrl）
      const modifier = isMac ? e.metaKey : e.ctrlKey

      // 忽略在输入框中的快捷键
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // 在输入框中，只允许某些快捷键
        if (modifier && e.key === 's') {
          e.preventDefault()
          // TODO: 实现保存
          console.log('💾 Save shortcut triggered (in input)')
        }
        return
      }

      // ============ 撤销 (Ctrl/Cmd + Z) ============
      if (modifier && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        if (canUndo()) {
          e.preventDefault()
          undo()
          
          if (import.meta.env.DEV) {
            console.log('⌨️ Undo triggered by keyboard')
          }
        }
        return
      }

      // ============ 重做 (Ctrl/Cmd + Shift + Z) ============
      if (modifier && e.key.toLowerCase() === 'z' && e.shiftKey) {
        if (canRedo()) {
          e.preventDefault()
          redo()
          
          if (import.meta.env.DEV) {
            console.log('⌨️ Redo triggered by keyboard (Shift+Z)')
          }
        }
        return
      }

      // ============ 重做 (Ctrl/Cmd + Y) - Windows 风格 ============
      if (modifier && e.key.toLowerCase() === 'y') {
        if (canRedo()) {
          e.preventDefault()
          redo()
          
          if (import.meta.env.DEV) {
            console.log('⌨️ Redo triggered by keyboard (Y)')
          }
        }
        return
      }

      // ============ 保存 (Ctrl/Cmd + S) ============
      if (modifier && e.key.toLowerCase() === 's') {
        e.preventDefault()
        // TODO: 实现保存功能
        console.log('💾 Save shortcut triggered')
        return
      }

      // ============ 删除选中节点 (Delete/Backspace) ============
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNodes.length > 0) {
          e.preventDefault()
          selectedNodes.forEach((id) => {
            removeNode(id)
          })
          
          if (import.meta.env.DEV) {
            console.log('⌨️ Delete nodes:', selectedNodes.length)
          }
        }
        return
      }

      // ============ 清除选择 (Escape) ============
      if (e.key === 'Escape') {
        clearSelection()
        
        if (import.meta.env.DEV) {
          console.log('⌨️ Clear selection')
        }
        return
      }

      // ============ 全选 (Ctrl/Cmd + A) ============
      if (modifier && e.key.toLowerCase() === 'a') {
        e.preventDefault()
        selectAll()
        
        if (import.meta.env.DEV) {
          console.log('⌨️ Select all')
        }
        return
      }

      // ============ 复制 (Ctrl/Cmd + C) ============
      if (modifier && e.key.toLowerCase() === 'c') {
        if (selectedNodes.length > 0) {
          e.preventDefault()
          copyNodes(selectedNodes)
          
          if (import.meta.env.DEV) {
            console.log('⌨️ Copy nodes:', selectedNodes.length)
          }
        }
        return
      }

      // ============ 剪切 (Ctrl/Cmd + X) ============
      if (modifier && e.key.toLowerCase() === 'x') {
        if (selectedNodes.length > 0) {
          e.preventDefault()
          cutNodes(selectedNodes)
          
          if (import.meta.env.DEV) {
            console.log('⌨️ Cut nodes:', selectedNodes.length)
          }
        }
        return
      }

      // ============ 粘贴 (Ctrl/Cmd + V) ============
      if (modifier && e.key.toLowerCase() === 'v') {
        e.preventDefault()
        pasteNodes()
        
        if (import.meta.env.DEV) {
          console.log('⌨️ Paste nodes')
        }
        return
      }

      // ============ 复制节点 (Ctrl/Cmd + D) ============
      if (modifier && e.key.toLowerCase() === 'd') {
        if (selectedNodes.length > 0) {
          e.preventDefault()
          duplicateNodes(selectedNodes)
          
          if (import.meta.env.DEV) {
            console.log('⌨️ Duplicate nodes:', selectedNodes.length)
          }
        }
        return
      }
    }

    // 绑定事件
    window.addEventListener('keydown', handleKeyDown)

    // 清理
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [undo, redo, canUndo, canRedo, selectedNodes, removeNode, clearSelection, copyNodes, cutNodes, pasteNodes, selectAll, duplicateNodes])

  // 提供快捷键信息（可用于显示帮助）
  return {
    shortcuts: [
      { key: `${isMac ? '⌘' : 'Ctrl'}+Z`, description: 'Undo' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+Shift+Z`, description: 'Redo' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+Y`, description: 'Redo (alternative)' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+S`, description: 'Save (coming soon)' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+A`, description: 'Select all' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+C`, description: 'Copy' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+X`, description: 'Cut' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+V`, description: 'Paste' },
      { key: `${isMac ? '⌘' : 'Ctrl'}+D`, description: 'Duplicate' },
      { key: 'Delete/Backspace', description: 'Delete selected nodes' },
      { key: 'Escape', description: 'Clear selection' },
    ],
  }
}

