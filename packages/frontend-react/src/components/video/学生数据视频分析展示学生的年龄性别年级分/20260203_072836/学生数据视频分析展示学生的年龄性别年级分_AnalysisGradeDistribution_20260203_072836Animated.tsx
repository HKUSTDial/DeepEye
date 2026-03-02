import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 11.0;
  
  const data = [
    {
      "grade": 10,
      "count_grade": 10,
      "count": 10
    },
    {
      "grade": 11,
      "count_grade": 5,
      "count": 5
    },
    {
      "grade": 12,
      "count_grade": 5,
      "count": 5
    }
  ];
  
  const xField = 'grade';
  const yField = 'count';
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const barColor = '#4ade80';
  const highlightColor = '#22c55e';
  const gridColor = '#374151';
  const axisColor = '#6b7280';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Bar chart entrance animation",
      "time_start": 11.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_grade_10",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "grade": 10
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight grade 10 when mentioned",
      "time_start": 14.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_grade_11",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "grade": 11
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight grade 11 when mentioned",
      "time_start": 14.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_grade_12",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "grade": 12
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight grade 12 when mentioned",
      "time_start": 14.0,
      "duration": 3.2
    }
  ];
  
  const narrations = [
    {
      "text": "接下来分析各年级的学生人数分布。",
      "time_start": 11.0,
      "time_end": 14.0
    },
    {
      "text": "十年级学生人数最多达到10人，十一年级和十二年级均为5人。",
      "time_start": 14.0,
      "time_end": 17.0
    }
  ];
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 600])
      .padding(0.3);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2])
      .range([320, 0]);
    return { xScale, yScale };
  }, [data, maxValue]);
  
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
      .attr('id', 'barGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#6ee7b7');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', '#86efac');
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.2);
    
    const g = svg.append('g').attr('transform', 'translate(180, 80)');
    const {xScale, yScale} = scales;
    
    g.selectAll('.grid-line')
      .data(yScale.ticks(5))
      .enter()
      .append('line')
      .attr('class', 'grid-line')
      .attr('x1', 0)
      .attr('x2', 600)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .style('opacity', 0.3);
    
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', 320)
      .attr('width', xScale.bandwidth())
      .attr('height', 0)
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : 'url(#barGradient)')
      .attr('rx', 12)
      .attr('ry', 12)
      .style('filter', 'url(#shadow)')
      .attr('stroke', (d: any) => d[yField] === maxValue ? highlightColor : 'none')
      .attr('stroke-width', (d: any) => d[yField] === maxValue ? 3 : 0)
      .style('opacity', 0);
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 20)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField]}人`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '24px' : '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[xField]}年级`)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 160)')
      .text('学生人数')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-weight', '500')
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
    const innerHeight = 320;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      if (frame >= animEnd) {
        // Animation completed, force all elements to final state
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis-label').style('opacity', 1);
        
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;

        // Bars grow sequentially
        g.selectAll('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;
          const animDuration = 0.6;
          const barStart = i * delayPerBar;
          const barEnd = barStart + animDuration;

          if (totalTime >= barStart && totalTime <= barEnd) {
            const barProgress = (totalTime - barStart) / animDuration;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Labels fade in with delay
        g.selectAll('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3;
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
        
        // Axis label fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.y-axis-label').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;
    
    // Collect all currently active emphasis animations
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      // Calculate pulse effect
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all highlighted items
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

      // Apply highlighting to all bars
      g.selectAll('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'url(#shadow)');
        }
      });
    }

    // 3. Restore normal state when no emphasis is active
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.bar')
        .attr('stroke', (d: any) => d[yField] === maxValue ? highlightColor : 'none')
        .attr('stroke-width', (d: any) => d[yField] === maxValue ? 3 : 0)
        .style('opacity', 1)
        .style('filter', 'url(#shadow)');
      g.selectAll('.value-label, .category-label').style('opacity', 1);
      g.selectAll('.y-axis-label').style('opacity', 1);
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
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        各年级学生人数分布
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