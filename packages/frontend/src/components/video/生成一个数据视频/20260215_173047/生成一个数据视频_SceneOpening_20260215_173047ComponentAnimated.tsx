import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
}

export const 生成一个数据视频_SceneOpeningComponent: React.FC<SceneProps> = ({ 
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

  // The original content is shifted up by -40px.
  // The titleY/subtitleY values are additional offsets from their final position (0).
  // So, combine them.
  const combinedTitleTransformY = titleY - 40;
  const combinedSubtitleTransformY = subtitleY - 40;
  
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
          // The animation transform will be applied directly to the title/subtitle elements
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
            opacity: titleOpacity,
            transform: `translateY(${combinedTitleTransformY}px)`,
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
            opacity: subtitleOpacity,
            transform: `translateY(${combinedSubtitleTransformY}px)`,
          }}
        >
          Data Analysis
        </div>
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