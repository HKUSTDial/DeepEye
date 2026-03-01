import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const 分析数据并生成中文数据视频_SceneClosingComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419', // Solid background as per the given color
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // Bottom 80px padding for subtitles
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Large font size
          fontWeight: 800, // Bold font weight
          color: '#ffffff', // White color
          textAlign: 'center',
          marginBottom: 20,
          maxWidth: '80%',
          lineHeight: 1.2,
          opacity: 1, // Full opacity
        }}
      >
        总结与展望
      </div>

      {/* Optional summary text / Tagline */}
      <div
        style={{
          fontSize: 22, // Smaller font size
          fontWeight: 400, // Regular font weight
          color: '#e0e0e0', // Secondary text color
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 1, // Full opacity
        }}
      >
        Data-driven insights for better decisions
      </div>
    </AbsoluteFill>
  );
};