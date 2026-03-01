import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const flightdelaystatistic_SceneClosingComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419', // Solid background as per example and single color provided
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Centers content vertically within the padded area
        alignItems: 'center',    // Centers content horizontally
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // Top: 0, Right: 80, Bottom: 80 (for subtitles), Left: 80
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Within 56-72px range
          fontWeight: 800, // Within 700-900 range
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 20, // Space between title and summary
          maxWidth: '80%', // Ensures title doesn't span full width
          lineHeight: 1.2,
        }}
      >
        感谢观看
      </div>

      {/* Summary text based on narration */}
      <div
        style={{
          fontSize: 22, // Within 20-24px range
          fontWeight: 400, // Within 400-500 range
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%', // Ensures summary text doesn't span full width
          lineHeight: 1.6,
          opacity: 0.9, // Slight opacity for secondary text
        }}
      >
        总体来看，航空公司、目的地和日期是影响航班延误的关键因素，值得持续关注。
      </div>
    </AbsoluteFill>
  );
};