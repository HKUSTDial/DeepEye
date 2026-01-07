/**
 * Unified HTTP client for API requests
 * 支持自动鉴权、token 刷新
 */

import { config } from '../config'
import { useAuthStore } from '../stores/auth'

export const API_BASE = config.api.baseUrl
export const AUTH_BASE = config.api.authBaseUrl

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

interface RequestOptions {
  body?: unknown
  skipAuth?: boolean  // 是否跳过自动添加 token（用于登录/注册等）
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public response?: any) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * 核心请求函数
 * 自动添加 Authorization header
 * 自动处理 token 过期并刷新
 */
async function request<T>(
  method: HttpMethod, 
  path: string, 
  options: RequestOptions = {}
): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), config.api.timeout)

  try {
    // 1. 准备 headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    // 2. 自动添加 Authorization header（如果有 token 且不跳过鉴权）
    if (!options.skipAuth) {
      const token = useAuthStore.getState().accessToken
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    // 3. 发起请求
    let res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    })

    // 4. 处理 401 - Token 过期，尝试刷新
    if (res.status === 401 && !options.skipAuth) {
      console.log('[HTTP Client] Token expired, attempting refresh...')
      
      try {
        // 调用 refresh token
        await useAuthStore.getState().refreshToken()
        
        // 用新 token 重试请求
        const newToken = useAuthStore.getState().accessToken
        if (newToken) {
          headers['Authorization'] = `Bearer ${newToken}`
          
          res = await fetch(`${API_BASE}${path}`, {
            method,
            headers,
            body: options.body ? JSON.stringify(options.body) : undefined,
            signal: controller.signal,
          })
        }
      } catch (refreshError) {
        // Refresh 失败，跳转登录页
        console.error('[HTTP Client] Token refresh failed:', refreshError)
        useAuthStore.getState().logout()
        
        // 如果在浏览器环境，跳转到登录页
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
        
        throw new ApiError(401, 'Session expired, please login again')
      }
    }

    // 5. 处理响应
    if (!res.ok) {
      let errorMessage = `Request failed: ${res.statusText}`
      let errorData: any = undefined
      
      try {
        errorData = await res.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch {
        // 无法解析 JSON，使用默认错误消息
      }
      
      throw new ApiError(res.status, errorMessage, errorData)
    }

    return res.status === 204 ? (undefined as T) : res.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

/**
 * 认证相关请求（不自动添加 token）
 */
async function authRequest<T>(
  method: HttpMethod,
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), config.api.timeout)

  try {
    const res = await fetch(`${AUTH_BASE}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    })

    if (!res.ok) {
      let errorMessage = `Request failed: ${res.statusText}`
      let errorData: any = undefined
      
      try {
        errorData = await res.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch {
        // 无法解析 JSON
      }
      
      throw new ApiError(res.status, errorMessage, errorData)
    }

    return res.status === 204 ? (undefined as T) : res.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

// 业务 API（需要鉴权）
export const http = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body }),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, { body }),
  delete: <T>(path: string) => request<T>('DELETE', path),
}

// 认证 API（不需要鉴权）
export const authHttp = {
  get: <T>(path: string) => authRequest<T>('GET', path),
  post: <T>(path: string, body?: unknown) => authRequest<T>('POST', path, { body }),
  put: <T>(path: string, body?: unknown) => authRequest<T>('PUT', path, { body }),
  patch: <T>(path: string, body?: unknown) => authRequest<T>('PATCH', path, { body }),
  delete: <T>(path: string) => authRequest<T>('DELETE', path),
}

