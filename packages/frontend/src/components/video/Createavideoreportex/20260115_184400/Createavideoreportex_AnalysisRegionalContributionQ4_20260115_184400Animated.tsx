import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 63.684;
  
  // Animation configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 63.684,
      "duration": 5.419999999999999
    },
    {
      "id": "emphasis_latin_america",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "region": "Latin America"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Latin America when mentioned",
      "time_start": 68.954,
      "duration": 9.058000000000007
    },
    {
      "id": "emphasis_north_america",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "region": "North America"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight North America when mentioned",
      "time_start": 74.25399999999999,
      "duration": 3.7580000000000098
    }
  ];

  // Subtitle configuration
  const narrations = [
    {
      "text": "Geographically, all regions contributed strongly to our Q4 success.",
      "time_start": 63.684,
      "time_end": 68.904,
      "audio_file": "public/audio/generated_20260115_184400_analysis_regional_contribution_q4_narr0.wav"
    },
    {
      "text": "Latin America led with $2.07M, closely followed by North America at $1.99M.",
      "time_start": 68.904,
      "time_end": 78.012,
      "audio_file": "public/audio/generated_20260115_184400_analysis_regional_contribution_q4_narr1.wav"
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
      "region": "Latin America",
      "sum_total_amount": 2068668.0,
      "count": 515
    },
    {
      "region": "North America", 
      "sum_total_amount": 1985550.0,
      "count": 509
    },
    {
      "region": "Asia Pacific",
      "sum_total_amount": 1823094.0,
      "count": 479
    },
    {
      "region": "Europe",
      "sum_total_amount": 1811320.0,
      "count": 497
    }
  ];
  
  // Extract field names from data_binding
  const xField = 'region';
  const yField = 'sum_total_amount';
  
  // Color configuration - Q4 revenue success theme with emerald/teal colors
  const backgroundColor = '#ffffff';
  const containerBackground = '#ffffff';
  const textColor = '#0f172a';
  const barColor = '#2563eb'; // Emerald green for revenue success
  const highlightColor = '#7c3aed'; // Darker emerald for emphasis
  const gridColor = '#cbd5e1';
  const axisColor = '#64748b';
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Format number function
  const formatNumber = (value: number): string => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  };
  
  // D3 scales for categorical bar chart
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.25);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([320, 0]);
    return { xScale, yScale };
  }, [data, maxValue]);
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add filters
    const defs = svg.append('defs');
    
    // 柔和阴影（代替发光）
    const shadow = defs.append('filter').attr('id', 'softShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 2)
      .attr('stdDeviation', 3)
      .attr('flood-color', '#000000')
      .attr('flood-opacity', 0.12);
    
    // Draw chart
    const g = svg.append('g').attr('transform', 'translate(80, 60)');
    const {xScale, yScale} = scales;
    
    // Y-axis grid lines
    const yTicks = yScale.ticks(6);
    g.selectAll('.grid-y')
      .data(yTicks)
      .enter()
      .append('line')
      .attr('class', 'grid-y')
      .attr('x1', 0)
      .attr('x2', 800)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .style('opacity', 0.3);
    
    // Draw bars with initial state for animation
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', 320)
      .attr('width', xScale.bandwidth())
      .attr('height', 0)
      .attr('fill', (d: any) => d[yField] === maxValue ? '#0891b2' : barColor)
      .attr('rx', 6)
      .style('opacity', 0)
      .style('filter', 'url(#softShadow)');
    
    // Value labels on top of bars with initial state
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12)
      .attr('text-anchor', 'middle')
      .text((d: any) => formatNumber(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? '#0891b2' : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '20px' : '16px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? '700' : '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    // Region labels with initial state
    g.selectAll('.region-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'region-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', (d: any) => d[yField] === maxValue ? '#0891b2' : textColor)
      .style('font-size', '15px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? '700' : '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    // Y-axis labels with initial state
    g.selectAll('.y-tick-label')
      .data(yTicks)
      .enter()
      .append('text')
      .attr('class', 'y-tick-label')
      .attr('x', -15)
      .attr('y', (d: any) => yScale(d) + 5)
      .attr('text-anchor', 'end')
      .text((d: any) => formatNumber(d))
      .attr('fill', axisColor)
      .style('font-size', '13px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    // Y-axis title with initial state
    g.append('text')
      .attr('class', 'y-axis-title')
      .attr('x', -60)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -60, 160)')
      .text('Revenue (USD)')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
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

    const {yScale} = scales;
    const innerHeight = 320;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // Animation completed - force all elements to final state
      if (frame >= animEnd) {
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .region-label').style('opacity', 1);
        g.selectAll('.y-tick-label, .y-axis-title').style('opacity', 1);
        g.selectAll('.grid-y').style('opacity', 0.3);
        
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
        g.selectAll('.value-label, .region-label').each(function(d: any, i: number) {
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
        
        // Axis labels fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.y-tick-label, .y-axis-title').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-tick-label, .y-axis-title').style('opacity', 1);
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
            .attr('stroke', '#0891b2')
            .attr('stroke-width', 3 * maxPulse)
            .style('filter', 'drop-shadow(0 0 10px rgba(8, 145, 178, 0.6))');
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none');
        }
      });
    }

    // 3. Restore normal state when no emphasis is active
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1).style('filter', 'url(#softShadow)');
      g.selectAll('.value-label, .region-label').style('opacity', 1);
      g.selectAll('.y-tick-label, .y-axis-title').style('opacity', 1);
      g.selectAll('.grid-y').style('opacity', 0.3);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, maxValue]);
  
  return (
    <AbsoluteFill style={{ 
      background: '#ffffff',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px'
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 25,
        fontSize: '32px',
        fontWeight: '700',
        color: '#111827',
        textAlign: 'center',
        maxWidth: '1200px'
      }}>
        Regional Revenue Distribution - Q4 2025
      </div>
      
      {/* Chart */}
      <svg 
        ref={svgRef} 
        width={960} 
        height={480} 
        style={{ 
          marginTop: '10px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
      
      {/* Subtitles */}
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