/**
 * VideoComposer - 数据视频串联组件
 * 仅保留动态加载链路：
 * 1) 已注册组件（前端缓存）
 * 2) 本地静态模板目录（若存在）
 * 3) 后端 registry + TSX 拉取编译
 */

import React, { useState, useEffect, useMemo } from 'react'
import { AbsoluteFill, Sequence, useVideoConfig, Audio } from 'remotion'
import { getAudioFileUrl, getVideoComponentRegistry, getVideoComponentFileUrl, type VideoConfig } from '../../api/video'
import { compileTsxAndGetComponent } from '../../utils/compileTsxInBrowser'

type SceneNarration = {
  text?: string
  time_start?: number
  time_end?: number
  audio_file?: string
}

type SceneContent = {
  title?: string
  headline?: string
  style?: {
    background_color?: string
  }
}

type VideoScene = {
  id: string
  type?: string
  time_range?: [number, number]
  content?: SceneContent
  narration?: SceneNarration[]
  animations?: unknown[]
}

type SceneComponentProps = {
  sceneStartOffset?: number
  narrations?: SceneNarration[]
  animations?: unknown[]
  sceneContent?: SceneContent
  scene?: VideoScene
}

type SceneComponent = React.FC<SceneComponentProps>

type SceneModule = Record<string, unknown> & { default?: SceneComponent }

interface VideoComposerProps {
  configJson: VideoConfig | Record<string, unknown> | null | undefined
  componentPrefix?: string
  taskId?: string | null
  sessionId?: string | null
  includeOpeningClosing?: boolean
  registeredSceneComponents?: Record<string, SceneComponent> | null
}

/** 根据 scene_id 生成动画组件文件名（与后端一致） */
function sceneIdToFilename(sceneId: string, datasetName: string, taskId: string): string {
  const camel = sceneId
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join('')
  const needComponent =
    sceneId === 'scene_opening' ||
    sceneId === 'scene_closing' ||
    sceneId.toLowerCase().includes('stat') ||
    sceneId.endsWith('_statistics')
  if (needComponent) return `${datasetName}_${camel}_${taskId}ComponentAnimated.tsx`
  return `${datasetName}_${camel}_${taskId}Animated.tsx`
}

/** 所有子目录下的场景 TSX（如果存在） */
const dynamicModuleLoaders = import.meta.glob<SceneModule>(
  ['./**/*ComponentAnimated.tsx', './**/*Animated.tsx'],
  { eager: false },
)

function parseScenes(configJson: VideoComposerProps['configJson']): VideoScene[] {
  if (!configJson || typeof configJson !== 'object') {
    return []
  }
  const rawScenes = (configJson as { scenes?: unknown }).scenes
  if (!Array.isArray(rawScenes)) {
    return []
  }
  return rawScenes
    .filter((scene): scene is Record<string, unknown> => Boolean(scene) && typeof scene === 'object')
    .map((scene) => ({
      id: String(scene.id || ''),
      type: typeof scene.type === 'string' ? scene.type : undefined,
      time_range: Array.isArray(scene.time_range) ? (scene.time_range as [number, number]) : undefined,
      content: (scene.content as SceneContent | undefined) || undefined,
      narration: Array.isArray(scene.narration) ? (scene.narration as SceneNarration[]) : undefined,
      animations: Array.isArray(scene.animations) ? scene.animations : undefined,
    }))
    .filter((scene) => scene.id.length > 0)
}

function pickSceneComponent(mod: SceneModule): SceneComponent | null {
  if (typeof mod.default === 'function') {
    return mod.default
  }
  const named = Object.values(mod).find((v): v is SceneComponent => typeof v === 'function')
  return named || null
}

const VideoComposerComponent: React.FC<VideoComposerProps> = ({
  configJson,
  componentPrefix = '',
  taskId,
  sessionId,
  includeOpeningClosing = true,
  registeredSceneComponents,
}) => {
  const { fps } = useVideoConfig()

  const [dynamicComponents, setDynamicComponents] = useState<Record<string, SceneComponent> | null>(null)
  const [dynamicLoadError, setDynamicLoadError] = useState<string | null>(null)

  const scenes = useMemo(() => parseScenes(configJson), [configJson])

  const hasRegisteredComponents = Boolean(
    registeredSceneComponents && Object.keys(registeredSceneComponents).length > 0,
  )

  const useDynamic = useMemo(() => {
    return Boolean(taskId && componentPrefix)
  }, [taskId, componentPrefix])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      if (hasRegisteredComponents && registeredSceneComponents) {
        if (!cancelled) {
          setDynamicComponents(registeredSceneComponents)
          setDynamicLoadError(null)
        }
        return
      }

      if (!useDynamic || !taskId || !componentPrefix || scenes.length === 0) {
        if (!cancelled) {
          setDynamicComponents(null)
          setDynamicLoadError(null)
        }
        return
      }

      const sceneIds = scenes.map((scene) => scene.id)
      const localLoaded: Record<string, SceneComponent> = {}

      const localPromises = sceneIds.map(async (sceneId) => {
        const filename = sceneIdToFilename(sceneId, componentPrefix, taskId)
        const pathKey = `./${componentPrefix}/${taskId}/${filename}`
        const loader = dynamicModuleLoaders[pathKey]
        if (!loader) {
          return
        }
        try {
          const mod = await loader()
          const component = pickSceneComponent(mod)
          if (component) {
            localLoaded[sceneId] = component
          }
        } catch (error) {
          console.warn(`Failed to load local dynamic scene ${sceneId}:`, error)
        }
      })

      await Promise.all(localPromises)

      if (Object.keys(localLoaded).length > 0) {
        if (!cancelled) {
          setDynamicComponents(localLoaded)
          setDynamicLoadError(null)
        }
        return
      }

      try {
        const registryResponse = await getVideoComponentRegistry(taskId, sessionId)
        const registry = registryResponse.registry || {}
        const remoteLoaded: Record<string, SceneComponent> = {}

        await Promise.all(
          Object.entries(registry).map(async ([sceneId, filename]) => {
            try {
              const url = getVideoComponentFileUrl(taskId, filename, sessionId)
              const response = await fetch(url)
              if (!response.ok) {
                throw new Error(`${filename}: ${response.status}`)
              }
              const tsx = await response.text()
              const component = await compileTsxAndGetComponent(tsx, filename)
              if (component) {
                remoteLoaded[sceneId] = component
              }
            } catch (error) {
              console.warn(`[VideoComposer] fetch/compile ${sceneId}:`, error)
            }
          }),
        )

        if (!cancelled) {
          const hasAny = Object.keys(remoteLoaded).length > 0
          setDynamicComponents(hasAny ? remoteLoaded : null)
          setDynamicLoadError(hasAny ? null : '未找到与当前任务匹配的组件（后端可能尚未生成完成）。')
        }
      } catch (error) {
        if (!cancelled) {
          console.warn('[VideoComposer] load from API failed:', error)
          setDynamicComponents(null)
          setDynamicLoadError(
            `加载组件失败：${error instanceof Error ? error.message : '请确认该任务已生成视频组件。'}`,
          )
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [
    hasRegisteredComponents,
    registeredSceneComponents,
    useDynamic,
    taskId,
    componentPrefix,
    scenes,
    sessionId,
  ])

  const sceneComponents = useMemo(() => {
    if (hasRegisteredComponents && registeredSceneComponents) {
      return registeredSceneComponents
    }
    if (dynamicComponents && Object.keys(dynamicComponents).length > 0) {
      return dynamicComponents
    }
    return {}
  }, [hasRegisteredComponents, registeredSceneComponents, dynamicComponents])

  const allScenes = useMemo(() => {
    return scenes.filter((scene) => {
      if (!scene.type) return false
      if (includeOpeningClosing) {
        return ['opening', 'chart', 'stat_cards', 'closing'].includes(scene.type)
      }
      return scene.type === 'chart'
    })
  }, [scenes, includeOpeningClosing])

  const audioSegments = useMemo(() => {
    return scenes.flatMap((scene) => {
      if (!scene.narration) return []
      return scene.narration
        .filter((narration) => Boolean(narration?.audio_file))
        .map((narration) => ({
          audioFile: narration.audio_file || '',
          startTime: narration.time_start || 0,
          endTime: narration.time_end ?? (narration.time_start || 0) + 3,
        }))
    })
  }, [scenes])

  const backgroundColor = useMemo(() => {
    const firstChartScene = scenes.find((scene) => scene.type === 'chart')
    return firstChartScene?.content?.style?.background_color || '#0f1419'
  }, [scenes])

  const getSceneComponent = (scene: VideoScene): SceneComponent | null => {
    return sceneComponents[scene.id] || null
  }

  const createMissingSceneComponent = (scene: VideoScene): SceneComponent => {
    const sceneId = String(scene.id || 'unknown')
    const title = String(scene.content?.title || scene.content?.headline || sceneId)
    const type = String(scene.type || 'unknown')

    return () => (
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          color: '#e5e7eb',
          padding: 48,
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: 860 }}>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>Scene component not generated</div>
          <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 10 }}>
            Scene ID: <span style={{ fontFamily: 'monospace' }}>{sceneId}</span> · Type: {type}
          </div>
          <div style={{ fontSize: 14, opacity: 0.9 }}>{title}</div>
          <div style={{ marginTop: 14, fontSize: 12, opacity: 0.7 }}>
            This usually means the backend only generated some TSX files. Re-run generation or check backend logs.
          </div>
        </div>
      </AbsoluteFill>
    )
  }

  if (useDynamic && dynamicLoadError && (!dynamicComponents || Object.keys(dynamicComponents).length === 0)) {
    return (
      <AbsoluteFill style={{ backgroundColor, justifyContent: 'center', alignItems: 'center', color: '#fff' }}>
        <div style={{ textAlign: 'center', maxWidth: 360 }}>
          <div style={{ marginBottom: 8 }}>无法加载本次生成的视频组件</div>
          <div style={{ fontSize: 12, opacity: 0.8 }}>{dynamicLoadError}</div>
        </div>
      </AbsoluteFill>
    )
  }

  if (useDynamic && dynamicComponents === null && !dynamicLoadError) {
    return (
      <AbsoluteFill style={{ backgroundColor, justifyContent: 'center', alignItems: 'center', color: '#fff' }}>
        <div>正在加载视频组件…</div>
      </AbsoluteFill>
    )
  }

  return (
    <AbsoluteFill style={{ backgroundColor }}>
      {audioSegments.map((segment, idx) => {
        const startFrame = Math.floor(segment.startTime * fps)
        const durationInFrames = Math.floor((segment.endTime - segment.startTime) * fps)
        if (durationInFrames <= 0) return null
        const audioFilename = segment.audioFile.split('/').pop() || segment.audioFile
        if (!audioFilename) return null
        const audioSrc = getAudioFileUrl(audioFilename, sessionId)
        return (
          <Sequence key={`audio-${idx}`} from={startFrame} durationInFrames={durationInFrames}>
            <Audio src={audioSrc} />
          </Sequence>
        )
      })}

      {allScenes.map((scene, sceneIndex) => {
        let startTime: number
        let endTime: number

        if (!scene.time_range || !Array.isArray(scene.time_range) || scene.time_range.length < 2) {
          if (scene.narration?.length) {
            const first = scene.narration[0]
            const last = scene.narration[scene.narration.length - 1]
            startTime = first.time_start || 0
            endTime = last.time_end ?? (last.time_start || 0) + 3
          } else {
            startTime = sceneIndex * 10
            endTime = startTime + 5
          }
        } else {
          ;[startTime, endTime] = scene.time_range
        }

        const startFrame = Math.round(startTime * fps)
        const duration = Math.round((endTime - startTime) * fps)
        const SceneComponent = getSceneComponent(scene) || createMissingSceneComponent(scene)
        const durationInFrames = duration <= 0 ? Math.round(1 * fps) : duration

        return (
          <Sequence key={scene.id} from={startFrame} durationInFrames={durationInFrames} name={scene.id}>
            <SceneComponent
              sceneStartOffset={startTime}
              narrations={scene.narration}
              animations={scene.animations}
              sceneContent={scene.content}
              scene={scene}
            />
          </Sequence>
        )
      })}
    </AbsoluteFill>
  )
}

export const VideoComposer = VideoComposerComponent
