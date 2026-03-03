import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';

interface StatCard {
  title: string;
  value: string;
  subtitle: string;
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

export const Createavideoreportex_SceneStatsComponent: React.FC<SceneProps> = ({ 
  sceneStartOffset = 0, 
  narrations = [],
  animations = [],
  title = "Q4 2025 Key Metrics" 
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // CRITICAL: In Sequence, frame starts from 0 (local frame number)
  const relativeTime = frame / fps;
  const absoluteTime = sceneStartOffset + relativeTime;
  
  // 优化后的卡片数据：只保留前4个，学术风配色（蓝紫青色系）
  const cards: StatCard[] = [
    {
      "title": "Peak Monthly Revenue",
      "value": "$892,402",
      "subtitle": "December 2025",
      "color": "#2563eb" // 深蓝
    },
    {
      "title": "Top Product Sales",
      "value": "$2.42M",
      "subtitle": "Laptop Pro X",
      "color": "#0891b2" // 青色
    },
    {
      "title": "Electronics Revenue",
      "value": "$6.05M",
      "subtitle": "79% of Q4 total",
      "color": "#7c3aed" // 紫色
    },
    {
      "title": "Leading Region",
      "value": "$2.07M",
      "subtitle": "Latin America",
      "color": "#0d9488" // 青绿色
    }
  ];

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
    const emphasisAnim = emphasisAnims.find(a => a.target_data?.card_index === cardIndex);
    if (!emphasisAnim) return 1;
    
    const animStartFrame = (emphasisAnim.time_start - sceneStartOffset) * fps;
    const animDuration = emphasisAnim.duration * fps;
    const isActive = frame >= animStartFrame && frame < animStartFrame + animDuration;
    
    if (!isActive) return 1;
    
    const intensity = emphasisAnim.style?.intensity || 0.1;
    const progress = (frame - animStartFrame) / animDuration;
    const pulse = Math.sin(progress * Math.PI * 8) * intensity + 1;
    return pulse;
  };
  
  // Subtitle logic
  const currentNarration = narrations.find(
    n => absoluteTime >= n.time_start && absoluteTime < n.time_end
  );

  return (
    <AbsoluteFill
      style={{
        background: '#ffffff',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 60px 130px 60px',
      }}
    >
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
              color: '#111827',
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
          gap: 24, // 增加间距，因为只有4个卡片了
          justifyContent: 'center',
          alignItems: 'center',
          width: '100%',
          maxWidth: '1200px', // 限制最大宽度，保持紧凑
          flexWrap: 'nowrap',
          marginTop: title ? 60 : 0,
          padding: '0 20px',
          boxSizing: 'border-box',
        }}
      >
        {cards.map((card, index) => {
          const progress = getCardProgress(index);
          const emphasis = getCardEmphasis(index);
          const opacity = progress;
          const scale = (0.8 + 0.2 * progress) * emphasis;
          const y = (1 - progress) * 30;
          
          return (
            <div
              key={index}
              style={{
                background: '#f8fafc', // 极浅灰背景
                border: '1px solid #e2e8f0', // 细边框
                borderRadius: 16,
                padding: '32px 24px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                flex: '1 1 0%',
                minWidth: 0,
                width: 0,
                boxSizing: 'border-box',
                opacity: opacity,
                transform: `scale(${scale}) translateY(${y}px)`,
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)', // 柔和阴影
              }}
            >
              <div
                style={{
                  fontSize: 44, // 稍微缩小字号防止溢出 (原52)
                  fontWeight: 800,
                  color: card.color, // 使用深色系的强调色
                  marginBottom: 16,
                  lineHeight: 1,
                  textAlign: 'center',
                }}
              >
                {card.value}
              </div>

              <div
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: '#374151', // 深灰
                  textAlign: 'center',
                  lineHeight: 1.3,
                  width: '100%',
                  marginBottom: 8,
                }}
              >
                {card.title}
              </div>

              <div
                style={{
                  fontSize: 14,
                  fontWeight: 400,
                  color: '#6b7280', // 中灰
                  textAlign: 'center',
                  lineHeight: 1.2,
                  width: '100%',
                }}
              >
                {card.subtitle}
              </div>
            </div>
          );
        })}
      </div>

      {/* Subtitles */}
      {currentNarration && (
        <div style={{ position: 'absolute', bottom: 35, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
          <div style={{ background: 'rgba(0, 0, 0, 0.75)', padding: '12px 24px', borderRadius: 8, maxWidth: '90%', textAlign: 'center' }}>
            <span style={{ color: '#ffffff',
                fontSize: 17, fontWeight: 500, lineHeight: 1.45 }}>
              {currentNarration.text}
            </span>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
