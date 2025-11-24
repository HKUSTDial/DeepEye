/**
 * HTTP API 客户端
 *
 * 统一管理所有 HTTP 请求，包括：
 * - 请求拦截（添加认证 Token）
 * - 响应拦截（错误处理）
 * - 超时控制
 */

import { apiConfig } from '../config/api.config'

export interface APIRequestOptions extends RequestInit {
  skipErrorStatuses?: number[]
}

export interface APIError {
  message: string
  status: number
  detail?: string
}

export class APIClient {
  private baseURL: string
  private timeout: number
  private token: string | null = null

  constructor(baseURL?: string, timeout?: number) {
    // 使用统一的配置中心
    this.baseURL = baseURL || apiConfig.getBaseURL()
    this.timeout = timeout || apiConfig.getTimeout()

    // 从 localStorage 恢复 token
    this.token = localStorage.getItem('auth_token')
  }

  /**
   * 设置认证 Token
   */
  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem('auth_token', token)
    } else {
      localStorage.removeItem('auth_token')
    }
  }

  /**
   * 获取当前 Token
   */
  getToken(): string | null {
    return this.token
  }

  /**
   * 清除认证信息
   */
  clearAuth() {
    this.setToken(null)
  }

  /**
   * 发送 HTTP 请求
   */
  async request<T = any>(
    endpoint: string,
    options: APIRequestOptions = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const { skipErrorStatuses, ...fetchOptions } = options
    
    // 构建请求头（默认使用 JSON，但对 FormData 自动让浏览器处理）
    const headers = new Headers(fetchOptions.headers || undefined)
    const isFormDataBody =
      typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData

    if (!isFormDataBody && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    // 添加认证 Token
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`)
    }

    // 创建 AbortController 用于超时控制
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeout)

    try {
      const response = await fetch(
        url,
        {
          ...fetchOptions,
          headers,
          signal: controller.signal,
        }
      )

      clearTimeout(timeoutId)

      // 处理响应
      if (!response.ok) {
        if (skipErrorStatuses?.includes(response.status)) {
          return undefined as T
        }
        await this.handleError(response)
      }

      // 204 无内容直接返回
      if (response.status === 204) {
        return undefined as T
      }

      const contentType = response.headers.get('content-type')?.toLowerCase() ?? ''
      const isJSON = contentType.includes('application/json') || contentType.includes('+json')
      const rawText = await response.text()

      if (!rawText) {
        return undefined as T
      }

      if (isJSON) {
        try {
          return JSON.parse(rawText) as T
        } catch (error) {
          console.warn('解析 JSON 失败，返回原始文本', error)
        }
      }

      return rawText as T
    } catch (error) {
      clearTimeout(timeoutId)
      
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error('请求超时')
        }
        throw error
      }
      
      throw new Error('未知错误')
    }
  }

  /**
   * 处理错误响应
   */
  private async handleError(response: Response): Promise<never> {
    let errorMessage = response.statusText
    let errorDetail: string | undefined

    try {
      const errorData = await response.json()
      errorDetail = errorData.detail || errorData.message
    } catch {
      // 无法解析错误响应
    }

    // 401 未授权 - 清除 Token
    if (response.status === 401) {
      this.clearAuth()
      errorMessage = '未授权，请重新登录'
    }

    // 使用 detail 作为主要错误信息（如果存在）
    const finalMessage = errorDetail || errorMessage

    const error = new Error(finalMessage) as Error & APIError
    error.message = finalMessage
    error.status = response.status
    error.detail = errorDetail

    throw error
  }

  /**
   * GET 请求
   */
  async get<T = any>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const queryString = params
      ? '?' + new URLSearchParams(params).toString()
      : ''
    
    return this.request<T>(endpoint + queryString, {
      method: 'GET',
    })
  }

  /**
   * POST 请求
   */
  async post<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * PUT 请求
   */
  async put<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * DELETE 请求
   */
  async delete<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    })
  }
}

// 全局单例
export const apiClient = new APIClient()

