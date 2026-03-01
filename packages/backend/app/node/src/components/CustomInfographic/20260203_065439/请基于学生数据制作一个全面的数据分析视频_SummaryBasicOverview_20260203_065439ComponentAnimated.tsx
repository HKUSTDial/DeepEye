import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';

interface StatCard {
  number: string;
  label: string;
  color: string;
}

interface Animation {
  id: string;
  type: 'entrance' | 'emphasis';
  effect: string;
  time_start: number;
  duration: number;
  target_data?: {
    card_index?: number;
    data_filter?: {
      card_id?: string;
    };
  };
  style?: {
    direction?: string;
    stagger_delay?: number;
    intensity?: number;
  };
}

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
  animations?: Animation[];
  title?: string;
}

export const 请基于学生数据制作一个全面的数据分析视频_SummaryBasicOverviewComponent: React.FC<SceneProps> = ({ 
  sceneStartOffset = 0, 
  title = "数据统计概览",
  narrations = [],
  animations = []
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // CRITICAL: In Sequence, frame starts from 0 (local frame number)
  const relativeTime = frame / fps;
  const absoluteTime = sceneStartOffset + relativeTime;

  const cards: StatCard[] = [
    {
      number: "20",
      label: "总记录数",
      color: "#5b8ff9"
    },
    {
      number: "2",
      label: "性别类型数",
      color: "#61ddaa"
    },
    {
      number: "3",
      label: "年级数量",
      color: "#65789b"
    },
    {
      number: "5",
      label: "班级数量",
      color: "#f6bd16"
    }
  ];

  // Card ID mapping for emphasis animations
  const cardIdMap: { [key: string]: number } = {
    'total_records': 0,
    'unique_genders': 1,
    'unique_grades': 2,
    'unique_classes': 3
  };

  // Extract entrance animation from config
  const entranceAnim = useMemo(() => {
    return animations.find(a => a.type === 'entrance' && a.effect === 'fade_in');
  }, [animations]);
  
  // Get animation parameters from config (or use defaults)
  const staggerDelay = entranceAnim?.style?.stagger_delay || 0.15;
  const entranceStartFrame = entranceAnim 
    ? (entranceAnim.time_start - sceneStartOffset) * fps 
    : 0;
  const entranceDurationFrames = entranceAnim 
    ? entranceAnim.duration * fps 
    : 0.5 * fps;
  
  // Extract emphasis animations
  const emphasisAnims = useMemo(() => {
    return animations.filter(a => a.type === 'emphasis' && a.effect === 'pulse');
  }, [animations]);
  
  // Function to calculate card entrance animation progress
  const getCardProgress = (index: number) => {
    if (!entranceAnim) {
      // Fallback: use default animation
      const cardDelay = 0.2;
      const cardInterval = 0.15;
      const cardAnimDuration = 0.5;
      const cardStartTime = cardDelay + index * cardInterval;
      return Math.max(0, Math.min(1, (relativeTime - cardStartTime) / cardAnimDuration));
    }
    
    // Use config animation timing
    const cardStartFrame = entranceStartFrame + index * (staggerDelay * fps);
    return interpolate(
      frame,
      [cardStartFrame, cardStartFrame + entranceDurationFrames],
      [0, 1],
      {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
        easing: Easing.out(Easing.cubic),
      }
    );
  };
  
  // Function to calculate card emphasis/pulse effect
  const getCardEmphasis = (cardIndex: number) => {
    const emphasisAnim = emphasisAnims.find(a => {
      if (a.target_data?.card_index !== undefined) {
        return a.target_data.card_index === cardIndex;
      }
      if (a.target_data?.data_filter?.card_id) {
        return cardIdMap[a.target_data.data_filter.card_id] === cardIndex;
      }
      return false;
    });
    
    if (!emphasisAnim) return { scale: 1, borderWidth: 2, boxShadow: 'none' };
    
    const animStartFrame = (emphasisAnim.time_start - sceneStartOffset) * fps;
    const animDuration = emphasisAnim.duration * fps;
    const isActive = frame >= animStartFrame && frame < animStartFrame + animDuration;
    
    if (!isActive) return { scale: 1, borderWidth: 2, boxShadow: 'none' };
    
    const intensity = emphasisAnim.style?.intensity || 0.1;
    const progress = (frame - animStartFrame) / animDuration;
    const pulse = Math.sin(progress * Math.PI * 8) * intensity + 1;
    const borderWidth = 2 + intensity * 4;
    const cardColor = cards[cardIndex].color;
    const boxShadow = `0 0 ${20 + intensity * 20}px ${cardColor}40`;
    
    return { scale: pulse, borderWidth, boxShadow };
  };
  
  // Subtitle logic
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
        padding: '0 60px 130px 60px', // Bottom padding for subtitles
      }}
    >
      {/* Title - Display if provided */}
      {title && (
        <div
          style={{
            position: 'absolute',
            top: 80,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 10,
          }}
        >
          <h2
            style={{
              fontSize: 42,
              fontWeight: 700,
              color: '#ffffff',
              margin: 0,
              textAlign: 'center',
              letterSpacing: '0.5px',
            }}
          >
            {title}
          </h2>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          flexDirection: 'row',
          gap: 20,
          justifyContent: 'center',
          alignItems: 'center',
          width: '100%',
          maxWidth: '1400px',
          flexWrap: 'nowrap', // Prevent wrapping
          marginTop: title ? 60 : 0, // Add top margin if title exists
          padding: '0 40px',
          boxSizing: 'border-box',
        }}
      >
        {cards.map((card, index) => {
          const progress = getCardProgress(index);
          const opacity = progress;
          const scale = 0.8 + 0.2 * progress;
          const y = (1 - progress) * 30;
          const emphasis = getCardEmphasis(index);
          
          return (
            <div
              key={index}
              style={{
                background: 'rgba(26, 32, 44, 0.8)',
                border: `${emphasis.borderWidth}px solid ${card.color}`,
                borderRadius: 12,
                padding: '28px 20px', // Reduced padding
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                flex: '1 1 0%', // Use flex for equal width distribution
                minWidth: 0, // Allow flex to shrink
                width: 0, // Let flexbox control width
                boxSizing: 'border-box',
                opacity: opacity,
                transform: `scale(${scale * emphasis.scale}) translateY(${y}px)`,
                boxShadow: emphasis.boxShadow,
              }}
            >
              {/* Number */}
              <div
                style={{
                  fontSize: 52,
                  fontWeight: 800,
                  color: card.color,
                  marginBottom: 12,
                  lineHeight: 1,
                }}
              >
                {card.number}
              </div>

              {/* Label */}
              <div
                style={{
                  fontSize: 15, // Reduced font size
                  fontWeight: 500,
                  color: '#e0e0e0',
                  textAlign: 'center',
                  lineHeight: 1.3, // Reduced line height
                  wordWrap: 'break-word',
                  overflowWrap: 'break-word',
                  width: '100%',
                  maxWidth: '100%',
                }}
              >
                {card.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Subtitles */}
      {currentNarration && (
        <div style={{ position: 'absolute', bottom: 35, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
          <div style={{ background: 'rgba(0, 0, 0, 0.75)', padding: '12px 24px', borderRadius: 8, maxWidth: '90%', textAlign: 'center' }}>
            <span style={{ color: '#ffffff', fontSize: 17, fontWeight: 500, lineHeight: 1.45 }}>
              {currentNarration.text}
            </span>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};