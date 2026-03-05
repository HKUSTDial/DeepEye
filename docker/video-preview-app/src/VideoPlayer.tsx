/**
 * VideoPlayer - Remotion composition component for data video preview.
 * Receives config + sceneComponents map as inputProps from Remotion Player.
 * This is a simplified, self-contained version of VideoComposer from the main frontend.
 */
import React from 'react'
import { AbsoluteFill, Sequence, Audio, useVideoConfig } from 'remotion'

export interface VideoConfig {
  meta: {
    title?: string
    fps: number
    width: number
    height: number
    video_duration: number
  }
  scenes: Array<{
    id: string
    type: string
    time_range?: [number, number]
    content?: unknown
    narration?: Array<{
      text: string
      time_start: number
      time_end: number
      audio_file?: string
    }>
    animations?: unknown[]
  }>
}

export interface VideoPlayerProps {
  config: VideoConfig
  sceneComponents: Record<string, React.FC<any>>
}

function withPreviewAuthQuery(src: string): string {
  if (typeof window === 'undefined') return src
  try {
    const page = new URL(window.location.href)
    const token = page.searchParams.get('token')
    const sessionId = page.searchParams.get('session_id')
    if (!token && !sessionId) return src

    const target = new URL(src, window.location.origin)
    if (token && !target.searchParams.get('token')) {
      target.searchParams.set('token', token)
    }
    if (sessionId && !target.searchParams.get('session_id')) {
      target.searchParams.set('session_id', sessionId)
    }
    return target.toString()
  } catch {
    return src
  }
}

function MissingSceneComponent({ scene }: { scene: any }) {
  const id = String(scene?.id ?? 'unknown')
  const title = String(scene?.content?.title ?? scene?.content?.headline ?? id)
  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        color: '#e5e7eb',
        background: '#0f1419',
        padding: 48,
      }}
    >
      <div style={{ textAlign: 'center', maxWidth: 860 }}>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>
          Scene component not available
        </div>
        <div style={{ fontSize: 12, opacity: 0.7, fontFamily: 'monospace', marginBottom: 8 }}>
          {id}
        </div>
        <div style={{ fontSize: 14, opacity: 0.9 }}>{title}</div>
      </div>
    </AbsoluteFill>
  )
}

export function VideoPlayer({ config, sceneComponents }: VideoPlayerProps) {
  const { fps } = useVideoConfig()

  const allScenes = (config?.scenes ?? []).filter((s) =>
    ['opening', 'chart', 'stat_cards', 'closing'].includes(s.type),
  )

  const audioSegments = React.useMemo(() => {
    return (config?.scenes ?? []).flatMap((scene) =>
      (scene.narration ?? [])
        .filter((n) => !!n.audio_file)
        .map((n) => ({
          src: withPreviewAuthQuery(n.audio_file!),
          startTime: n.time_start ?? 0,
          endTime: n.time_end ?? (n.time_start ?? 0) + 3.0,
        })),
    )
  }, [config])

  const firstChart = allScenes.find((s) => s.type === 'chart')
  const bg = (firstChart?.content as any)?.style?.background_color ?? '#0f1419'

  return (
    <AbsoluteFill style={{ background: bg }}>
      {audioSegments.map((seg, idx) => {
        const startFrame = Math.floor(seg.startTime * fps)
        const dur = Math.floor((seg.endTime - seg.startTime) * fps)
        if (dur <= 0) return null
        return (
          <Sequence key={`audio-${idx}`} from={startFrame} durationInFrames={dur}>
            <Audio src={seg.src} />
          </Sequence>
        )
      })}

      {allScenes.map((scene, sceneIndex) => {
        let startTime: number
        let endTime: number
        if (scene.time_range && scene.time_range.length >= 2) {
          ;[startTime, endTime] = scene.time_range
        } else if (scene.narration?.length) {
          const first = scene.narration[0]
          const last = scene.narration[scene.narration.length - 1]
          startTime = first.time_start ?? 0
          endTime = last.time_end ?? (last.time_start ?? 0) + 3.0
        } else {
          startTime = sceneIndex * 10.0
          endTime = startTime + 5.0
        }

        const startFrame = Math.round(startTime * fps)
        const duration = Math.round((endTime - startTime) * fps)
        const durationInFrames = duration <= 0 ? Math.round(fps) : duration

        const SceneComp = sceneComponents[scene.id]

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={durationInFrames}
            name={scene.id}
          >
            {SceneComp ? (
              <SceneComp
                sceneStartOffset={startTime}
                narrations={scene.narration}
                animations={scene.animations}
                sceneContent={scene.content}
                scene={scene}
              />
            ) : (
              <MissingSceneComponent scene={scene} />
            )}
          </Sequence>
        )
      })}
    </AbsoluteFill>
  )
}
