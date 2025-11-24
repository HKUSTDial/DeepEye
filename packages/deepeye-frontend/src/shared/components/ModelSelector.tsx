/**
 * 模型选择器组件
 *
 * 统一的 LLM 模型选择下拉框
 */

import { AVAILABLE_MODELS, getModelsByProvider, PROVIDER_NAMES } from '@/shared/config/models'
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
  /** 是否按提供商分组 */
  groupByProvider?: boolean
}

export function ModelSelector({
  value,
  onChange,
  className,
  disabled = false,
  groupByProvider = true
}: ModelSelectorProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange?.(e.target.value)
  }

  // 按提供商分组
  if (groupByProvider) {
    const modelsByProvider = getModelsByProvider()

    return (
      <select
        value={value}
        onChange={handleChange}
        disabled={disabled}
        className={cn(
          'bg-background border text-foreground text-sm rounded px-2 py-1',
          'focus:outline-none focus:ring-2 focus:ring-ring',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          className
        )}
      >
        {Object.entries(modelsByProvider).map(([provider, models]) => (
          <optgroup key={provider} label={PROVIDER_NAMES[provider] || provider}>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    )
  }

  // 不分组
  return (
    <select
      value={value}
      onChange={handleChange}
      disabled={disabled}
      className={cn(
        'bg-background border text-foreground text-sm rounded px-2 py-1',
        'focus:outline-none focus:ring-2 focus:ring-ring',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
    >
      {AVAILABLE_MODELS.map((model) => (
        <option key={model.id} value={model.id}>
          {model.name}
        </option>
      ))}
    </select>
  )
}

