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
        background: '#0f1419', // Background color as specified
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
          fontSize: 64, // Within 56-72px range
          fontWeight: 800, // Within 700-900 range
          color: '#ffffff', // Title color as specified
          textAlign: 'center',
          marginBottom: 20,
          maxWidth: '80%',
          lineHeight: 1.2,
          opacity: 1, // Full opacity as no animations yet
        }}
      >
        感谢观看
      </div>

      {/* Summary text using narration content */}
      <div
        style={{
          fontSize: 22, // Within 20-24px range
          fontWeight: 400, // Within 400-500 range
          color: '#e0e0e0', // Secondary text color as specified
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 1, // Full opacity as no animations yet
        }}
      >
        通过本次分析，我们发现航空公司选择、目的地城市和日期趋势对航班延误有显著影响。
      </div>
    </AbsoluteFill>
  );
};