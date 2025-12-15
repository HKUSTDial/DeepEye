/**
 * 模型选择器组件
 *
 * 统一的 LLM 模型选择下拉框
 */

import { useState, useEffect } from 'react'
import { llmModelsAPI } from '@/shared/api'
import { cn } from '@/shared/utils'

export interface ModelSelectorProps {
  /** 当前选中的模型 ID */
  value?: string
  /** 选择变化回调 */
  onChange?: (modelId: string) => void
  /** 额外的类名 */
  className?: string
  /** 是否禁用 */
  disabled?: boolean
  /** 是否按提供商分组 (暂不支持) */
  groupByProvider?: boolean
}

export function ModelSelector({
  value,
  onChange,
  className,
  disabled = false,
  // groupByProvider = true // 暂不支持分组
}: ModelSelectorProps) {
  const [models, setModels] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadModels = async () => {
      setLoading(true)
      try {
        const data = await llmModelsAPI.list()
        setModels(data)
        
        // 如果当前有数据但没有选中值，触发 onChange 选择第一个
        // 注意：这里需要小心死循环或不必要的更新，通常由父组件控制 value
        // 但如果父组件传了 undefined，我们可以尝试帮它选一个
        if (!value && data.length > 0 && onChange) {
            onChange(data[0].id)
        }
      } catch (error) {
        console.error('Failed to load models:', error)
      } finally {
        setLoading(false)
      }
    }
    loadModels()
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange?.(e.target.value)
  }

  return (
    <select
      value={value || ''}
      onChange={handleChange}
      disabled={disabled || loading}
      className={cn(
        'bg-background border text-foreground text-sm rounded px-2 py-1',
        'focus:outline-none focus:ring-2 focus:ring-ring',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
    >
      {loading ? (
        <option>加载中...</option>
      ) : models.length === 0 ? (
        <option value="">无可用模型</option>
      ) : (
        models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.model_name || model.model_endpoint_name}
          </option>
        ))
      )}
    </select>
  )
}

