import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 分析数据并生成中文数据视频_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Centers the contentWrapper vertically
        alignItems: 'center', // Centers the contentWrapper horizontally
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px', // Horizontal padding for the entire scene
      }}
    >
      {/* Content Wrapper to adjust for narration space at the bottom */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          transform: 'translateY(-40px)', // Shifts content up by 40px to reserve 80px at the bottom
          width: '100%', // Allows maxWidth on children to work within the AbsoluteFill's padding
        }}
      >
        {/* Main Title */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 800,
            color: '#ffffff',
            textAlign: 'center',
            marginBottom: 24, // Spacing between title and subtitle (20-30px range)
            maxWidth: '80%', // Constrain width for readability
            lineHeight: 1.2,
          }}
        >
          航班延误数据分析
        </div>

        {/* Subtitle */}
        <div
          style={{
            fontSize: 28,
            fontWeight: 400,
            color: '#e0e0e0',
            textAlign: 'center',
            maxWidth: '70%', // Constrain width for readability
            lineHeight: 1.5,
          }}
        >
          航空公司与目的地表现一览
        </div>
      </div>
      {/* The bottom 80px area is implicitly reserved below this content due to the translateY */}
    </AbsoluteFill>
  );
};