import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 展示月度销售趋势生成包含动态图表的数据视_SceneClosingComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // 底部80px padding for subtitles
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64,
          fontWeight: 800,
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 20,
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        Thank You
      </div>

      {/* Optional summary text */}
      <div
        style={{
          fontSize: 22,
          fontWeight: 400,
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 0.9,
        }}
      >
        感谢观看我们的月度销售趋势分析
      </div>
    </AbsoluteFill>
  );
};