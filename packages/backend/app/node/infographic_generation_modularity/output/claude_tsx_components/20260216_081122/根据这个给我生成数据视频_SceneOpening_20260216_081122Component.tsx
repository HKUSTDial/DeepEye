import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 根据这个给我生成数据视频_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Centers content vertically within the padded area
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // Left/Right 80px, Bottom 80px reserved for narration
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Large, eye-catching
          fontWeight: 800, // Bold
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24, // Spacing between title and subtitle
          maxWidth: '80%', // Ensures content doesn't stretch too wide
          lineHeight: 1.2,
        }}
      >
        航班延误数据分析
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28, // Smaller, secondary text
          fontWeight: 400, // Regular weight
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%', // Ensures content doesn't stretch too wide
          lineHeight: 1.5,
        }}
      >
        洞察航空公司与目的地表现
      </div>
    </AbsoluteFill>
  );
};