import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const Generateadatavideoba_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px',
        paddingBottom: 80, // Reserve bottom 80px for narration subtitles
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64,
          fontWeight: 800,
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24, // Spacing between title and subtitle
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        2015航班延误洞察
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28,
          fontWeight: 400,
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.5,
        }}
      >
        航空公司与目的地表现分析
      </div>
    </AbsoluteFill>
  );
};