import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

interface SceneProps {
  sceneStartOffset?: number;
  narrations?: Array<{text: string; time_start: number; time_end: number}>;
}

export const 展示月度销售趋势生成包含动态图表的数据视_SceneOpeningComponent: React.FC<SceneProps> = ({ 
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
  const titleDelay = 0.2;      // Title appears after 0.2