/**
 * Toast - 通知组件
 */

import { useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastProps {
  id: string
  type: ToastType
  message: string
  duration?: number
  onClose: (id: string) => void
}

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertCircle,
  info: Info,
}

const styles = {
  success: 'bg-green-50 text-green-800 border-green-200 dark:bg-green-950/50 dark:text-green-400 dark:border-green-800',
  error: 'bg-destructive/10 text-destructive border-destructive/20',
  warning: 'bg-yellow-50 text-yellow-800 border-yellow-200 dark:bg-yellow-950/50 dark:text-yellow-400 dark:border-yellow-800',
  info: 'bg-primary/10 text-primary border-primary/20',
}

const iconStyles = {
  success: 'text-green-600 dark:text-green-500',
  error: 'text-destructive',
  warning: 'text-yellow-600 dark:text-yellow-500',
  info: 'text-primary',
}

export function Toast({ id, type, message, duration = 3000, onClose }: ToastProps) {
  const Icon = icons[type]

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose(id)
      }, duration)

      return () => clearTimeout(timer)
    }
  }, [id, duration, onClose])

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border p-4 shadow-lg ${styles[type]} animate-in slide-in-from-top-6 fade-in duration-300`}
      role="alert"
    >
      <Icon className={`mt-0.5 flex-shrink-0 ${iconStyles[type]}`} size={20} />
      <p className="flex-1 text-sm font-medium">{message}</p>
      <button
        onClick={() => onClose(id)}
        className="flex-shrink-0 rounded-lg p-1 hover:bg-secondary/50 transition-colors"
      >
        <X size={16} />
      </button>
    </div>
  )
}

/**
 * ToastContainer - Toast 容器
 */
export interface ToastContainerProps {
  toasts: Omit<ToastProps, 'onClose'>[]
  onClose: (id: string) => void
}

export function ToastContainer({ toasts, onClose }: ToastContainerProps) {
  return (
    <div className="fixed left-1/2 top-20 z-50 flex -translate-x-1/2 flex-col gap-2" style={{ maxWidth: '400px', minWidth: '320px' }}>
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onClose={onClose} />
      ))}
    </div>
  )
}

