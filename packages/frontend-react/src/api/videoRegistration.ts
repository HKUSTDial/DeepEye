/**
 * 视频按 task_id 注册缓存：后端保存 config + TSX，前端拉取后编译并注册，根据 id 预览。
 */

import type React from 'react'
import { getVideoFull, type VideoConfig } from './video'
import { compileTsxAndGetComponent } from '../utils/compileTsxInBrowser'

export interface RegisteredVideo {
  config: VideoConfig
  components: Record<string, React.FC<any>>
}

const cache = new Map<string, RegisteredVideo>()
const loading = new Map<string, Promise<RegisteredVideo | null>>()

/**
 * 根据 task_id 向后端拉取 config + 所有 TSX，编译后注册到缓存，并返回。
 * 同一 task_id 并发只请求一次；已注册的 task_id 直接读缓存。
 */
export async function registerVideoByTaskId(taskId: string): Promise<RegisteredVideo | null> {
  const cached = cache.get(taskId)
  if (cached) return cached

  const existing = loading.get(taskId)
  if (existing) return existing

  const promise = (async (): Promise<RegisteredVideo | null> => {
    try {
      const res = await getVideoFull(taskId)
      const components: Record<string, React.FC<any>> = {}
      for (const [sceneId, filename] of Object.entries(res.registry || {})) {
        const tsx = res.files?.[filename]
        if (!tsx) continue
        const comp = await compileTsxAndGetComponent(tsx, filename)
        if (comp) components[sceneId] = comp
      }
      const entry: RegisteredVideo = { config: res.config, components }
      cache.set(taskId, entry)
      return entry
    } catch (e) {
      console.warn('[videoRegistration] register failed:', taskId, e)
      return null
    } finally {
      loading.delete(taskId)
    }
  })()
  loading.set(taskId, promise)
  return promise
}

/** 从缓存读取已注册的视频（仅读，不拉取） */
export function getRegisteredVideo(taskId: string): RegisteredVideo | null {
  return cache.get(taskId) ?? null
}

/** 判断某 task_id 是否已注册 */
export function isVideoRegistered(taskId: string): boolean {
  return cache.has(taskId)
}
