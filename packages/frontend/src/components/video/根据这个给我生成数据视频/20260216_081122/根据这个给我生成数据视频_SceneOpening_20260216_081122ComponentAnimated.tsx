import { useCurrentFrame, useVideoConfig } from 'remotion';
import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 根据这个给我生成数据视频_SceneOpeningComponent: React.FC<SceneProps> = ({ 
  sceneStartOffset = 0,
  narrations = []
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // CRITICAL: In Sequence, frame starts from 0 (local frame number)
  // relativeTime is time relative to scene start (in seconds)
  const relativeTime = frame / fps;
  
  // absoluteTime is used for subtitle matching (absolute video time)
  const absoluteTime = sceneStartOffset + relativeTime;
  
  // Animation parameters
  const titleDelay = 0.2;      // Title appears after 0.2s
  const subtitleDelay = 0.5;   // Subtitle appears after 0.5s
  const animDuration = 0.6;    // Animation duration: 0.6s
  
  // Title animation (fade in + slide up)
  const titleProgress = Math.max(0, Math.min(1, (relativeTime - titleDelay) / animDuration));
  const titleOpacity = titleProgress;
  const titleY = (1 - titleProgress) * 20; // Slide up 20px
  
  // Subtitle animation (fade in + slide up)
  const subtitleProgress = Math.max(0, Math.min(1, (relativeTime - subtitleDelay) / animDuration));
  const subtitleOpacity = subtitleProgress;
  const subtitleY = (1 - subtitleProgress) * 20;
  
  // Subtitle logic: find current narration based on absoluteTime
  const currentNarration = narrations.find(
    n => absoluteTime >= n.time_start && absoluteTime < n.time_end
  );
  
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Centers content vertically within the padded area
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // Left/Right 80px, Bottom 80px reserved for narration
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Large, eye-catching
          fontWeight: 800, // Bold
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24, // Spacing between title and subtitle
          maxWidth: '80%', // Ensures content doesn't stretch too wide
          lineHeight: 1.2,
          // Animation styles
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        航班延误数据分析
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28, // Smaller, secondary text
          fontWeight: 400, // Regular weight
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%', // Ensures content doesn't stretch too wide
          lineHeight: 1.5,
          // Animation styles
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
        }}
      >
        洞察航空公司与目的地表现
      </div>

      {/* Narration Subtitles */}
      {currentNarration && (
        <div
          style={{
            position: 'absolute',
            bottom: 35,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              background: 'rgba(0, 0, 0, 0.75)',
              padding: '12px 24px',
              borderRadius: 8,
              maxWidth: '90%',
              textAlign: 'center',
            }}
          >
            <span
              style={{
                color: '#ffffff',
                fontSize: 17,
                fontWeight: 500,
                lineHeight: 1.45,
                fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
              }}
            >
              {currentNarration.text}
            </span>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};