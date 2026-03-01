import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
    { "delay_range": "<-15分钟", "count": 0 },
    { "delay_range": "-15至-5分钟", "count": 5 },
    { "delay_range": "-5至0分钟", "count": 14 },
    { "delay_range": "0至15分钟", "count": 5 },
    { "delay_range": "15至30分钟", "count": 1 },
    { "delay_range": "30至60分钟", "count": 0 },
    { "delay_range": "60至120分钟", "count": 3 },
    { "delay_range": ">120分钟", "count": 2 }
  ];
  
  const xField = "delay_range";
  const yField = "count";
  
  // Color configuration - CRITICAL: Background colors are fixed per JSON config
  const backgroundColor = '#0f1419';
  // const containerBackground = '#0f1419'; // Not directly used in AbsoluteFill, but kept for consistency

  // Scene-specific colors based on "Delays/Problems" semantics
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f59e0b'; // Muted orange for general delays
  const highlightColor = '#ef4444'; // Red for significant delays (accent)
  const gridColor = '#333333'; // Subtle grey for grid lines
  const axisColor = '#888888'; // Lighter grey for axis lines and labels
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // D3 scales and chart dimensions
  const chartWidth = 1000; // Inner width of the chart area
  const chartHeight = 280; // Inner height of the chart area, adjusted to leave space for subtitles
                             // (Absolute Y of chart bottom is 120 + 280 = 400. X-axis label is at 440,
                             // which is well above the 540px limit for bottom 180px subtitle zone)

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding for cleaner bar separation

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Add 20% padding above max value for labels
      .range([chartHeight, 0]); // Invert range for SVG coordinates (0 at top)
      
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight]);
  
  // Animation configuration (from task description)
  const animations = [
    {
      "id": "entrance_analysis_depdelay_distribution",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation for 起飞延误时长分布",
      "time_start": 54.175,
      "duration": 5.112000000000006
    },
    {
      "id": "emphasis_depdelay_ontime_early",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "delay_range": [
            "-5至0分钟",
            "-15至-5分钟"
          ]
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights that are on time or slightly early",
      "time_start": 54.175,
      "duration": 5.112000000000006
    },
    {
      "id": "emphasis_depdelay_long_delay",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "delay_range": [
            "60至120分钟",
            ">120分钟"
          ]
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with long delays (over 60 minutes)",
      "time_start": 59.087,
      "duration": 5.037999999999994
    }
  ];

  // Subtitle configuration (from task description)
  const narrations = [
    {
      "text": "深入来看，大部分航班能准点或略微提前起飞。",
      "time_start": 54.175,
      "time_end": 59.087,
      "audio_file": "20260217_135016_analysis_depdelay_distribution_narr0.wav"
    },
    {
      "text": "但也有少数航班，面临超过60分钟的长时间延误。",
      "time_start": 59.087,
      "time_end": 63.925,
      "audio_file": "20260217_135016_analysis_depdelay_distribution_narr1.wav"
    }
  ];

  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 54.175;  // Start time of the scene in the original video

  // Helper to get current narration text
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  // First useEffect for static rendering and initial state for animations
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    // Apply SVG clarity optimizations
    svg.attr('shape-rendering', 'geometricPrecision')
       .attr('text-rendering', 'geometricPrecision');
    
    const defs = svg.append('defs');
    
    // Gradient for highlighted bars (long delays)
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8)?.toString() || '#a00');
    
    // Shadow filter (using feDropShadow to avoid blurring the actual shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group, translated for margins
    // 80px left margin, 40px top margin relative to SVG container
    const g = svg.append('g').attr('transform', `translate(80, 40)`);
    const {xScale, yScale} = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across the chart width
        .tickFormat(() => '') // No labels for grid lines
        .ticks(5)) // 5 ticks for the y-axis
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .style('opacity', 0); // Initial state for animation

    // X-axis (category labels)
    const xAxisGroup = g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`) // Position at the bottom of the chart area
      .call(d3.axisBottom(xScale).tickSizeOuter(0)); // No outer ticks
    
    xAxisGroup.selectAll('text')
      .attr('class', 'category-label') // Added class for animation
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .attr('y', 15) // Adjust tick label position below the axis line
      .style('opacity', 0); // Initial state for animation
    
    xAxisGroup.select('.domain').attr('stroke', axisColor); // Color the axis line

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 40) // Positioned below tick labels, within subtitle safe zone
      .attr('text-anchor', 'middle')
      .attr('fill', axisColor)
      .style('font-size', '18px')
      .style('font-weight', '500')
      .text('延误时长 (分钟)')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // Y-axis (value labels)
    const yAxisGroup = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5)); // 5 ticks for the y-axis
    
    yAxisGroup.selectAll('text')
      .attr('class', 'y-tick-label') // Added class for animation
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    yAxisGroup.select('.domain').attr('stroke', axisColor); // Color the axis line

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // CRITICAL: At least -70 to avoid overlap with tick numbers
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`)
      .attr('fill', axisColor)
      .style('font-size', '18px')
      .style('font-weight', '500')
      .text('航班数量')
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
      .attr('y', chartHeight) // Start at the bottom for animation
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with 0 height for animation
      .attr('fill', (d: any) => {
        // Highlight bars representing delays > 60 minutes
        if (d[xField] === "60至120分钟" || d[xField] === ">120分钟") {
          return 'url(#highlightGradient)';
        }
        return barColor;
      })
      .attr('rx', 6) // Rounded corners for a softer look
      .style('filter', 'url(#shadow)') // Apply shadow effect
      .style('opacity', 0); // Initial state for animation
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight) // Start at the bottom for animation
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField] > 0 ? d[yField].toString() : '') // Only show label for non-zero counts
      .attr('fill', (d: any) => {
        if (d[xField] === "60至120分钟" || d[xField] === ">120分钟") {
          return highlightColor; // Highlighted label color
        }
        return textColor;
      })
      .style('font-size', '16px')
      .style('font-weight', '700') // Bold for emphasis
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

  }, [scales, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight]);


  // Second useEffect for ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {xScale, yScale} = scales;
    const innerHeight = chartHeight; // Use chartHeight as innerHeight for bar animations

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      if (frame >= animEnd) {
        // Entrance animation completed, force all elements to final state
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label, .y-tick-label, .x-axis-label, .y-axis-label').style('opacity', 1);
        g.selectAll('.grid-y line').style('opacity', 1); // Grid lines also fade in
        
        // Continue executing emphasis animations (don't return)
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps; // Current elapsed seconds

        // Bar animation (grow from bottom)
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;  // Fixed delay 0.12 seconds
          const animDuration = 0.6;   // Fixed duration 0.6 seconds
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
            // Bar animation completed, set to final state
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Value labels and Category labels fade in
        g.selectAll<SVGTextElement, any>('.value-label, .category-label, .y-tick-label').each(function(d: any, i: number) {
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
        
        // Axis labels and Grid lines fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', eased);
          g.selectAll('.grid-y line').style('opacity', eased);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
          g.selectAll('.grid-y line').style('opacity', 1);
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
      
      // Calculate average pulse for synchronized effect
      let maxPulse = 1; // Default to 1, will increase if pulsing
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Pulse effect: sin wave for oscillatory motion, scaled to 1.0-1.1
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // 6 pulses over duration
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting
      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter && filter.delay_range) { // Ensure delay_range exists
          filter.delay_range.forEach((range: string) => {
            highlightedItems.add(range);
          });
        }
      });

      // Process all bars (avoid loop overwriting)
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red border
            .attr('stroke-width', 4 * maxPulse) // Pulsing border width
            .style('filter', 'url(#shadow) drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3) // Reduce opacity for non-highlighted bars
             .attr('stroke', 'none')
             .style('filter', 'url(#shadow)'); // Keep original shadow
        }
      });

      // Process value labels
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          label.style('opacity', 1).attr('fill', highlightColor); // Ensure highlighted label is visible and red
        } else {
          label.style('opacity', 0.3).attr('fill', textColor); // Dim non-highlighted labels
        }
      });
      
      // Also dim other labels/axes/grid if emphasis is active
      g.selectAll('.category-label, .y-tick-label, .x-axis-label, .y-axis-label').each(function() {
        d3.select(this).style('opacity', 0.3);
      });
      g.selectAll('.grid-y line').style('opacity', 0.1); // Dim grid lines further
    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation is done)
    const entranceAnimFinished = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;

    if (!hasActiveEmphasis && entranceAnimFinished) {
      // Restore bars to default appearance
      g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1).style('filter', 'url(#shadow)');
      g.selectAll('.value-label').style('opacity', 1).attr('fill', (d: any) => {
        // Restore static highlight color for specific labels if applicable
        if (d[xField] === "60至120分钟" || d[xField] === ">120分钟") {
          return highlightColor; 
        }
        return textColor;
      });
      
      // Restore all other labels/axes/grid
      g.selectAll('.category-label, .y-tick-label, .x-axis-label, .y-axis-label').style('opacity', 1);
      g.selectAll('.grid-y line').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, barColor, highlightColor, textColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to start to manage top/bottom space
      padding: '0px 40px' // Left/right padding
    }}>
      {/* Title - positioned absolutely to reserve top 80px */}
      <div style={{
        position: 'absolute',
        top: 30, // Start title at 30px from top
        left: 0,
        right: 0,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Light color for title on dark background
        textAlign: 'center',
        zIndex: 10, // Ensure title is above SVG content
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        起飞延误时长分布
      </div>
      
      {/* Chart SVG container */}
      <svg 
        ref={svgRef} 
        width={1160} // Total SVG width (chartWidth + 2 * left/right margins)
        height={460} // Total SVG height (adjusted to fit within 720px, leaving 180px for subtitles)
        style={{ 
          marginTop: '80px', // Push chart down to clear the title area (80px from top)
          overflow: 'visible' // Ensure shadows and labels are not clipped by SVG boundary
        }} 
      />

      {/* Subtitle Display Logic */}
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
          fontFamily: 'system-ui, -apple-system, sans-serif',
          WebkitFontSmoothing: 'antialiased',
          textRendering: 'geometricPrecision'
        }}>
          {getCurrentNarration().text}
        </div>
      )}
    </AbsoluteFill>
  );
};