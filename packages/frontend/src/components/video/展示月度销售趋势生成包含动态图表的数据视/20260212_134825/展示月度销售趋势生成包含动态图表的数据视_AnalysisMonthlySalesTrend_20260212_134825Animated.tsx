import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 1.193;
  
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
      "time_start": 1.193,
      "duration": 2.2960000000000003
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
      "time_start": 4.218,
      "duration": -0.9289999999999998
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
      "time_start": 6.193,
      "duration": -2.9039999999999995
    }
  ];
  
  const narrations = [
    {
      "text": "销售额呈现稳定上升趋势，从1月的1200增长至4月的2000，连续四个月保持增长态势，总增幅达67%。",
      "time_start": 1.193,
      "time_end": 3.289,
      "audio_file": "20260212_134825_analysis_monthly_sales_trend_narr0.wav"
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
    
    const g = svg.append('g').attr('transform', 'translate(100, 80)');
    const {xScale, yScale} = scales;
    
    g.selectAll('.grid-y')
      .data(yScale.ticks(5))
      .enter()
      .append('line')
      .attr('class', 'grid-y')
      .attr('x1', 0)
      .attr('x2', 700)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .style('opacity', 0.3);
    
    const line = d3.line()
      .x((d: any) => xScale(+d[xField]))
      .y((d: any) => yScale(d[yField]))
      .curve(d3.curveMonotoneX);
    
    g.append('path')
      .datum(data)
      .attr('class', 'line')
      .attr('fill', 'none')
      .attr('stroke', 'url(#lineGradient)')
      .attr('stroke-width', 4)
      .attr('d', line)
      .style('filter', 'url(#shadow)')
      .style('opacity', 0);
    
    g.selectAll('.point')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'point')
      .attr('cx', (d: any) => xScale(+d[xField]))
      .attr('cy', (d: any) => yScale(d[yField]))
      .attr('r', (d: any) => d[yField] === maxValue ? 8 : 6)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : lineColor)
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 2)
      .style('filter', 'url(#shadow)')
      .style('opacity', 0);
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => xScale(+d[xField]))
      .attr('y', (d: any) => yScale(d[yField]) - 15)
      .attr('text-anchor', 'middle')
      .text((d: any) => `¥${d[yField]}`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '20px' : '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d: any) => `¥${d}`);
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);
    
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
    
    g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor);
    
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', 150)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 150)')
      .text('销售额')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
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
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
  }, [scales, maxValue]);
  
  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale} = scales;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      if (frame >= animEnd) {
        // Animation completed, force all elements to final state
        g.selectAll('.line').style('opacity', 1);
        g.selectAll('.point').style('opacity', 1);
        g.selectAll('.value-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        g.selectAll('.grid-y').style('opacity', 0.3);
        
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;
        
        // Line drawing animation
        const lineStart = 0;
        const lineDuration = 1.2;
        if (totalTime >= lineStart && totalTime <= lineStart + lineDuration) {
          const lineProgress = (totalTime - lineStart) / lineDuration;
          const eased = d3.easeCubicOut(lineProgress);
          g.selectAll('.line').style('opacity', eased);
        } else if (totalTime > lineStart + lineDuration) {
          g.selectAll('.line').style('opacity', 1);
        }
        
        // Points animation
        g.selectAll('.point').each(function(d: any, i: number) {
          const point = d3.select(this);
          const delayPerPoint = 0.15;
          const animDuration = 0.4;
          const pointStart = 0.8 + i * delayPerPoint;
          const pointEnd = pointStart + animDuration;

          if (totalTime >= pointStart && totalTime <= pointEnd) {
            const pointProgress = (totalTime - pointStart) / animDuration;
            const eased = d3.easeCubicOut(pointProgress);
            point.style('opacity', eased);
          } else if (totalTime > pointEnd) {
            point.style('opacity', 1);
          }
        });

        // Labels animation
        g.selectAll('.value-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerLabel = 0.15;
          const labelDelay = 0.3;
          const animDuration = 0.4;
          const labelStart = 0.8 + i * delayPerLabel + labelDelay;
          const labelEnd = labelStart + animDuration;

          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });
        
        // Axis labels animation
        const axisStart = 0.3;
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

    // 2. EMPHASIS ANIMATION
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;
    
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = Math.abs(anim.duration) * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = Math.abs(anim.duration) * fps;
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

      g.selectAll('.point').each(function(d: any) {
        const point = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          point
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
        } else {
          point.style('opacity', 0.3).attr('stroke', backgroundColor).style('filter', 'url(#shadow)');
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
      g.selectAll('.point').attr('stroke', backgroundColor).style('opacity', 1).style('filter', 'url(#shadow)');
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
        width={900} 
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