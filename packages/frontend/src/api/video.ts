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

function withSessionQuery(url: string, sessionId?: string | null): string {
  if (!sessionId) return url
  const sep = url.includes('?') ? '&' : '?'
  return `${url}${sep}session_id=${encodeURIComponent(sessionId)}`
}

function requireSessionId(sessionId?: string | null): string {
  const value = (sessionId || '').trim()
  if (!value) {
    throw new Error('session_id is required for video assets')
  }
  return value
}

/** Extract taskId from workflow outputs (shared by useChat and WorkflowLivePanel). */
export function extractVideoOutputParams(outputs: Record<string, unknown>): {
  taskId?: string
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
      hasVideoPath: !!out.video_path,
      hasTaskId: !!out.task_id,
    })
    
    const videoInfo = out.video_info as Record<string, unknown> | undefined
    const videoPath = out.video_path as string | undefined
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
      const m = String(videoPath).match(/(?:claude_tsx_animated|video_components)[/\\](\d{8}_\d{6})/)
      if (m) {
        taskId = m[1]
        console.log(`✅ extractVideoOutputParams: Extracted taskId from video_path: ${taskId}`)
      }
    }
    
    if (taskId) {
      const result = { taskId }
      console.log('✅ extractVideoOutputParams: Returning video params:', result)
      return result
    }
  }
  
  console.log('⚠️ extractVideoOutputParams: No video output found in outputs')
  return {}
}

/** Authenticated video audio URL for <Audio src>, session-scoped. */
export function getAudioFileUrl(filename: string, sessionId?: string | null): string {
  const path = withSessionQuery(`/api/v1/video/audio/${encodeURIComponent(filename)}`, sessionId)
  if (typeof window !== 'undefined' && path.startsWith('/')) {
    return `${window.location.origin}${path}`
  }
  return path
}

/** 获取某 task 的组件 registry：scene_id -> filename */
export interface VideoComponentRegistryResponse {
  task_id: string
  session_id?: string | null
  registry: Record<string, string>
}

export async function getVideoComponentRegistry(
  taskId: string,
  sessionId?: string | null,
): Promise<VideoComponentRegistryResponse> {
  const full = await getVideoFull(taskId, sessionId)
  return {
    task_id: full.task_id,
    session_id: full.session_id,
    registry: full.registry,
  }
}

/** 获取动态组件 TSX 源码的 URL（鉴权：cookie/header + session scope） */
export function getVideoComponentFileUrl(taskId: string, filename: string, sessionId?: string | null): string {
  return withSessionQuery(
    `/api/v1/video/components/${encodeURIComponent(taskId)}/${encodeURIComponent(filename)}`,
    sessionId,
  )
}

/** 按 task_id 一次拉取：config + registry + 所有 TSX 源码，供前端注册后按 id 预览 */
export interface VideoFullResponse {
  task_id: string
  session_id?: string | null
  config: VideoConfig
  registry: Record<string, string>
  files: Record<string, string>
}

export async function getVideoFull(taskId: string, sessionId?: string | null): Promise<VideoFullResponse> {
  const sid = requireSessionId(sessionId)
  const url = withSessionQuery(`/video/full/${encodeURIComponent(taskId)}`, sid)
  return http.get<VideoFullResponse>(url)
}
