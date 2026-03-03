import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 43.425;  // Start time of the scene in the original video

  // Animation Configuration
  const animations = [
    {
      "id": "entrance_analysis_destcity_arrdelay_distribution",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation for destination city average arrival delay distribution.",
      "time_start": 43.425,
      "duration": 3.775000000000003
    },
    {
      "id": "emphasis_minneapolis_delay",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "destcity": "Minneapolis"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Minneapolis when its highest average delay is mentioned.",
      "time_start": 47.0,
      "duration": 7.374999999999997
    },
    {
      "id": "emphasis_losangeles_delay",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "destcity": "Los Angeles"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Los Angeles when its lowest average delay is mentioned.",
      "time_start": 47.0,
      "duration": 7.374999999999997
    }
  ];

  // Subtitle Configuration
  const narrations = [
    {
      "text": "那么，目的城市对延误有何影响呢？",
      "time_start": 43.425,
      "time_end": 47.0,
      "audio_file": "20260217_135016_analysis_destcity_arrdelay_distribution_narr0.wav"
    },
    {
      "text": "明尼阿波利斯平均到达延误最高，而洛杉矶的表现最佳，仅5.13分钟。",
      "time_start": 47.0,
      "time_end": 54.175,
      "audio_file": "20260217_135016_analysis_destcity_arrdelay_distribution_narr1.wav"
    }
  ];
  
  // Hardcoded data
  const data = [
  {
    "destcity": "Boston",
    "avg_arrdelay": 12.52,
    "count": 385
  },
  {
    "destcity": "Dallas",
    "avg_arrdelay": 15.78,
    "count": 608
  },
  {
    "destcity": "Los Angeles",
    "avg_arrdelay": 5.13,
    "count": 514
  },
  {
    "destcity": "Minneapolis",
    "avg_arrdelay": 19.58,
    "count": 439
  },
  {
    "destcity": "New York",
    "avg_arrdelay": 15.04,
    "count": 769
  },
  {
    "destcity": "San Francisco",
    "avg_arrdelay": 13.05,
    "count": 459
  },
  {
    "destcity": "Washington",
    "avg_arrdelay": 13.95,
    "count": 583
  }
];
  
  // Extract field names from data_binding
  const xField = "destcity";
  const yField = "avg_arrdelay";
  
  // Color configuration (background colors are CRITICAL and fixed as per JSON config)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; 
  
  // Scene-specific colors based on "flight delay statistics" and "comparison" semantics
  const textColor = '#e8eaed'; // Light grey for readability on dark background
  const barColor = '#3b82f6';   // A vibrant blue for general bars (analytical/data point tone)
  const highlightColorMax = '#ef4444'; // Red for highest delay (problem/warning tone)
  const highlightColorMin = '#10b981'; // Green for lowest delay (positive/best performance tone)
  const gridColor = '#4a5568';  // Subtle grey-blue for grid lines
  const axisColor = '#6b7280';  // Slightly darker grey-blue for axis elements
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  const minItem = data.find((d: any) => d[yField] === minValue);

  // Chart dimensions (Canvas: 1280x720px)
  const chartWidth = 960; // Overall SVG width
  const chartHeight = 550; // Overall SVG height
  // Margins adjusted for title (top: 80px) and subtitle zone (bottom: 180px)
  const margin = { top: 80, right: 60, bottom: 180, left: 100 }; 
  const innerWidth = chartWidth - margin.left - margin.right; // Actual chart drawing area width
  const innerHeight = chartHeight - margin.top - margin.bottom; // Actual chart drawing area height

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerWidth])
      .padding(0.2);
    
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Extend domain slightly above max for label space
      .range([innerHeight, 0]); // In SVG, 0 is top, innerHeight is bottom
      
    return { xScale, yScale };
  }, [data, innerWidth, innerHeight, maxValue]);
  
  // 1. Static D3 Rendering (Modified for initial animation state)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear SVG contents on re-render
    
    const { xScale, yScale } = scales;

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Shadow filter (use feDropShadow to avoid blur on shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
      
    // Linear gradient for the highest delay bar
    const maxGradient = defs.append('linearGradient')
      .attr('id', 'maxGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    maxGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColorMax)?.brighter(0.5)?.toString() || highlightColorMax);
    maxGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorMax);

    // Linear gradient for the lowest delay bar
    const minGradient = defs.append('linearGradient')
      .attr('id', 'minGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    minGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColorMin)?.brighter(0.5)?.toString() || highlightColorMin);
    minGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorMin);

    // Chart group - translated to apply margins
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    // Y-axis grid lines (before bars for background effect)
    g.append('g')
      .attr('class', 'grid-y')
      .attr('color', gridColor)
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => '')
      )
      .select('.domain').remove(); // Remove the axis line from grid
    
    // Draw bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      // Initial state for animation: height 0, y at bottom, opacity 0
      .attr('y', innerHeight) 
      .attr('width', xScale.bandwidth())
      .attr('height', 0) 
      .attr('fill', (d: any) => {
        if (d[xField] === maxItem?.destcity) return 'url(#maxGradient)';
        if (d[xField] === minItem?.destcity) return 'url(#minGradient)';
        return barColor;
      })
      .attr('rx', 8) // Rounded corners for aesthetics
      .style('filter', 'url(#shadow)') // Apply shadow effect
      .style('opacity', 0); // Initial opacity 0 for animation
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(2)}`) // Format to 2 decimal places
      .attr('fill', (d: any) => {
        if (d[xField] === maxItem?.destcity) return highlightColorMax;
        if (d[xField] === minItem?.destcity) return highlightColorMin;
        return textColor;
      })
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0 for animation
    
    // X-axis category labels
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', innerHeight + 30) 
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0 for animation

    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d) => `${d} min`);
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.select('.y-axis').selectAll('line').attr('stroke', axisColor); // Set tick line color
    g.select('.y-axis').select('.domain').remove(); // Remove the axis line from y-axis

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Position it further left from the chart area
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${innerHeight / 2})`)
      .text("平均到达延误 (分钟)")
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0 for animation

  }, [scales, data, xField, yField, maxValue, minValue, maxItem, minItem, barColor, highlightColorMax, highlightColorMin, textColor, gridColor, axisColor, innerWidth, innerHeight, margin.left, margin.top, margin.bottom, chartWidth, chartHeight]); 

  // 2. Animation Logic (Second useEffect)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { xScale, yScale } = scales;

    // 1. ENTRANCE ANIMATION - Check if entrance animation is configured
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // CRITICAL: After animation ends, force all elements to final state
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
        g.selectAll('.value-label, .category-label, .y-axis-label').style('opacity', 1);
        // Grid lines are static, no need to animate their opacity.
        
        // Continue to emphasis animation check (don't return)
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

        // Bars grow from bottom
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;  // Fixed delay 0.12 seconds
          const animDuration = 0.6;   // Fixed duration 0.6 seconds
          const barAnimStart = i * delayPerBar;
          const barAnimEnd = barAnimStart + animDuration;

          if (totalTime >= barAnimStart && totalTime <= barAnimEnd) {
            // Bar animation in progress
            const barProgress = (totalTime - barAnimStart) / animDuration;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barAnimEnd) {
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
          const labelAnimStart = i * delayPerBar + labelDelay;
          const labelAnimEnd = labelAnimStart + animDuration;

          if (totalTime >= labelAnimStart && totalTime <= labelAnimEnd) {
            const labelProgress = (totalTime - labelAnimStart) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelAnimEnd) {
            label.style('opacity', 1);
          }
        });
        
        // Y-axis label fade in
        const axisLabelDelay = 0.3; // Fixed delay 0.3 seconds
        const axisLabelDuration = 0.4; // Fixed duration 0.4 seconds
        const axisLabelAnimStart = axisLabelDelay;
        const axisLabelAnimEnd = axisLabelAnimStart + axisLabelDuration;
        
        if (totalTime >= axisLabelAnimStart && totalTime <= axisLabelAnimEnd) {
          const axisLabelProgress = (totalTime - axisLabelAnimStart) / axisLabelDuration;
          g.selectAll('.y-axis-label').style('opacity', d3.easeCubicOut(axisLabelProgress));
        } else if (totalTime > axisLabelAnimEnd) {
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
      
      // Calculate all active animations' average pulse (for synchronous effect)
      let maxPulse = 1; // Base pulse
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Pulse effect: goes from 1 to 1.05 and back, 6 cycles over duration
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; 
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting
      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          // Find matching data items
          data.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d[xField]);  // Use xField (e.g., "destcity") as unique identifier
            }
          });
        }
      });

      // Process all bars/data points at once
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red border for highlight
            .attr('stroke-width', 4 * maxPulse) // Pulse stroke width
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3) // Reduce opacity for non-highlighted bars
             .attr('stroke', 'none')
             .style('filter', 'url(#shadow)'); // Reapply original shadow
        }
      });
      
      // Also adjust value labels and category labels for highlighted items
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1);
        } else {
          label.style('opacity', 0.3);
        }
      });

    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation is complete)
    const entranceAnimCompleted = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;
    
    if (!hasActiveEmphasis && entranceAnimCompleted) {
      // Bar Chart elements
      g.selectAll('.bar')
        .attr('stroke', 'none') // Remove stroke
        .style('opacity', 1)    // Restore full opacity
        .style('filter', 'url(#shadow)'); // Restore original shadow
      g.selectAll('.value-label, .category-label, .y-axis-label').style('opacity', 1); // Restore full opacity for labels
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, innerHeight, barColor, highlightColorMax, highlightColorMin, textColor]);

  // Subtitle display logic
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };

  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to start to control vertical positioning
      padding: '0px 0px' 
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Position 30px from top, reserving top 80px for subtitle overlay
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各目的城市平均延误情况
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={chartWidth} 
        height={chartHeight} 
        style={{ 
          marginTop: '60px', // Push the SVG down to make room for the title above
          shapeRendering: 'geometricPrecision', // Critical for SVG clarity
          textRendering: 'geometricPrecision' // Critical for SVG text clarity
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