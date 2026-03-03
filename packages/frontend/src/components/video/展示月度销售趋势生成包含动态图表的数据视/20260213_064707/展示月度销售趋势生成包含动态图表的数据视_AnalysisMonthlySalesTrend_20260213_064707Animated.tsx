import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 6.575;
  
  const data = [
    {
      "month": "1",
      "sum_sales": 1200,
      "count": 1
    },
    {
      "month": "2",
      "sum_sales": 1500,
      "count": 1
    },
    {
      "month": "3",
      "sum_sales": 1800,
      "count": 1
    },
    {
      "month": "4",
      "sum_sales": 2000,
      "count": 1
    }
  ];
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "draw_line",
      "trigger_narration": 0,
      "description": "Line chart entrance animation",
      "time_start": 6.575,
      "duration": 11.75
    },
    {
      "id": "emphasis_january",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "month": "1"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight January data point when mentioned",
      "time_start": 9.6,
      "duration": 8.525
    },
    {
      "id": "emphasis_april",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "month": "4"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight April data point when mentioned",
      "time_start": 11.575,
      "duration": 6.550000000000001
    }
  ];
  
  const narrations = [
    {
      "text": "销售额呈现稳定上升趋势，从1月的1200增长至4月的2000，连续四个月保持增长态势，总增幅达67%。",
      "time_start": 6.575,
      "time_end": 18.125,
      "audio_file": "20260213_064707_analysis_monthly_sales_trend_narr0.wav"
    }
  ];
  
  const xField = 'month';
  const yField = 'sum_sales';
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const lineColor = '#10b981';
  const highlightColor = '#34d399';
  const gridColor = '#2a3441';
  const axisColor = '#6b7280';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const xScale = d3.scaleLinear()
      .domain([1, 4])
      .range([0, 700]);
    const yScale = d3.scaleLinear()
      .domain([minValue * 0.9, maxValue * 1.1])
      .range([300, 0]);
    return { xScale, yScale };
  }, [data, maxValue, minValue]);
  
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  // Static rendering
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
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    const g = svg.append('g').attr('transform', 'translate(120, 80)');
    const {xScale, yScale} = scales;
    
    // Grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .selectAll('line')
      .data(yScale.ticks(5))
      .enter()
      .append('line')
      .attr('x1', 0)
      .attr('x2', 700)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .style('opacity', 0);
    
    // Line path
    const line = d3.line()
      .x((d: any) => xScale(+d[xField]))
      .y((d: any) => yScale(d[yField]))
      .curve(d3.curveMonotoneX);
    
    const linePath = g.append('path')
      .datum(data)
      .attr('class', 'line')
      .attr('fill', 'none')
      .attr('stroke', 'url(#lineGradient)')
      .attr('stroke-width', 4)
      .attr('d', line)
      .style('filter', 'url(#shadow)')
      .style('opacity', 0);
    
    // Get total path length for animation
    const totalLength = linePath.node()?.getTotalLength() || 0;
    linePath
      .attr('stroke-dasharray', totalLength + ' ' + totalLength)
      .attr('stroke-dashoffset', totalLength);
    
    // Data points
    g.selectAll('.dot')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'dot')
      .attr('cx', (d: any) => xScale(+d[xField]))
      .attr('cy', (d: any) => yScale(d[yField]))
      .attr('r', (d: any) => d[yField] === maxValue ? 8 : 6)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : lineColor)
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 2)
      .style('filter', 'url(#shadow)')
      .style('opacity', 0);
    
    // Value labels
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => xScale(+d[xField]))
      .attr('y', (d: any) => yScale(d[yField]) - 20)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField])
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    // Y-axis
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
      .style('text-rendering', 'geometricPrecision');
    
    // X-axis
    const xAxis = d3.axisBottom(xScale)
      .ticks(4)
      .tickFormat((d: any) => `${d}月`);
    
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', 'translate(0, 300)')
      .call(xAxis)
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Axis styling
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);
    g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor);
    
    // Axis labels
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', 150)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 150)')
      .text('销售额')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', 350)
      .attr('y', 340)
      .attr('text-anchor', 'middle')
      .text('月份')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
  }, [scales, maxValue]);
  
  // Animation updates
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      if (frame >= animEnd) {
        // Animation completed, force all elements to final state
        const linePath = g.select('.line');
        linePath
          .attr('stroke-dashoffset', 0)
          .style('opacity', 1);
        
        g.selectAll('.dot').style('opacity', 1);
        g.selectAll('.value-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        g.selectAll('.grid-y').style('opacity', 0.3);
        
      } else if (frame >= animStart) {
        // Animation in progress
        const totalTime = (frame - animStart) / fps;
        const lineDuration = 2.0; // Line drawing duration
        const dotDelay = 1.5; // Dots appear after line starts
        const dotDuration = 1.0; // Dot animation duration
        const labelDelay = 2.0; // Labels appear after dots
        const labelDuration = 0.8; // Label fade duration
        const axisDelay = 0.5; // Axis labels delay
        const axisDuration = 0.6; // Axis fade duration
        
        // Line drawing animation
        const linePath = g.select('.line');
        if (totalTime <= lineDuration) {
          const lineProgress = totalTime / lineDuration;
          const eased = d3.easeCubicOut(lineProgress);
          const totalLength = linePath.node()?.getTotalLength() || 0;
          linePath
            .attr('stroke-dashoffset', totalLength * (1 - eased))
            .style('opacity', 1);
        } else {
          linePath.attr('stroke-dashoffset', 0).style('opacity', 1);
        }
        
        // Grid lines fade in
        if (totalTime >= 0.3 && totalTime <= 0.3 + 0.5) {
          const gridProgress = (totalTime - 0.3) / 0.5;
          g.selectAll('.grid-y').style('opacity', gridProgress * 0.3);
        } else if (totalTime > 0.3 + 0.5) {
          g.selectAll('.grid-y').style('opacity', 0.3);
        }
        
        // Dots animation
        g.selectAll('.dot').each(function(d: any, i: number) {
          const dot = d3.select(this);
          const dotStart = dotDelay + i * 0.15;
          const dotEnd = dotStart + dotDuration;
          
          if (totalTime >= dotStart && totalTime <= dotEnd) {
            const dotProgress = (totalTime - dotStart) / dotDuration;
            const eased = d3.easeBackOut(dotProgress);
            dot.style('opacity', eased);
          } else if (totalTime > dotEnd) {
            dot.style('opacity', 1);
          }
        });
        
        // Labels animation
        g.selectAll('.value-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const labelStart = labelDelay + i * 0.1;
          const labelEnd = labelStart + labelDuration;
          
          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / labelDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });
        
        // Axis labels animation
        if (totalTime >= axisDelay && totalTime <= axisDelay + axisDuration) {
          const axisProgress = (totalTime - axisDelay) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', eased);
        } else if (totalTime > axisDelay + axisDuration) {
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION
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
              highlightedItems.add(d[xField]);
            }
          });
        }
      });

      g.selectAll('.dot').each(function(d: any) {
        const dot = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          dot
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
        } else {
          dot.style('opacity', 0.3).attr('stroke', backgroundColor).style('filter', 'url(#shadow)');
        }
      });
      
      g.selectAll('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });
    }

    // 3. Restore normal state
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.dot')
        .attr('stroke', backgroundColor)
        .attr('stroke-width', 2)
        .style('opacity', 1)
        .style('filter', 'url(#shadow)');
      g.selectAll('.value-label').style('opacity', 1);
      g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
      g.selectAll('.grid-y').style('opacity', 0.3);
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
      <div style={{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
      }}>
        月度销售趋势
      </div>
      
      <svg 
        ref={svgRef} 
        width={960} 
        height={500} 
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