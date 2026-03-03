import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const 分析数据并生成中文数据视频_SceneClosingComponent: React.FC<SceneProps> = ({ 
  sceneStartOffset = 0,
  narrations = []
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // CRITICAL: In Sequence, frame starts from 0 (local frame number)
  const relativeTime = frame / fps;
  
  // absoluteTime is used for subtitle matching (absolute video time)
  const absoluteTime = sceneStartOffset + relativeTime;
  
  // Animation parameters - RICH LAYERED ANIMATIONS
  const titleDelay = 0.15;           // Title starts animating at 0.15s
  const titleDuration = 0.8;         // Title animation duration: 0.8s
  const subtitleDelay = 0.5;         // Subtitle starts after title (0.5s delay)
  const subtitleDuration = 0.7;       // Subtitle animation duration: 0.7s
  
  // Title animation: fade in + slide up + scale
  const titleProgress = interpolate(
    frame,
    [titleDelay * fps, (titleDelay + titleDuration) * fps],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }
  );
  
  const titleOpacity = titleProgress;
  const titleY = (1 - titleProgress) * 30;  // Slide up from 30px below
  const titleScale = 0.92 + 0.08 * titleProgress;  // Scale from 0.92 to 1.0
  
  // Subtitle animation: fade in + slide up (delayed)
  const subtitleProgress = interpolate(
    frame,
    [subtitleDelay * fps, (subtitleDelay + subtitleDuration) * fps],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }
  );
  
  const subtitleOpacity = subtitleProgress;
  const subtitleY = (1 - subtitleProgress) * 20;  // Slide up from 20px below
  
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
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // 底部80px padding for subtitles
      }}
    >
      {/* Main Title - with rich animations */}
      <div
        style={{
          fontSize: 64, // Within 56-72px
          fontWeight: 800, // Within 700-900
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 20,
          maxWidth: '80%',
          lineHeight: 1.2,
          opacity: titleOpacity,
          transform: `translateY(${titleY}px) scale(${titleScale})`,
          transition: 'none', // Disable CSS transitions for Remotion animations
        }}
      >
        总结与展望
      </div>

      {/* Optional summary text - with delayed animation */}
      <div
        style={{
          fontSize: 22, // Within 20-24px
          fontWeight: 400, // Within 400-500
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          transition: 'none', // Disable CSS transitions for Remotion animations
        }}
      >
        通过本次分析，我们发现MQ航空面临最严重的延误问题，而AA航空表现优异；同时，目的地城市也对航班准点率有显著影响。
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