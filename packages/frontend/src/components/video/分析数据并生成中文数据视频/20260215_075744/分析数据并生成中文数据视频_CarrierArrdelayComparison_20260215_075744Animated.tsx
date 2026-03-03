import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 10.0;  // Start time of the scene in the original video
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "avg_arrdelay": 9.48,
    "count": 1880
  },
  {
    "carrier": "EV",
    "avg_arrdelay": 12.76,
    "count": 144
  },
  {
    "carrier": "MQ",
    "avg_arrdelay": 38.98,
    "count": 56
  },
  {
    "carrier": "OO",
    "avg_arrdelay": 26.06,
    "count": 319
  },
  {
    "carrier": "UA",
    "avg_arrdelay": 15.6,
    "count": 1358
  }
];
  
  // Data binding configuration
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均抵达延误时间 (分钟)"
    }
  };

  const xField = data_binding.x_axis?.field || 'carrier';
  const yField = (data_binding.y_axis as {field: string}).field || 'avg_arrdelay';
  const yLabel = (data_binding.y_axis as {label: string}).label || 'Value';
  
  // Color configuration (CRITICAL: Background colors are fixed!)
  const backgroundColor = '#0f1419'; // MUST use this exact value
  // const containerBackground = '#0f1419'; // Not directly used as a variable in JSX
  
  // Scene-specific theme colors for 'delays'
  const textColor = '#e8eaed'; 
  const barColor = '#f97316'; // Vibrant orange for delays
  const highlightColor = '#dc2626'; // More intense red for longest delay
  const gridColor = '#3a3a3a'; // Subtle grey for grid lines
  const axisColor = '#888888'; // Subtle grey for axis lines
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions and margins
  const width = 1000;
  const height = 400; // Chart drawing area height (max y-axis value to x-axis)
  const margin = { top: 100, right: 60, bottom: 180, left: 80 }; // Bottom 180px for subtitles
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15]) // Extend domain slightly above max for label space
      .range([innerHeight, 0]); // Invert range for SVG coordinates
      
    return { xScale, yScale };
  }, [data, xField, maxValue, innerWidth, innerHeight]);

  // Animation configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 10.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_mq_carrier",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "carrier": "MQ"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight MQ airline as having the longest delay",
      "time_start": 10.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_aa_carrier",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "carrier": "AA"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight AA airline as having the shortest delay",
      "time_start": 10.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_aa_delay_value",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "carrier": "AA",
          "avg_arrdelay": 9.48
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight AA's specific delay value of 9.48 minutes",
      "time_start": 10.0,
      "duration": 3.2
    }
  ];

  // Subtitle configuration
  const narrations = [
    {
      "text": "紧接着，我们分析各航空公司平均抵达延误时间。与出发延误类似，MQ航空的抵达延误也最长，AA航空则最短，仅为9.48分钟。",
      "time_start": 10.0,
      "time_end": 13.0
    }
  ];

  // Helper to get current narration text
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
    svg.selectAll('*').remove(); // Clear SVG contents

    // Add SVG clarity optimizations
    svg.attr('shape-rendering', 'geometricPrecision')
       .attr('text-rendering', 'geometricPrecision');
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Gradient for the highlight bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); 
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor); 
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.4);
    
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    const { xScale, yScale } = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => "")
        .ticks(5)
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `${d} min`))
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 10) // Positioned to the left of the axis
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 10}, ${innerHeight / 2})`)
      .text(yLabel)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // Draw bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', innerHeight) // Initial state for animation: at the bottom
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial state for animation: height 0
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 6) // Rounded corners for aesthetics
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#barShadow)' : 'none')
      .style('opacity', 0); // Initial state for animation
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Position slightly above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(2)}`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation
    
    // Category labels below chart (X-axis labels)
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', innerHeight + 40) // Position below the chart area (innerHeight is the bottom of the chart)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[xField] === maxItem?.[xField] ? 'bold' : 'normal')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

  }, [scales, data, xField, yField, maxValue, maxItem, barColor, highlightColor, textColor, gridColor, axisColor, innerWidth, innerHeight, margin.left, margin.top]);
  
  // ANIMATION LOGIC
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { yScale } = scales;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance' && a.effect === 'grow_bars');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // ✅ CRITICAL: 动画结束后，强制所有元素到最终状态
      if (frame >= animEnd) {
        // Bar Chart elements
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', yScale(d[yField]))
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis-label').style('opacity', 1);
        // Grid lines are not explicitly animated for entrance, so they should be visible
        g.selectAll('.grid-y').selectAll('line').style('opacity', 1);

      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

        // Bars grow
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;  // Fixed delay 0.12 seconds
          const animDuration = 0.6;   // Fixed duration 0.6 seconds
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
              .attr('y', yScale(d[yField]))
              .style('opacity', 1);
          }
        });

        // Labels fade in (category + value simultaneously)
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3;  // Additional delay 0.3 seconds
          const animDuration = 0.4; // Fixed duration 0.4 seconds
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
        
        // Y-axis label fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.y-axis-label').style('opacity', eased);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - Highlight specific data
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
      
      // Calculate max pulse for synchronized effect
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Adjust for desired pulse frequency/intensity
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // 1.0 to 1.05 scale
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
              highlightedItems.add(d[xField]); // Use xField (carrier) as identifier
            }
          });
        }
      });

      // Apply emphasis styles to bars
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red border
            .attr('stroke-width', 3 * maxPulse) // Pulsing border width
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none');
        }
      });

      // Apply emphasis styles to value labels
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1).attr('fill', highlightColor);
        } else {
          label.style('opacity', 0.3).attr('fill', textColor);
        }
      });

      // Apply emphasis styles to category labels
      g.selectAll<SVGTextElement, any>('.category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1).attr('fill', highlightColor);
        } else {
          label.style('opacity', 0.3).attr('fill', textColor);
        }
      });

    }

    // 3. Restore normal state (only when no emphasis is active AND entrance animation is done)
    const entranceDone = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;

    if (!hasActiveEmphasis && entranceDone) {
      g.selectAll('.bar')
        .attr('stroke', 'none')
        .style('opacity', 1)
        .style('filter', (d: any) => d[yField] === maxValue ? 'url(#barShadow)' : 'none')
        .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor); // Restore original fill
      
      g.selectAll('.value-label')
        .style('opacity', 1)
        .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor); // Restore original fill
      
      g.selectAll('.category-label')
        .style('opacity', 1)
        .attr('fill', textColor); // Restore original fill
    }

  }, [frame, fps, scales, animations, data, xField, yField, maxValue, barColor, highlightColor, textColor, innerHeight, sceneStartOffset]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to control padding more precisely
      paddingTop: '60px', // Reserve space for title + top padding
      paddingBottom: '180px' // CRITICAL: Reserve bottom 180px for subtitles
    }}>
      {/* Title - positioned at the top, allowing for subtitle overlay */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top edge
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        zIndex: 10,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均抵达延误时间对比
      </div>
      
      {/* Chart - positioned below the title, within the safe zone */}
      <svg 
        ref={svgRef} 
        width={width} 
        height={height} 
        style={{ 
          marginTop: '20px', // Space between title and chart
          overflow: 'visible' // Allow elements like shadows to extend beyond svg boundaries
        }} 
      />
      
      {/* Subtitle Display */}
      {getCurrentNarration() && (
        <div style={{
          position: 'absolute',
          bottom: 35,  // Bottom 35px (within the reserved 130px space, supporting 2-3 lines)
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