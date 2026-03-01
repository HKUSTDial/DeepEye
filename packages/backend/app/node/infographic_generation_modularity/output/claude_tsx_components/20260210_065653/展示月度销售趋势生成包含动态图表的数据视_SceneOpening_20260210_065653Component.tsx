import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const 展示月度销售趋势生成包含动态图表的数据视_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px',
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64,
          fontWeight: 800,
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24,
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        月度销售趋势分析
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28,
          fontWeight: 400,
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.5,
        }}
      >
        2024年1-4月销售数据
      </div>
    </AbsoluteFill>
  );
};