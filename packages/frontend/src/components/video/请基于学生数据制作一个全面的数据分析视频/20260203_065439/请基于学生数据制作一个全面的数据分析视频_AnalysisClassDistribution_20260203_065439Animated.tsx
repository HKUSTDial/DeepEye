import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 23.0;
  
  // Animation configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation - bars grow from bottom showing class distribution",
      "time_start": 23.0,
      "duration": 3.2
    }
  ];

  // Subtitle configuration
  const narrations = [
    {
      "text": "最后看各班级的学生分布。",
      "time_start": 23.0,
      "time_end": 26.0
    },
    {
      "text": "所有班级人数完全相等，每班均为5人，显示出高度统一的班级规模。",
      "time_start": 26.0,
      "time_end": 29.0
    }
  ];

  // Helper function to get current narration
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  // Hardcoded data
  const data = [
    {
      "class_name": "高一(1)班",
      "count": 5
    },
    {
      "class_name": "高一(2)班",
      "count": 5
    },
    {
      "class_name": "高二(1)班",
      "count": 5
    },
    {
      "class_name": "高三(1)班",
      "count": 5
    }
  ];
  
  // Extract field names from data_binding
  const xField = 'class_name';
  const yField = 'count';
  
  // Color configuration - using uniform class distribution theme with purple/blue accents
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const barColor = '#8b5cf6';  // Purple for uniform distribution analysis
  const highlightColor = '#a855f7';  // Lighter purple accent
  const gridColor = '#2d3748';
  const axisColor = '#718096';
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const avgValue = d3.mean(data, (d: any) => d[yField]) || 0;
  
  // D3 scales for categorical bar chart
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.3);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2])
      .range([320, 0]);
    return { xScale, yScale };
  }, [data, maxValue]);
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create uniform distribution gradient
    const gradient = defs.append('linearGradient')
      .attr('id', 'uniformGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#a855f7');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#8b5cf6');
    
    // Glow effect for uniform bars
    const glow = defs.append('filter').attr('id', 'glow');
    glow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 0)
      .attr('stdDeviation', 8)
      .attr('flood-color', '#a855f7')
      .attr('flood-opacity', 0.6);
    
    // Draw chart
    const g = svg.append('g').attr('transform', 'translate(90, 60)');
    const {xScale, yScale} = scales;
    
    // Draw Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-800)
        .tickFormat(() => "")
        .ticks(5)
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.3);
    
    // Draw bars - all equal, emphasize uniformity - initial state for animation
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', 320) // Start from bottom
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with 0 height
      .attr('fill', 'url(#uniformGradient)')
      .attr('rx', 6)
      .style('filter', 'url(#glow)')
      .attr('stroke', highlightColor)
      .attr('stroke-width', 2)
      .style('opacity', 0); // Start invisible
    
    // Value labels on top of bars - initial state for animation
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField])
      .attr('fill', highlightColor)
      .style('font-size', '20px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible
    
    // Category labels below chart - initial state for animation
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible
    
    // Y-axis label - initial state for animation
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 160)')
      .text('学生人数')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible
    
    // Uniformity indicator - initial state for animation
    g.append('text')
      .attr('class', 'uniformity-label')
      .attr('x', 400)
      .attr('y', 40)
      .attr('text-anchor', 'middle')
      .text('完全均衡分布')
      .attr('fill', highlightColor)
      .style('font-size', '18px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible
    
    // Clean up grid
    g.select('.grid-y').select('.domain').remove();
    
  }, [scales, data]);

  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale} = scales;
    const innerHeight = 320;  // Chart height

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // Animation completed - force all elements to final state
      if (frame >= animEnd) {
        // Bar Chart elements
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis-label, .uniformity-label').style('opacity', 1);
        
        // Continue executing other animations (don't return)
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

        // Bars grow sequentially
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;  // Each bar delays 0.12 seconds
          const animDuration = 0.6;   // Single bar animation duration 0.6 seconds
          const barStart = i * delayPerBar;
          const barEnd = barStart + animDuration;

          if (totalTime >= barStart && totalTime <= barEnd) {
            // Bar animation in progress
            const barProgress = (totalTime - barStart) / animDuration;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            // Bar animation completed
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Labels delayed fade in (category + value simultaneously)
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3;  // Additional delay 0.3 seconds
          const animDuration = 0.4;
          const labelStart = i * delayPerBar + labelDelay;
          const labelEnd = labelStart + animDuration;

          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });
        
        // Axis labels fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.y-axis-label, .uniformity-label').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis-label, .uniformity-label').style('opacity', 1);
        }
      }
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset]);
  
  return (
    <AbsoluteFill style={{ 
      background: '#0f1419',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px'
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}>
        各班级学生人数分布
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={980} 
        height={500} 
        style={{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />

      {/* Subtitle display */}
      {getCurrentNarration() && (
        <div style={{
          position: 'absolute',
          bottom: 35,
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(10px)',
          padding: '15px 30px',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          color: '#ffffff',
          fontSize: '17px',
          fontWeight: '500',
          lineHeight: '1.45',
          maxWidth: '90%',
          textAlign: 'center',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
        }}>
          {getCurrentNarration().text}
        </div>
      )}
    </AbsoluteFill>
  );
};