/**
 * App - entry point for the video preview container app.
 * Imports config.json and scene_registry.ts that are injected by VideoDeployService at deploy time.
 */
import { Player } from '@remotion/player'
import { VideoPlayer, type VideoConfig } from './VideoPlayer'
import config from './config.json'
import { sceneComponents } from './scene_registry'

const videoConfig = config as unknown as VideoConfig
const fps = videoConfig?.meta?.fps ?? 30
const width = videoConfig?.meta?.width ?? 1920
const height = videoConfig?.meta?.height ?? 1080
const durationInFrames = Math.max(1, Math.ceil((videoConfig?.meta?.video_duration ?? 10) * fps))

export function App() {
  return (
    <div
      data-app="deepeye-video-preview"
      style={{
        width: '100vw',
        height: '100vh',
        background: '#f8fafc',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
      }}
    >
      <Player
        component={VideoPlayer}
        inputProps={{ config: videoConfig, sceneComponents }}
        durationInFrames={durationInFrames}
        fps={fps}
        compositionWidth={width}
        compositionHeight={height}
        style={{ width: '100%', maxWidth: Math.min(960, width) }}
        controls
        autoPlay
        loop
        acknowledgeRemotionLicense
      />
    </div>
  )
}
