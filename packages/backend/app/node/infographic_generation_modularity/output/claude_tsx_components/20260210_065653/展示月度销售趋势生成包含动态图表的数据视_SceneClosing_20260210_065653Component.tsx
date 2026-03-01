import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const 展示月度销售趋势生成包含动态图表的数据视_SceneClosingComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
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
          fontSize: 72,
          fontWeight: 800,
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24,
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        感谢观看
      </div>

      {/* Summary text */}
      <div
        style={{
          fontSize: 22,
          fontWeight: 400,
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 0.9,
        }}
      >
        数据驱动决策，共创美好未来
      </div>
    </AbsoluteFill>
  );
};