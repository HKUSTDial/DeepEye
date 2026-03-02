import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 2.76;
  
  const data = [
    {
      "grade": "高一",
      "avg_score": 88.5,
      "count": 2
    },
    {
      "grade": "高二", 
      "avg_score": 78.0,
      "count": 1
    }
  ];
  
  const xField = 'grade';
  const yField = 'avg_score';
  
  const backgroundColor = '#0f1419';
  const _containerBackground = '#0f1419';
  void _containerBackground
  const textColor = '#e8eaed';
  const barColor = '#10b981';
  const highlightColor = '#34d399';
  const gridColor = '#374151';
  const axisColor = '#6b7280';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const _minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const _maxItem = data.find((d: any) => d[yField] === maxValue);
  void _minValue
  void _maxItem
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.3);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15])
      .range([320, 0]);
    return { xScale, yScale };
  }, [data, maxValue]);
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Bar chart entrance animation",
      "time_start": 2.76,
      "duration": 0.768
    },
    {
      "id": "emphasis_grade_1",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "grade": "高一"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight 高一年级 when mentioned",
      "time_start": 3.3779999999999997,
      "duration": 1.2360000000000002
    },
    {
      "id": "emphasis_grade_2",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "grade": "高二"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight 高二年级 when mentioned",
      "time_start": 7.927999999999999,
      "duration": Math.abs(-3.313999999999999)
    }
  ];

  const narrations = [
    {
      "text": "接下来对比各年级的成绩表现。",
      "time_start": 2.76,
      "time_end": 3.328,
      "audio_file": "tmp/video_config_audio/analysis_grade_comparison_narr0.wav"
    },
    {
      "text": "高一年级平均成绩达到88.5分，明显超过高二年级的78.0分。",
      "time_start": 3.328,
      "time_end": 4.614,
      "audio_file": "tmp/video_config_audio/analysis_grade_comparison_narr1.wav"
    }
  ];

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
      .attr('id', 'scoreGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#34d399');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#10b981');
    
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 6)
      .attr('stdDeviation', 8)
      .attr('flood-color', '#000000')
      .attr('flood-opacity', 0.25);
    
    const g = svg.append('g').attr('transform', 'translate(80, 60)');
    const {xScale, yScale} = scales;
    
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', 320)
      .attr('width', xScale.bandwidth())
      .attr('height', 0)
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#scoreGradient)' : barColor)
      .attr('rx', 12)
      .attr('ry', 12)
      .style('filter', 'url(#barShadow)')
      .style('opacity', 0);
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 20)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(1)}分`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '22px')
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
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d: any) => `${d}分`);
    
    const yAxisGroup = g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis);
    
    yAxisGroup.selectAll('line, path')
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);
    
    yAxisGroup.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .ticks(5)
        .tickSize(-800)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-width', 0.5)
      .attr('stroke-dasharray', '3,3')
      .attr('opacity', 0.6);
    
  }, [scales, data, maxValue]);

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
        
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;

        // Bars grow sequentially
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
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
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(_d: any, i: number) {
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

      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'url(#barShadow)');
        }
      });
    }

    // 3. Restore normal state when no emphasis is active
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1).style('filter', 'url(#barShadow)');
      g.selectAll('.value-label, .category-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start',
      padding: '0'
    }}>
      <div style={{
        position: 'absolute',
        top: 25,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        letterSpacing: '-0.5px'
      }}>
        各年级平均成绩对比
      </div>
      
      <svg 
        ref={svgRef} 
        width={960} 
        height={480} 
        style={{ 
          marginTop: '90px',
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
          {getCurrentNarration()?.text}
        </div>
      )}
    </AbsoluteFill>
  );
};