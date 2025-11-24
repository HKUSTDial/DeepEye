/**
 * LLM 模型配置
 * 
 * 统一管理所有可用的 AI 模型
 */

export interface ModelConfig {
  /** 模型 ID */
  id: string
  /** 显示名称 */
  name: string
  /** 模型提供商 */
  provider: 'openai' | 'anthropic' | 'google' | 'deepseek' | 'other'
  /** 模型描述 */
  description?: string
  /** 是否为默认模型 */
  isDefault?: boolean
  /** 上下文窗口大小 */
  contextWindow?: number
  /** 是否支持视觉 */
  supportsVision?: boolean
  /** 是否支持函数调用 */
  supportsFunctionCalling?: boolean
}

/**
 * 可用的 LLM 模型列表
 */
export const AVAILABLE_MODELS: ModelConfig[] = [
  // OpenAI 模型
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o-mini',
    provider: 'openai',
    description: '',
    isDefault: true,
    contextWindow: 128000,
    supportsVision: true,
    supportsFunctionCalling: true
  }
]

/**
 * 获取默认模型
 */
export function getDefaultModel(): ModelConfig {
  return AVAILABLE_MODELS.find(m => m.isDefault) || AVAILABLE_MODELS[0]
}

/**
 * 根据 ID 获取模型配置
 */
export function getModelById(id: string): ModelConfig | undefined {
  return AVAILABLE_MODELS.find(m => m.id === id)
}

/**
 * 按提供商分组模型
 */
export function getModelsByProvider(): Record<string, ModelConfig[]> {
  return AVAILABLE_MODELS.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = []
    }
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, ModelConfig[]>)
}

/**
 * 提供商显示名称映射
 */
export const PROVIDER_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  deepseek: 'DeepSeek',
  other: '其他'
}

