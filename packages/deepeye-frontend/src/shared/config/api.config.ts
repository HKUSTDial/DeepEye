/**
 * API 配置中心
 * 统一管理所有 API 相关配置
 */

export interface APIConfig {
  baseURL: string
  timeout: number
  enableLogging: boolean
}

/**
 * 从环境变量加载配置
 */
function loadConfigFromEnv(): APIConfig {
  // 直接硬编码配置，不依赖环境变量
  const baseURL = 'http://localhost:8001/api/v1'
  const timeout = 30000
  const enableLogging = true  // 开发环境启用日志

  return {
    baseURL,
    timeout,
    enableLogging,
  }
}

/**
 * API 配置管理器
 */
class APIConfigManager {
  private config: APIConfig

  constructor() {
    this.config = loadConfigFromEnv()
    this.logConfig()
  }

  /**
   * 获取配置
   */
  getConfig(): APIConfig {
    return { ...this.config }
  }

  /**
   * 获取基础 URL
   */
  getBaseURL(): string {
    return this.config.baseURL
  }

  /**
   * 获取超时时间
   */
  getTimeout(): number {
    return this.config.timeout
  }

  /**
   * 是否启用日志
   */
  isLoggingEnabled(): boolean {
    return this.config.enableLogging
  }

  /**
   * 更新配置（用于运行时动态修改）
   */
  updateConfig(partial: Partial<APIConfig>): void {
    this.config = { ...this.config, ...partial }
    this.logConfig()
  }

  /**
   * 打印配置信息
   */
  private logConfig(): void {
    if (this.config.enableLogging) {
      console.group('⚙️ API 配置')
      console.log('📍 Base URL:', this.config.baseURL)
      console.log('⏱️  Timeout:', this.config.timeout, 'ms')
      console.log('📝 Logging:', this.config.enableLogging ? '启用' : '禁用')
      console.groupEnd()
    }
  }
}

// 导出单例
export const apiConfig = new APIConfigManager()

// 导出便捷方法
export const getAPIBaseURL = () => apiConfig.getBaseURL()
export const getAPITimeout = () => apiConfig.getTimeout()
export const isAPILoggingEnabled = () => apiConfig.isLoggingEnabled()

