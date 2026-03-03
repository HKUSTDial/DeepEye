import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 36.504;  // Start time of the scene in the original video
  
  const data = [
    {
      "product_name": "Laptop Pro X",
      "sum_total_amount": 2420880.0,
      "count": 246
    },
    {
      "product_name": "SmartPhone Ultra",
      "sum_total_amount": 2012220.0,
      "count": 261
    },
    {
      "product_name": "4K Monitor",
      "sum_total_amount": 882560.0,
      "count": 259
    },
    {
      "product_name": "Smart Watch Gen5",
      "sum_total_amount": 731570.0,
      "count": 251
    },
    {
      "product_name": "Ergo Chair",
      "sum_total_amount": 621180.0,
      "count": 241
    },
    {
      "product_name": "NoiseCancel Headset",
      "sum_total_amount": 540750.0,
      "count": 248
    },
    {
      "product_name": "Mechanical Keyboard",
      "sum_total_amount": 299040.0,
      "count": 249
    },
    {
      "product_name": "Gaming Mouse",
      "sum_total_amount": 180432.0,
      "count": 245
    }
  ];
  
  const xField = 'product_name';
  const yField = 'sum_total_amount';
  
  const backgroundColor = '#ffffff';
  const containerBackground = '#ffffff';
  const textColor = '#0f172a';
  const barColor = '#2563eb';
  const highlightColor = '#0891b2';
  const gridColor = '#cbd5e1';
  const axisColor = '#64748b';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const formatCurrency = (value: number): string => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toLocaleString()}`;
  };
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 1000])
      .padding(0.15);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([320, 0]);
    return { xScale, yScale };
  }, [data, maxValue]);
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 36.504,
      "duration": 4.4120000000000035
    },
    {
      "id": "emphasis_laptop_pro_x",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "product_name": "Laptop Pro X"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Laptop Pro X when mentioned",
      "time_start": 40.766,
      "duration": 9.202000000000005,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "Laptop Pro X",
        "word_time": 40.766
      }
    },
    {
      "id": "emphasis_smartphone_ultra",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "product_name": "SmartPhone Ultra"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight SmartPhone Ultra when mentioned",
      "time_start": 46.191,
      "duration": 3.777000000000001,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "SmartPhone Ultra",
        "word_time": 46.191
      }
    }
  ];

  const narrations = [
    {
      "text": "Now let's examine which products drove this Q4 success.",
      "time_start": 36.504,
      "time_end": 40.716,
      "audio_file": "public/audio/generated_20260115_184400_analysis_top_products_q4_narr0.wav"
    },
    {
      "text": "Laptop Pro X dominated with $2.42M in revenue, followed by SmartPhone Ultra at $2.01M.",
      "time_start": 40.716,
      "time_end": 49.968,
      "audio_file": "public/audio/generated_20260115_184400_analysis_top_products_q4_narr1.wav"
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
      .attr('id', 'goldGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#fde047');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#f59e0b');
    
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', '#fbbf24');
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', '#d97706');
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 6)
      .attr('stdDeviation', 8)
      .attr('flood-color', '#fbbf24')
      .attr('flood-opacity', 0.4);
    
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
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : 'url(#goldGradient)')
      .attr('rx', 6)
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none')
      .style('stroke', (d: any) => d[yField] === maxValue ? '#f59e0b' : 'none')
      .style('stroke-width', (d: any) => d[yField] === maxValue ? 2 : 0)
      .style('opacity', 0);
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12)
      .attr('text-anchor', 'middle')
      .text((d: any) => formatCurrency(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? '#fbbf24' : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '20px' : '16px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? '800' : '600')
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
      .text((d: any) => {
        const name = d[xField];
        if (name.length > 12) {
          return name.substring(0, 10) + '...';
        }
        return name;
      })
      .attr('fill', (d: any) => d[yField] === maxValue ? '#fbbf24' : textColor)
      .style('font-size', '14px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? '700' : '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const yAxis = d3.axisLeft(yScale)
      .ticks(6)
      .tickFormat((d: any) => formatCurrency(d as number));
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis);
    
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);
    g.select('.y-axis').selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .ticks(6)
        .tickSize(-1000)
        .tickFormat(() => "")
      );
    
    g.select('.grid-y').selectAll('line').attr('stroke', gridColor).attr('opacity', 0.3);
    g.select('.grid-y').select('.domain').remove();
    
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
      
      // Animation ended - force all elements to final state
      if (frame >= animEnd) {
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        
        // Continue executing emphasis animations (don't return)
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
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
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
    
    // Collect all currently active emphasis animations
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      // Calculate pulse effect from all active animations
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting
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

      // Process all bars at once to avoid overwriting
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ef4444')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(239, 68, 68, 0.8))');
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none');
        }
      });
    }

    // 3. Restore normal state when no emphasis is active
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1).style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none');
      g.selectAll('.value-label, .category-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset]);
  
  return (
    <AbsoluteFill style={{ 
      background: '#ffffff',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px'
    }}>
      <div style={{
        position: 'absolute',
        top: 25,
        fontSize: '36px',
        fontWeight: '700',
        color: '#111827',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        Top Products by Total Sales Revenue - Q4 2025
      </div>
      
      <svg 
        ref={svgRef} 
        width={1160} 
        height={480} 
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