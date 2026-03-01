import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 生成一下视频_SceneClosingComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419', // Using solid background as only one color was provided for "gradient"
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // Reserve bottom 80px for narration subtitles
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Within 56-72px range
          fontWeight: 800, // Within 700-900 range
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 20, // Spacing between title and optional tagline
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        Thank You
      </div>

      {/* Optional summary text */}
      <div
        style={{
          fontSize: 22, // Within 20-24px range
          fontWeight: 400, // Within 400-500 range
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 0.9, // Slightly subdued
        }}
      >
        Data-driven insights for better decisions
      </div>
    </AbsoluteFill>
  );
};