/**
 * 视频按 task_id 注册缓存：后端保存 config + TSX，前端拉取后编译并注册，根据 id 预览。
 */

import type React from 'react'
import { getVideoFull, type VideoConfig } from './video'
import { compileTsxAndGetComponent } from '../utils/compileTsxInBrowser'

type SceneComponent = React.FC<Record<string, unknown>>

export interface RegisteredVideo {
  config: VideoConfig
  components: Record<string, SceneComponent>
}

const cache = new Map<string, RegisteredVideo>()
const loading = new Map<string, Promise<RegisteredVideo | null>>()

function cacheKey(taskId: string, sessionId?: string | null): string {
  return `${sessionId || '__legacy__'}:${taskId}`
}

/**
 * 根据 task_id 向后端拉取 config + 所有 TSX，编译后注册到缓存，并返回。
 * 同一 task_id 并发只请求一次；已注册的 task_id 直接读缓存。
 */
export async function registerVideoByTaskId(
  taskId: string,
  sessionId?: string | null,
): Promise<RegisteredVideo | null> {
  const key = cacheKey(taskId, sessionId)
  const cached = cache.get(key)
  if (cached) return cached

  const existing = loading.get(key)
  if (existing) return existing

  const promise = (async (): Promise<RegisteredVideo | null> => {
    try {
      const res = await getVideoFull(taskId, sessionId)
      const components: Record<string, SceneComponent> = {}
      for (const [sceneId, filename] of Object.entries(res.registry || {})) {
        const tsx = res.files?.[filename]
        if (!tsx) continue
        const comp = await compileTsxAndGetComponent(tsx, filename)
        if (comp) components[sceneId] = comp
      }
      const entry: RegisteredVideo = { config: res.config, components }
      cache.set(key, entry)
      return entry
    } catch (e) {
      console.warn('[videoRegistration] register failed:', { taskId, sessionId, error: e })
      return null
    } finally {
      loading.delete(key)
    }
  })()
  loading.set(key, promise)
  return promise
}

/** 从缓存读取已注册的视频（仅读，不拉取） */
export function getRegisteredVideo(taskId: string, sessionId?: string | null): RegisteredVideo | null {
  return cache.get(cacheKey(taskId, sessionId)) ?? null
}

/** 判断某 task_id 是否已注册 */
export function isVideoRegistered(taskId: string, sessionId?: string | null): boolean {
  return cache.has(cacheKey(taskId, sessionId))
}

/** 清除视频组件缓存，强制下次预览时重新拉取 TSX。在控制台执行 window.clearVideoCache?.() 可刷新组件 */
export function clearVideoCache(taskId?: string, sessionId?: string | null): void {
  if (taskId != null) {
    cache.delete(cacheKey(taskId, sessionId ?? undefined))
  } else {
    cache.clear()
  }
}
