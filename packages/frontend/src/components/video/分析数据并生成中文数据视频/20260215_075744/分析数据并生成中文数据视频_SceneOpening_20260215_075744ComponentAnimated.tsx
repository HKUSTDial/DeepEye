import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const 分析数据并生成中文数据视频_SceneOpeningComponent: React.FC<SceneProps> = ({ 
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
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
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
            opacity: subtitleOpacity,
            transform: `translateY(${subtitleY}px)`,
          }}
        >
          航空公司与目的地表现一览
        </div>
      </div>
      {/* The bottom 80px area is implicitly reserved below this content due to the translateY */}

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