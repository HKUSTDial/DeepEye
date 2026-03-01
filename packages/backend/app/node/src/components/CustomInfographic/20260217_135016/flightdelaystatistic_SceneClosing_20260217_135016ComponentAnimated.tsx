import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const flightdelaystatistic_SceneClosingComponent: React.FC<SceneProps> = ({
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
        background: '#0f1419', // Solid background as per example and single color provided
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Centers content vertically within the padded area
        alignItems: 'center',    // Centers content horizontally
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // Top: 0, Right: 80, Bottom: 80 (for subtitles), Left: 80
      }}
    >
      {/* Main Title - with rich animations */}
      <div
        style={{
          fontSize: 64, // Within 56-72px range
          fontWeight: 800, // Within 700-900 range
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 20, // Space between title and summary
          maxWidth: '80%', // Ensures title doesn't span full width
          lineHeight: 1.2,
          opacity: titleOpacity,
          transform: `translateY(${titleY}px) scale(${titleScale})`,
          transition: 'none', // Disable CSS transitions for Remotion animations
        }}
      >
        感谢观看
      </div>

      {/* Summary text based on narration - with delayed animation */}
      <div
        style={{
          fontSize: 22, // Within 20-24px range
          fontWeight: 400, // Within 400-500 range
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%', // Ensures summary text doesn't span full width
          lineHeight: 1.6,
          // Original opacity: 0.9 is overridden by animated opacity
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          transition: 'none', // Disable CSS transitions
        }}
      >
        总体来看，航空公司、目的地和日期是影响航班延误的关键因素，值得持续关注。
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