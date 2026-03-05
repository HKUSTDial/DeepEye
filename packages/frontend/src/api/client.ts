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
  headers?: Record<string, string>
  skipAuth?: boolean  // 是否跳过自动添加 token（用于登录/注册等）
  timeout?: number    // 毫秒，不传则用 config.api.timeout
}

export class ApiError extends Error {
  public status: number
  public response?: unknown

  constructor(status: number, message: string, response?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.response = response
  }
}

function extractErrorMessage(errorData: unknown, fallback: string): string {
  if (!errorData || typeof errorData !== 'object') {
    return fallback
  }
  const record = errorData as Record<string, unknown>
  if (typeof record.detail === 'string') {
    return record.detail
  }
  if (typeof record.message === 'string') {
    return record.message
  }
  return fallback
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
  const timeoutMs = options.timeout ?? config.api.timeout
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    // 1. 准备 headers
    const headers: Record<string, string> = { ...options.headers }
    
    // 如果 body 不是 FormData，默认设置为 JSON
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }

    // 2. 自动添加 Authorization header（如果有 token 且不跳过鉴权）
    if (!options.skipAuth) {
      const token = useAuthStore.getState().accessToken
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    // 3. 准备 body
    const body = options.body instanceof FormData 
      ? options.body 
      : (options.body ? JSON.stringify(options.body) : undefined)

    // 4. 发起请求
    let res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body,
      credentials: 'include',
      signal: controller.signal,
    })

    // 5. 处理 401 - Token 过期，尝试刷新
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
            body,
            credentials: 'include',
            signal: controller.signal,
          })
        }
      } catch (refreshError) {
        // Refresh 失败，跳转登录页
        console.error('[HTTP Client] Token refresh failed:', refreshError)
        useAuthStore.getState().logout()
        
        // 如果在浏览器环境，跳转到登录页
        if (typeof window !== 'undefined') {
          const next = `${window.location.pathname}${window.location.search}`
          window.location.href = `/auth?next=${encodeURIComponent(next)}`
        }
        
        throw new ApiError(401, 'Session expired, please login again')
      }
    }

    // 6. 处理响应
    if (!res.ok) {
      let errorMessage = `Request failed: ${res.statusText}`
      let errorData: unknown = undefined
      
      try {
        errorData = await res.json()
        errorMessage = extractErrorMessage(errorData, errorMessage)
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
 * Raw request that returns the Response object (for blobs/streams).
 * Uses the same auth + refresh logic as `request`.
 */
async function requestResponse(
  method: HttpMethod,
  path: string,
  options: RequestOptions = {},
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), config.api.timeout)

  try {
    // 1. Prepare headers
    const headers: Record<string, string> = { ...options.headers }

    // Keep behavior consistent with `request`: default to JSON content-type when not FormData
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }

    // 2. Auto add Authorization header
    if (!options.skipAuth) {
      const token = useAuthStore.getState().accessToken
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    // 3. Prepare body
    const body =
      options.body instanceof FormData
        ? options.body
        : (options.body ? JSON.stringify(options.body) : undefined)

    // 4. Fetch
    let res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body,
      credentials: 'include',
      signal: controller.signal,
    })

    // 5. Handle 401 with refresh and retry
    if (res.status === 401 && !options.skipAuth) {
      console.log('[HTTP Client] Token expired, attempting refresh...')
      try {
        await useAuthStore.getState().refreshToken()
        const newToken = useAuthStore.getState().accessToken
        if (newToken) {
          headers['Authorization'] = `Bearer ${newToken}`
          res = await fetch(`${API_BASE}${path}`, {
            method,
            headers,
            body,
            credentials: 'include',
            signal: controller.signal,
          })
        }
      } catch (refreshError) {
        console.error('[HTTP Client] Token refresh failed:', refreshError)
        useAuthStore.getState().logout()
        if (typeof window !== 'undefined') {
          const next = `${window.location.pathname}${window.location.search}`
          window.location.href = `/auth?next=${encodeURIComponent(next)}`
        }
        throw new ApiError(401, 'Session expired, please login again')
      }
    }

    // 6. Handle non-OK
    if (!res.ok) {
      let errorMessage = `Request failed: ${res.statusText}`
      let errorData: unknown = undefined

      try {
        errorData = await res.json()
        errorMessage = extractErrorMessage(errorData, errorMessage)
      } catch {
        // ignore
      }

      throw new ApiError(res.status, errorMessage, errorData)
    }

    return res
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
    const headers: Record<string, string> = { ...options.headers }
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }

    const res = await fetch(`${AUTH_BASE}${path}`, {
      method,
      headers,
      body: options.body instanceof FormData
        ? options.body
        : (options.body ? JSON.stringify(options.body) : undefined),
      credentials: 'include',
      signal: controller.signal,
    })

    if (!res.ok) {
      let errorMessage = `Request failed: ${res.statusText}`
      let errorData: unknown = undefined
      
      try {
        errorData = await res.json()
        errorMessage = extractErrorMessage(errorData, errorMessage)
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
  get: <T>(path: string, options?: RequestOptions) => request<T>('GET', path, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>('POST', path, { ...options, body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>('PUT', path, { ...options, body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>('PATCH', path, { ...options, body }),
  delete: <T>(path: string) => request<T>('DELETE', path),
  getResponse: (path: string) => requestResponse('GET', path),
}

// 认证 API（不需要鉴权）
export const authHttp = {
  get: <T>(path: string) => authRequest<T>('GET', path),
  post: <T>(path: string, body?: unknown) => authRequest<T>('POST', path, { body }),
  put: <T>(path: string, body?: unknown) => authRequest<T>('PUT', path, { body }),
  patch: <T>(path: string, body?: unknown) => authRequest<T>('PATCH', path, { body }),
  delete: <T>(path: string) => authRequest<T>('DELETE', path),
}
