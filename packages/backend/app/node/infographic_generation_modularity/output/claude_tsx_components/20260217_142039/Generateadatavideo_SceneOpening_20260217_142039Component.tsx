import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const Generateadatavideo_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
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
        paddingBottom: 80, // Reserve 80px at the bottom for narration subtitles
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Within 56-72px range
          fontWeight: 800, // Within 700-900 range
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24, // Within 20-30px range
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        航空客流洞察
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28, // Within 24-32px range
          fontWeight: 400, // Within 400-500 range
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.5,
        }}
      >
        每日趋势与波动分析
      </div>
    </AbsoluteFill>
  );
};