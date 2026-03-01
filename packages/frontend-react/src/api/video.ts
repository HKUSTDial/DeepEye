/**
 * Video generation API
 */

import { http } from './client'

export interface VideoConfig {
  meta: {
    title?: string
    fps: number
    width: number
    height: number
    video_duration: number
    user_query?: string
  }
  scenes: Array<{
    id: string
    type: string
    time_range: [number, number]
    content: unknown
    narration?: Array<{
      text: string
      time_start: number
      time_end: number
      audio_file?: string
    }>
    animations?: unknown[]
  }>
}

export interface VideoConfigResponse {
  config: VideoConfig
  config_path: string
  task_id?: string | null
}

export async function getVideoConfig(taskId: string): Promise<VideoConfigResponse> {
  return http.get<VideoConfigResponse>(`/video/config/${taskId}`)
}

export async function getVideoConfigByPath(path: string): Promise<VideoConfigResponse> {
  return http.get<VideoConfigResponse>(`/video/config/by-path?path=${encodeURIComponent(path)}`)
}

/** Save video config from workflow run output so GET /config/{task_id} can find it. */
export async function saveVideoConfig(taskId: string, config: VideoConfig): Promise<VideoConfigResponse> {
  return http.post<VideoConfigResponse>('/video/config', { task_id: taskId, config }, { timeout: 600_000 })
}

/** Extract taskId/configPath/config from workflow outputs (shared by useChat and WorkflowLivePanel). */
export function extractVideoOutputParams(outputs: Record<string, unknown>): {
  taskId?: string
  configPath?: string
  config?: Record<string, unknown>
} {
  if (!outputs || typeof outputs !== 'object') {
    console.log('🔍 extractVideoOutputParams: outputs is not an object', outputs)
    return {}
  }
  
  console.log('🔍 extractVideoOutputParams: Checking outputs:', JSON.stringify(outputs, null, 2))
  
  for (const nodeId of Object.keys(outputs)) {
    const out = outputs[nodeId] as Record<string, unknown> | undefined
    if (!out) continue
    
    console.log(`🔍 extractVideoOutputParams: Checking node ${nodeId}:`, {
      hasVideoInfo: !!out.video_info,
      hasConfigPath: !!out.config_path,
      hasVideoPath: !!out.video_path,
      hasTaskId: !!out.task_id,
      hasConfig: !!out.config,
    })
    
    const videoInfo = out.video_info as Record<string, unknown> | undefined
    const configPath = out.config_path as string | undefined
    const videoPath = out.video_path as string | undefined
    const config = out.config as Record<string, unknown> | undefined
    const topLevelTaskId = out.task_id as string | undefined
    
    let taskId: string | undefined
    
    // 优先级：1. 顶层 task_id（后端直接返回） 2. video_info.task_id 3. 从路径提取
    if (topLevelTaskId) {
      taskId = String(topLevelTaskId)
      console.log(`✅ extractVideoOutputParams: Found taskId from top level: ${taskId}`)
    } else if (videoInfo?.task_id) {
      taskId = String(videoInfo.task_id)
      console.log(`✅ extractVideoOutputParams: Found taskId from video_info: ${taskId}`)
    } else if (videoPath) {
      const m = String(videoPath).match(/claude_tsx_animated[/\\](\d{8}_\d{6})/)
      if (m) {
        taskId = m[1]
        console.log(`✅ extractVideoOutputParams: Extracted taskId from video_path: ${taskId}`)
      }
    } else if (configPath) {
      const m = String(configPath).match(/generated_(\d{8}_\d{6})_aligned\.json/)
      if (m) {
        taskId = m[1]
        console.log(`✅ extractVideoOutputParams: Extracted taskId from config_path: ${taskId}`)
      }
    }
    
    if (taskId || configPath) {
      const result = { taskId, configPath, config }
      console.log('✅ extractVideoOutputParams: Returning video params:', result)
      return result
    }
  }
  
  console.log('⚠️ extractVideoOutputParams: No video output found in outputs')
  return {}
}

/** Public API base for audio (no auth). Returns absolute URL so Remotion/browser loads audio reliably. */
export function getAudioFileUrl(filename: string): string {
  const apiBase = import.meta.env.VITE_API_URL || '/api/v1'
  const publicApiBase = apiBase.replace(/\/api\/v1\/?$/, '/api/public')
  const path = `${publicApiBase}/video/audio/${encodeURIComponent(filename)}`
  if (typeof window !== 'undefined' && path.startsWith('/')) {
    return `${window.location.origin}${path}`
  }
  return path
}

/** 获取某 task 的组件 registry：scene_id -> filename */
export interface VideoComponentRegistryResponse {
  task_id: string
  registry: Record<string, string>
}

export async function getVideoComponentRegistry(taskId: string): Promise<VideoComponentRegistryResponse> {
  return http.get<VideoComponentRegistryResponse>(`/video/components/${taskId}/registry`)
}

/** 获取动态组件 TSX 源码的 URL（public，无鉴权） */
export function getVideoComponentFileUrl(taskId: string, filename: string): string {
  const apiBase = import.meta.env.VITE_API_URL || '/api/v1'
  const publicApiBase = apiBase.replace(/\/api\/v1\/?$/, '/api/public')
  return `${publicApiBase}/video/components/${encodeURIComponent(taskId)}/${encodeURIComponent(filename)}`
}

/** 按 task_id 一次拉取：config + registry + 所有 TSX 源码，供前端注册后按 id 预览 */
export interface VideoFullResponse {
  task_id: string
  config: VideoConfig
  registry: Record<string, string>
  files: Record<string, string>
}

export async function getVideoFull(taskId: string): Promise<VideoFullResponse> {
  // 使用公开接口，无需认证（视频预览应该公开）
  const apiBase = import.meta.env.VITE_API_URL || '/api/v1'
  const publicApiBase = apiBase.replace(/\/api\/v1\/?$/, '/api/public')
  // 直接 fetch，不使用 http client（避免自动添加 token）
  const response = await fetch(`${publicApiBase}/video/full/${taskId}`)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(error.detail || `Failed to fetch video: ${response.status}`)
  }
  return response.json()
}
