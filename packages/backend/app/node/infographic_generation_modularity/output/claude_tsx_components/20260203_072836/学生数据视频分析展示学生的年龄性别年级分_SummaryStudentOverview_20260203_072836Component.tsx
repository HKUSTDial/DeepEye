import React from 'react';
import { AbsoluteFill } from 'remotion';

interface StatCard {
  number: string;
  label: string;
  color: string;
}

interface SceneProps {
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{text: string; time_start: number; time_end: number}>; // Narration subtitles (will be used in animation version)
  title?: string; // Scene title (optional)
}

export const 学生数据视频分析展示学生的年龄性别年级分_SummaryStudentOverviewComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0, title = "学生数据统计概览" }) => {
  const cards: StatCard[] = [
    {
      number: "20",
      label: "学生总人数",
      color: "#5b8ff9"
    },
    {
      number: "18.5",
      label: "平均年龄",
      color: "#61ddaa"
    },
    {
      number: "1:1.2",
      label: "男女比例",
      color: "#f6bd16"
    },
    {
      number: "4",
      label: "年级数量",
      color: "#e85d75"
    }
  ];

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
        {cards.map((card, index) => (
          <div
            key={index}
            style={{
              background: 'rgba(26, 32, 44, 0.8)',
              border: `2px solid ${card.color}`,
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
        ))}
      </div>
    </AbsoluteFill>
  );
};