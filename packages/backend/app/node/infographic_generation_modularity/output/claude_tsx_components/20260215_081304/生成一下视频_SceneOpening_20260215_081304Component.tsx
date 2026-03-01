import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 生成一下视频_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        paddingLeft: 80,
        paddingRight: 80,
        paddingBottom: 80, // Reserve bottom 80px for narration subtitles
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64,
          fontWeight: 800, // 700-900
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24, // 20-30px spacing
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        生成一下视频
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28, // 24-32px
          fontWeight: 400, // 400-500
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.5,
        }}
      >
        Data Analysis
      </div>
    </AbsoluteFill>
  );
};