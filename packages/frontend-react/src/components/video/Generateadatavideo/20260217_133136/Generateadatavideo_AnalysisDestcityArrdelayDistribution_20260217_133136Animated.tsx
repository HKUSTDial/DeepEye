import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 44.6; // Start time of the scene in the original video

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
  
  // Data binding configuration
  const data_binding = {
    "x_axis": {
      "field": "destcity",
      "label": "目的地城市"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均到达延误 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field; // Single y_axis field

  // Color configuration (CRITICAL: MUST use these background colors from JSON config)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Scene-specific colors (chosen based on "delays" semantic)
  const textColor = '#e8eaed'; 
  const barColor = '#ef4444';   // Red for delays
  const highlightColor = '#dc2626'; // Darker red for emphasis
  const gridColor = '#4a4e53';  // Subtle dark grey
  const axisColor = '#888888';  // Medium grey

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  const minItem = data.find((d: any) => d[yField] === minValue);
  
  // D3 scales
  const scales = useMemo(() => {
    const chartWidth = 900; // Adjusted for 960 total width with 30px padding
    const chartHeight = 320; // Max height for bars, leaving room for labels and subtitle zone
    
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Give some extra room above max value
      .range([chartHeight, 0]);

    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, xField, yField, maxValue]);
  
  // Animation configuration
  const animations = [
    {
      "id": "entrance_analysis_destcity_arrdelay_distribution",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation for average arrival delay by destination city",
      "time_start": 44.6,
      "duration": 5.124999999999997
    },
    {
      "id": "emphasis_minneapolis",
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
      "description": "Highlight Minneapolis bar when mentioned",
      "time_start": 49.525,
      "duration": 6.9120000000000035
    },
    {
      "id": "emphasis_los_angeles",
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
      "description": "Highlight Los Angeles bar when mentioned",
      "time_start": 49.525,
      "duration": 6.9120000000000035
    }
  ];

  // Subtitle configuration
  const narrations = [
    {
      "text": "最后，我们分析不同目的城市的平均抵达延误情况。",
      "time_start": 44.6,
      "time_end": 49.525,
      "audio_file": "20260217_133136_analysis_destcity_arrdelay_distribution_narr0.wav"
    },
    {
      "text": "明尼阿波利斯的平均延误最高，而洛杉矶则表现出色，延误时间最短。",
      "time_start": 49.525,
      "time_end": 56.237,
      "audio_file": "20260217_133136_analysis_destcity_arrdelay_distribution_narr1.wav"
    }
  ];

  // Static D3 rendering (initial state for animations)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const { xScale, yScale, chartWidth, chartHeight } = scales;

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Gradient for the highlighted bar (max delay)
    const gradient = defs.append('linearGradient')
      .attr('id', 'delayGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    // Shadow filter (using feDropShadow to avoid blur)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 6)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.4);
    
    // Draw chart group, positioned to allow space for title and subtitle
    const g = svg.append('g').attr('transform', 'translate(30, 80)'); // Shift chart down to leave space for title

    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .tickSizeOuter(0)
      .tickFormat((d) => `${d} min`); // Add 'min' suffix

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .call(g => g.select('.domain').remove()) // Remove the axis line
      .selectAll('text')
      .style('font-size', '14px')
      .style('fill', axisColor)
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.selectAll('.y-axis .tick line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2'); // Dashed grid lines

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // CRITICAL: Position far left to avoid overlap
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .style('font-size', '16px')
      .style('fill', textColor)
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // Draw bars (initial state for animation)
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', chartHeight) // Start from the bottom
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with zero height
      .attr('fill', (d: any) => {
        if (d[yField] === maxValue) return 'url(#delayGradient)';
        if (d[yField] === minValue) return '#20c997'; // A contrasting green for "best performer" (lowest delay)
        return barColor;
      })
      .attr('rx', 8) // Rounded corners
      .style('filter', (d: any) => (d[yField] === maxValue || d[yField] === minValue) ? 'url(#barShadow)' : 'none')
      .style('opacity', 0); // Initial state for animation
    
    // Value labels on top of bars (initial state for animation)
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(1)) // Format to one decimal place
      .attr('fill', (d: any) => {
        if (d[yField] === maxValue) return highlightColor;
        if (d[yField] === minValue) return '#20c997';
        return textColor;
      })
      .style('font-size', '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation
    
    // Category labels below chart (initial state for animation)
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 40) // Positioned relative to chartHeight, within the safe zone
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

  }, [scales, barColor, highlightColor, textColor, gridColor, axisColor, xField, yField, maxValue, minValue, maxItem, minItem]);
  
  // Second useEffect for animations
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { yScale, chartHeight } = scales; // Use chartHeight as innerHeight for bar animations

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');

    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;

      // CRITICAL: If animation has ended, force all elements to their final state
      if (frame >= animEnd) {
        // Bar Chart elements
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = chartHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', chartHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.select('.y-axis-label').style('opacity', 1); // Select the already existing one
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps; // Current elapsed seconds

        // Bars grow from bottom up
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12; // Fixed delay 0.12 seconds
          const animDuration = 0.6; // Fixed duration 0.6 seconds
          const barStartTime = i * delayPerBar;
          const barEndTime = barStartTime + animDuration;

          if (totalTime >= barStartTime && totalTime <= barEndTime) {
            const barProgress = (totalTime - barStartTime) / animDuration;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = chartHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', chartHeight - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barEndTime) {
            // Bar animation completed, set to final state
            const targetHeight = chartHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', chartHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Labels (value and category) fade in with delay
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3; // Additional fixed delay 0.3 seconds
          const animDuration = 0.4; // Fixed duration 0.4 seconds
          const labelStartTime = i * delayPerBar + labelDelay;
          const labelEndTime = labelStartTime + animDuration;

          if (totalTime >= labelStartTime && totalTime <= labelEndTime) {
            const labelProgress = (totalTime - labelStartTime) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEndTime) {
            label.style('opacity', 1);
          }
        });

        // Y-axis label fade in
        const axisStartTime = 0.3; // Fixed delay 0.3 seconds for axis
        const axisDuration = 0.4; // Fixed duration 0.4 seconds
        if (totalTime >= axisStartTime && totalTime <= axisStartTime + axisDuration) {
          const axisProgress = (totalTime - axisStartTime) / axisDuration;
          g.select('.y-axis-label').style('opacity', d3.easeCubicOut(axisProgress));
        } else if (totalTime > axisStartTime + axisDuration) {
          g.select('.y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - Highlight specific data points
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
        // Pulse effect: sin wave for oscillating size/stroke
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // Oscillates between 0.95 and 1.05
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
              highlightedItems.add(d[xField]); // Use xField (e.g., "destcity") as unique identifier
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
            .attr('stroke-width', 4 * maxPulse) // Pulsing stroke width
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none'); // Dim non-highlighted
        }
      });
      
      // Apply emphasis styles to value labels
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });

      // Apply emphasis styles to category labels
      g.selectAll<SVGTextElement, any>('.category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });
    }

    // 3. Restore normal state (only if no emphasis is active AND entrance is complete)
    const entranceEnded = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;
    if (!hasActiveEmphasis && entranceEnded) {
      g.selectAll('.bar').attr('stroke', 'none').style('filter', 'none').style('opacity', 1);
      g.selectAll('.value-label, .category-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, barColor, highlightColor, textColor]);

  // Helper function to get current narration text
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
      justifyContent: 'flex-start', // Align to top to control spacing
      padding: '0 40px' // Horizontal padding
    }}>
      {/* Title (reserved top 30-80px) */}
      <div style={{
        position: 'absolute',
        top: 30, // Top 30px
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Consistent bright text for titles
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各目的地城市平均到达延误
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={960} // Total SVG width
        height={550} // Total SVG height, positioned below title, leaving bottom space
        style={{ 
          marginTop: '0px', // Managed by absolute positioning of title and overall flexbox for main content
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
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