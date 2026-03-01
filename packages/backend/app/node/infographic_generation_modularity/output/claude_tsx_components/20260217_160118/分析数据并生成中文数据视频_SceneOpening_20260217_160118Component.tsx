import React from 'react';
import { AbsoluteFill } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const 分析数据并生成中文数据视频_SceneOpeningComponent: React.FC<SceneProps> = ({ sceneStartOffset = 0 }) => {
  return (
    <AbsoluteFill
      style={{
        background: '#0f1419',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center', // Centers content vertically within available space
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        paddingTop: 0,
        paddingLeft: 80,
        paddingRight: 80,
        paddingBottom: 80, // Reserves 80px at the bottom, shifting content upwards
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Within 56-72px
          fontWeight: 800, // Within 700-900
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24, // Within 20-30px
          maxWidth: '80%',
          lineHeight: 1.2,
        }}
      >
        航班延误分析报告
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28, // Within 24-32px
          fontWeight: 400, // Within 400-500
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.5,
        }}
      >
        航空公司与目的地表现洞察
      </div>
    </AbsoluteFill>
  );
};