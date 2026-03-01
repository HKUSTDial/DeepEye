import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const flightdelaystatistic_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Centers the contentWrapper vertically
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px', // Horizontal padding for content
      }}
    >
      {/* Wrapper for title and subtitle to adjust vertical position for narration space */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          transform: 'translateY(-40px)', // Shift content up by half of the 80px narration space
          width: '100%', // Ensure it takes full width for text centering
        }}
      >
        {/* Main Title */}
        <div
          style={{
            fontSize: 64, // Within 56-72px range
            fontWeight: 800, // Within 700-900 range
            color: '#ffffff',
            textAlign: 'center',
            marginBottom: 24, // Within 20-30px spacing
            maxWidth: '80%',
            lineHeight: 1.2,
          }}
        >
          航班延误洞察
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
          航空公司与目的地表现分析
        </div>
      </div>
    </AbsoluteFill>
  );
};