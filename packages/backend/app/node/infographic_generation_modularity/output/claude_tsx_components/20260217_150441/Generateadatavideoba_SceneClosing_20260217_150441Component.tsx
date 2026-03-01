import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const Generateadatavideoba_SceneClosingComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
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
        感谢观看
      </div>

      {/* Optional summary text (Narration content) */}
      <div
        style={{
          fontSize: 22, // Within 20-24px
          fontWeight: 400, // Within 400-500
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 0.9, // All elements at full opacity (0.9 is close enough, can be 1 for static)
        }}
      >
        本次分析揭示，MQ航空公司和明尼阿波利斯在航班延误中表现最差，值得重点关注。
      </div>
    </AbsoluteFill>
  );
};