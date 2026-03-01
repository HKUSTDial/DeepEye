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
        justifyContent: 'center', // Centers content vertically within the available space
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        paddingLeft: 80, // Horizontal padding
        paddingRight: 80, // Horizontal padding
        paddingBottom: 80, // Reserves 80px at the bottom, shifting the "center" point upwards
      }}
    >
      {/* Main Title */}
      <div
        style={{
          fontSize: 64, // Large, eye-catching
          fontWeight: 800, // Bold
          color: '#ffffff',
          textAlign: 'center',
          marginBottom: 24, // Spacing between title and subtitle
          maxWidth: '80%', // Constrain width for better readability
          lineHeight: 1.2,
        }}
      >
        航班延误深度解析
      </div>

      {/* Subtitle */}
      <div
        style={{
          fontSize: 28, // Smaller secondary text
          fontWeight: 400, // Regular weight
          color: '#e0e0e0',
          textAlign: 'center',
          maxWidth: '70%', // Constrain width for better readability
          lineHeight: 1.5,
        }}
      >
        洞察航空公司与目的地表现
      </div>
    </AbsoluteFill>
  );
};