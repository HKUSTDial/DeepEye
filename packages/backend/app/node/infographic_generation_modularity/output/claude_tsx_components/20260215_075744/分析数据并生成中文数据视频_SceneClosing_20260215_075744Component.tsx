import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 分析数据并生成中文数据视频_SceneClosingComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
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
          fontSize: 64, // Within 56-72px
          fontWeight: 800, // Within 700-900
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 20,
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        总结与展望
      </div>

      {/* Optional summary text - using the provided narration here */}
      <div
        style={{
          fontSize: 22, // Within 20-24px
          fontWeight: 400, // Within 400-500
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 1, // Full opacity as per requirements
        }}
      >
        通过本次分析，我们发现MQ航空面临最严重的延误问题，而AA航空表现优异；同时，目的地城市也对航班准点率有显著影响。
      </div>
    </AbsoluteFill>
  );
};