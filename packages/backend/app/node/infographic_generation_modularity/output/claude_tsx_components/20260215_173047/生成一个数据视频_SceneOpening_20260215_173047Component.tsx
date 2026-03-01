import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 生成一个数据视频_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Vertically center content initially
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px', // Horizontal padding
      }}
    >
      {/* Container to shift title/subtitle up, reserving space at the bottom */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          // Shift content up by half of the reserved bottom space (80px / 2 = 40px)
          transform: 'translateY(-40px)', 
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
            maxWidth: '80%', // Limit width for better readability on wider screens
            lineHeight: 1.2, // Adjust line height for large text
          }}
        >
          生成一个数据视频
        </div>

        {/* Subtitle */}
        <div
          style={{
            fontSize: 28, // Within 24-32px range
            fontWeight: 400, // Within 400-500 range
            color: '#e0e0e0',
            textAlign: 'center',
            maxWidth: '70%', // Limit width for better readability
            lineHeight: 1.5, // Adjust line height for readability
          }}
        >
          Data Analysis
        </div>
      </div>
    </AbsoluteFill>
  );
};