import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const sceneStartOffset = 5.0;
  
  const data = [
    { month: "1", sum_sales: 1200, count: 1 },
    { month: "2", sum_sales: 1500, count: 1 },
    { month: "3", sum_sales: 1800, count: 1 },
    { month: "4", sum_sales: 2000, count: 1 }
  ];
  
  const animations = [
    {
      id: "entrance_anim",
      type: "entrance",
      effect: "draw_line",
      trigger_narration: 0,
      description: "Line chart entrance animation - line draws from left to right with points appearing sequentially",
      time_start: 5.0,
      duration: 3.2
    },
    {
      id: "emphasis_1200",
      type: "emphasis",
      effect: "pulse",
      trigger_narration: 1,
      target_data: {
        data_filter: {
          month: "1"
        }
      },
      style: {
        intensity: 0.1
      },
      description: "Highlight January data point (1200) when mentioned",
      time_start: 8.0,
      duration: 3.2
    },
    {
      id: "emphasis_2000",
      type: "emphasis",
      effect: "pulse",
      trigger_narration: 1,
      target_data: {
        data_filter: {
          month: "4"
        }
      },
      style: {
        intensity: 0.1
      },
      description: "Highlight April data point (2000) when mentioned",
      time_start: 8.0,
      duration: 3.2
    }
  ];
  
  const narrations = [
    {
      text: "从1月到4月，销售额呈现强劲的上升态势。",
      time_start: 5.0,
      time_end: 8.0
    },
    {
      text: "销售额从1200增长至2000，增幅高达66.7%，展现出卓越的增长动力。",
      time_start: 8.0,
      time_end: 11.0
    }
  ];
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const lineColor = '#10b981';
  const highlightColor = '#34d399';
  const gridColor = '#2a3441';
  const axisColor = '#4a5568';
  const accentGold = '#fbbf24';
  
  const maxValue = d3.max(data, (d: any) => d.sum_sales) || 0;
  const minValue = d3.min(data, (d: any) => d.sum_sales) || 0;
  
  const scales = useMemo(() => {
    const xScale = d3.scaleLinear()
      .domain([1, 4])
      .range([0, 900]);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15])
      .range([340, 0]);
    return { xScale, yScale };
  }, [maxValue]);
  
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const gradient = defs.append('linearGradient')
      .attr('id', 'lineGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', lineColor);
    
    const glowFilter = defs.append('filter').attr('id', 'glow');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'coloredBlur');
    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
    
    const pointShadow = defs.append('filter').attr('id', 'pointShadow');
    pointShadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 2)
      .attr('stdDeviation', 4)
      .attr('flood-opacity', 0.4);
    
    const g = svg.append('g').attr('transform', 'translate(100, 100)');
    const { xScale, yScale } = scales;
    
    g.selectAll('.grid-y')
      .data(yScale.ticks(5))
      .enter()
      .append('line')
      .attr('class', 'grid-y')
      .attr('x1', 0)
      .attr('x2', 900)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4')
      .style('opacity', 0);
    
    const line = d3.line()
      .x((d: any) => xScale(+d.month))
      .y((d: any) => yScale(d.sum_sales))
      .curve(d3.curveMonotoneX);
    
    const area = d3.area()
      .x((d: any) => xScale(+d.month))
      .y0(340)
      .y1((d: any) => yScale(d.sum_sales))
      .curve(d3.curveMonotoneX);
    
    g.append('path')
      .attr('class', 'area-path')
      .datum(data)
      .attr('fill', 'url(#lineGradient)')
      .style('opacity', 0)
      .attr('d', area as any);
    
    g.append('path')
      .attr('class', 'line-path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', lineColor)
      .attr('stroke-width', 3)
      .attr('d', line as any)
      .style('filter', 'url(#glow)')
      .style('opacity', 0);
    
    g.selectAll('.data-point')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'data-point')
      .attr('cx', (d: any) => xScale(+d.month))
      .attr('cy', (d: any) => yScale(d.sum_sales))
      .attr('r', (d: any) => d.sum_sales === maxValue ? 8 : 6)
      .attr('fill', (d: any) => d.sum_sales === maxValue ? accentGold : highlightColor)
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 2)
      .style('filter', 'url(#pointShadow)')
      .style('opacity', 0);
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => xScale(+d.month))
      .attr('y', (d: any) => yScale(d.sum_sales) - 20)
      .attr('text-anchor', 'middle')
      .text((d: any) => d.sum_sales)
      .attr('fill', (d: any) => d.sum_sales === maxValue ? accentGold : textColor)
      .style('font-size', (d: any) => d.sum_sales === maxValue ? '22px' : '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d: any) => d.toString());
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.select('.y-axis').selectAll('line, path')
      .attr('stroke', axisColor)
      .attr('stroke-width', 1)
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -75)
      .attr('y', 170)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -75, 170)')
      .text('销售额')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.selectAll('.month-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'month-label')
      .attr('x', (d: any) => xScale(+d.month))
      .attr('y', 365)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d.month}月`)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', 450)
      .attr('y', 395)
      .attr('text-anchor', 'middle')
      .text('月份')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
  }, [scales, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { xScale, yScale } = scales;
    
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      if (frame >= animEnd) {
        g.select('.line-path').style('opacity', 1);
        g.select('.area-path').style('opacity', 0.15);
        g.selectAll('.data-point').style('opacity', 1);
        g.selectAll('.value-label').style('opacity', 1);
        g.selectAll('.month-label').style('opacity', 1);
        g.selectAll('.grid-y').style('opacity', 0.5);
        g.selectAll('.y-axis text').style('opacity', 1);
        g.selectAll('.y-axis line, .y-axis path').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
      } else if (frame >= animStart) {
        const totalTime = (frame - animStart) / fps;
        const totalDuration = entranceAnim.duration;
        
        const lineDrawDuration = 2.0;
        if (totalTime <= lineDrawDuration) {
          const lineProgress = totalTime / lineDrawDuration;
          const eased = d3.easeCubicOut(lineProgress);
          
          const linePath = g.select('.line-path');
          const totalLength = (linePath.node() as any)?.getTotalLength() || 0;
          
          linePath
            .style('stroke-dasharray', totalLength)
            .style('stroke-dashoffset', totalLength * (1 - eased))
            .style('opacity', 1);
          
          g.select('.area-path').style('opacity', 0.15 * eased);
          
          g.selectAll('.data-point').each(function(d: any, i: number) {
            const point = d3.select(this);
            const pointDelay = 0.4;
            const pointDuration = 0.3;
            const pointStart = i * pointDelay;
            const pointEnd = pointStart + pointDuration;
            
            if (totalTime >= pointStart && totalTime <= pointEnd) {
              const pointProgress = (totalTime - pointStart) / pointDuration;
              const eased = d3.easeCubicOut(pointProgress);
              point.style('opacity', eased);
            } else if (totalTime > pointEnd) {
              point.style('opacity', 1);
            }
          });
        } else {
          g.select('.line-path')
            .style('stroke-dasharray', 'none')
            .style('stroke-dashoffset', 0)
            .style('opacity', 1);
          g.select('.area-path').style('opacity', 0.15);
          g.selectAll('.data-point').style('opacity', 1);
        }
        
        const labelStart = 1.8;
        const labelDuration = 0.6;
        if (totalTime >= labelStart && totalTime <= labelStart + labelDuration) {
          const labelProgress = (totalTime - labelStart) / labelDuration;
          const eased = d3.easeCubicOut(labelProgress);
          g.selectAll('.value-label, .month-label').style('opacity', eased);
        } else if (totalTime > labelStart + labelDuration) {
          g.selectAll('.value-label, .month-label').style('opacity', 1);
        }
        
        const gridStart = 0.3;
        const gridDuration = 0.5;
        if (totalTime >= gridStart && totalTime <= gridStart + gridDuration) {
          const gridProgress = (totalTime - gridStart) / gridDuration;
          const eased = d3.easeCubicOut(gridProgress);
          g.selectAll('.grid-y').style('opacity', 0.5 * eased);
          g.selectAll('.y-axis text').style('opacity', eased);
          g.selectAll('.y-axis line, .y-axis path').style('opacity', eased);
        } else if (totalTime > gridStart + gridDuration) {
          g.selectAll('.grid-y').style('opacity', 0.5);
          g.selectAll('.y-axis text').style('opacity', 1);
          g.selectAll('.y-axis line, .y-axis path').style('opacity', 1);
        }
        
        const axisStart = 2.2;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', eased);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        }
      }
    }
    
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;
    
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          data.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d.month);
            }
          });
        }
      });

      g.selectAll<SVGCircleElement, any>('.data-point').each(function(d: any) {
        const point = d3.select(this);
        const isHighlighted = highlightedItems.has(d.month);

        if (isHighlighted) {
          point
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
        } else {
          point
            .style('opacity', 0.3)
            .attr('stroke', backgroundColor)
            .attr('stroke-width', 2)
            .style('filter', 'url(#pointShadow)');
        }
      });
      
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d.month);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });
    }
    
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.data-point')
        .attr('stroke', backgroundColor)
        .attr('stroke-width', 2)
        .style('opacity', 1)
        .style('filter', 'url(#pointShadow)');
      g.selectAll('.value-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, sceneStartOffset]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start',
      padding: '60px 40px'
    }}>
      <div style={{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}>
        月度销售额趋势
      </div>
      
      <svg 
        ref={svgRef} 
        width={1100} 
        height={600} 
        style={{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
      
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