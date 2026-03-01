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
        background: '#0f1419', // Background color as specified
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif", // Modern sans-serif font
        padding: '0 80px 80px 80px', // Reserve BOTTOM 80px for narration subtitles
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Large font size (56-72px)
          fontWeight: 800, // Bold font weight (700-900)
          color: '#ffffff', // White title color
          textAlign: 'center',
          marginBottom: 20,
          maxWidth: '80%',
          lineHeight: 1.2,
          opacity: 1, // Full opacity
        }}
      >
        总结与展望
      </div>

      {/* Optional summary text / Tagline */}
      <div
        style={{
          fontSize: 22, // Small font size (20-24px)
          fontWeight: 400, // Regular font weight (400-500)
          color: '#e0e0e0', // Secondary text color
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 1, // Full opacity
        }}
      >
        Data-driven insights for better decisions
      </div>
    </AbsoluteFill>
  );
};