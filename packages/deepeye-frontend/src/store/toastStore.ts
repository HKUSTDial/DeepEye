/**
 * Toast Store - 通知状态管理
 */

import { create } from 'zustand'
import type { ToastType } from '@/shared/components/Toast'

export interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

interface ToastStore {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
  success: (message: string, duration?: number) => void
  error: (message: string, duration?: number) => void
  warning: (message: string, duration?: number) => void
  info: (message: string, duration?: number) => void
}

let toastIdCounter = 0

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `toast-${++toastIdCounter}`
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }))
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },

  success: (message, duration = 3000) => {
    const id = `toast-${++toastIdCounter}`
    set((state) => ({
      toasts: [...state.toasts, { id, type: 'success', message, duration }],
    }))
  },

  error: (message, duration = 4000) => {
    const id = `toast-${++toastIdCounter}`
    set((state) => ({
      toasts: [...state.toasts, { id, type: 'error', message, duration }],
    }))
  },

  warning: (message, duration = 3500) => {
    const id = `toast-${++toastIdCounter}`
    set((state) => ({
      toasts: [...state.toasts, { id, type: 'warning', message, duration }],
    }))
  },

  info: (message, duration = 3000) => {
    const id = `toast-${++toastIdCounter}`
    set((state) => ({
      toasts: [...state.toasts, { id, type: 'info', message, duration }],
    }))
  },
}))

/**
 * 便捷的 toast 函数，可以在任何地方使用
 */
export const toast = {
  success: (message: string, duration?: number) => {
    useToastStore.getState().success(message, duration)
  },
  error: (message: string, duration?: number) => {
    useToastStore.getState().error(message, duration)
  },
  warning: (message: string, duration?: number) => {
    useToastStore.getState().warning(message, duration)
  },
  info: (message: string, duration?: number) => {
    useToastStore.getState().info(message, duration)
  },
}

