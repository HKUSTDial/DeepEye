import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
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
  
  // Data binding
  const data_binding = {
    "x_axis": {
      "field": "destcity",
      "label": "目的地城市"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均延误时间 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string, label: string }).field;

  // Color configuration (CRITICAL: background colors are fixed from JSON config!)
  const backgroundColor = '#0f1419'; 
  
  // Scene-specific colors based on "delay" semantics (orange/red for problems/delays)
  const textColor = '#e8eaed'; 
  const barColor = '#f59e0b'; // Amber-orange for general delays
  const highlightColor = '#ef4444'; // Red for the longest delay (explicitly mentioned in narration)
  const gridColor = '#374151'; // Subtle dark gray for grids
  const axisColor = '#6b7280'; // Medium gray for axes and labels
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;

  // D3 scales
  const scales = useMemo(() => {
    const chartWidth = 800; // SVG width (960) - left margin (80) - right margin (80)
    const chartHeight = 400; // Max available height for bars, leaves space for labels and subtitle zone

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Give some room above the max bar for labels
      .range([chartHeight, 0]); // Invert Y-axis for SVG coordinates (0 at top, chartHeight at bottom)

    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, xField, yField, maxValue]);
  
  // Remotion hooks and scene offset
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 22.288;  // Start time of the scene in the original video

  // Animation configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 22.288,
      "duration": 4.224000000000001
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
      "description": "Highlight Minneapolis when mentioned",
      "time_start": 26.312,
      "duration": 10.100000000000001
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
      "description": "Highlight Los Angeles when mentioned",
      "time_start": 26.312,
      "duration": 10.100000000000001
    }
  ];

  // Subtitle Configuration
  const narrations = [
    {
      "text": "接下来，我们看看各城市的平均抵达延误。",
      "time_start": 22.288,
      "time_end": 26.312,
      "audio_file": "20260217_150441_analysis_destcity_arrival_delays_narr0.wav"
    },
    {
      "text": "明尼阿波利斯延误最长，达19.58分钟；相比之下，洛杉矶表现最佳，平均延误仅5.13分钟。",
      "time_start": 26.312,
      "time_end": 36.212,
      "audio_file": "20260217_150441_analysis_destcity_arrival_delays_narr1.wav"
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
  
  // First useEffect for static rendering and initial animation state
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create gradient for the highlighted bar (from highlightColor to barColor)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); 
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor); 
    
    // Shadow filter (CRITICAL: use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Draw chart with proper spacing
    // Translate 'g' to leave space for title (top 80-100px) and left/right margins
    const { xScale, yScale, chartWidth, chartHeight } = scales;
    const g = svg.append('g').attr('transform', 'translate(80, 80)'); 
    
    // Add Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across the chart
        .tickFormat(() => "") // No labels for grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .style('opacity', 0); // Initial state for animation

    // Add Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5)) // 5 ticks for readability
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // CRITICAL: At least -70 to avoid overlap with tick numbers
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`) // Rotate around its new x,y
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
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
      .attr('y', chartHeight) // Initial state for animation: start from bottom
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial state for animation: height 0
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 6) // Rounded corners for aesthetics
      .style('filter', 'url(#shadow)')
      .style('opacity', 0); // Initial state for animation
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12) // Position slightly above the bar (final state)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2) + '分钟') // Format to 2 decimal places and add unit
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '20px' : '16px') // Larger for max value
      .style('font-weight', (d: any) => d[yField] === maxValue ? '800' : '500') // Bolder for max value
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation
    
    // Category labels (X-axis tick labels) below chart
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`) // Position X-axis at the bottom of the chart drawing area
      .call(d3.axisBottom(xScale))
      .selectAll('text')
      .attr('fill', axisColor)
      .attr('y', 15) // Adjust position relative to axis line, ensures visibility
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 40) // Position X-axis label below tick labels.
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // Select existing axis paths and lines and apply color (CRITICAL: correct selection method)
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor).style('opacity', 0); // Initial state for animation
    g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor).style('opacity', 0); // Initial state for animation

  }, [scales, data, xField, yField, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, data_binding]);
  
  // Second useEffect for ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { yScale, chartHeight } = scales;
    const innerHeight = chartHeight; // Renamed for clarity in animation context

    // 1. ENTRANCE ANIMATION - Check if active or completed
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    const isEntranceCompleted = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;

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
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label').style('opacity', 1);
        g.selectAll('.x-axis .tick text').style('opacity', 1); // Category labels (x-axis ticks)
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        g.selectAll('.grid-y line').style('opacity', 0.3); // Default opacity for grid lines
        g.select('.y-axis').selectAll('line, path').style('opacity', 1); // Axis lines/paths
        g.select('.x-axis').selectAll('line, path').style('opacity', 1); // Axis lines/paths

      } else if (frame >= animStart) {
        // 入场动画进行中
        const totalTime = (frame - animStart) / fps;  // 当前经过的秒数

        // Bars grow
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;  // Each bar delayed by 0.12 seconds
          const animDuration = 0.6;   // Single bar animation duration 0.6 seconds
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
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Value labels and Category labels (X-axis ticks) fade in
        g.selectAll<SVGTextElement, any>('.value-label, .x-axis .tick text').each(function(d: any, i: number) {
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
        
        // Axis labels (X-axis label, Y-axis label) fade in
        const axisLabelStart = 0.3; // Start after a small delay
        const axisLabelDuration = 0.4;
        if (totalTime >= axisLabelStart && totalTime <= axisLabelStart + axisLabelDuration) {
          const axisProgress = (totalTime - axisLabelStart) / axisLabelDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', eased);
        } else if (totalTime > axisLabelStart + axisLabelDuration) {
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        }

        // Grid lines and axis lines/paths fade in
        const gridStart = 0.2;
        const gridDuration = 0.4;
        if (totalTime >= gridStart && totalTime <= gridStart + gridDuration) {
          const gridProgress = (totalTime - gridStart) / gridDuration;
          const eased = d3.easeCubicOut(gridProgress);
          g.selectAll('.grid-y line').style('opacity', eased * 0.3); // Fade to default 0.3 opacity
          g.select('.y-axis').selectAll('line, path').style('opacity', eased);
          g.select('.x-axis').selectAll('line, path').style('opacity', eased);
        } else if (totalTime > gridStart + gridDuration) {
          g.selectAll('.grid-y line').style('opacity', 0.3);
          g.select('.y-axis').selectAll('line, path').style('opacity', 1);
          g.select('.x-axis').selectAll('line, path').style('opacity', 1);
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
      
      // Calculate max pulse for stroke width
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // 6 cycles over duration, pulse 1.0 to 1.05
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

      // Process all bars at once
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red border for highlight
            .attr('stroke-width', 4 * maxPulse) // Pulsing stroke width
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          // Non-highlighted bars (restore original fill, but reduce opacity and remove stroke)
          bar.style('opacity', 0.3)
             .attr('stroke', 'none')
             .style('filter', 'url(#shadow)'); // Restore original shadow filter
        }
      });

      // Also adjust opacity of value labels
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });

      // Adjust opacity of x-axis tick labels
      g.selectAll<SVGTextElement, any>('.x-axis .tick text').each(function(d: any) {
        const labelText = d3.select(this).text();
        const isHighlighted = highlightedItems.has(labelText); 
        d3.select(this).style('opacity', isHighlighted ? 1 : 0.3);
      });
      
    }

    // 3. Restore normal state (only if no emphasis is active AND entrance is completed)
    if (!hasActiveEmphasis && isEntranceCompleted) {
      // Bar Chart elements
      g.selectAll('.bar')
        .attr('stroke', 'none') // Remove stroke
        .style('opacity', 1)
        .style('filter', 'url(#shadow)'); // Restore default shadow filter
      
      g.selectAll('.value-label').style('opacity', 1);
      g.selectAll('.x-axis .tick text').style('opacity', 1); // Category labels
      g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
      g.selectAll('.grid-y line').style('opacity', 0.3);
      g.select('.y-axis').selectAll('line, path').style('opacity', 1);
      g.select('.x-axis').selectAll('line, path').style('opacity', 1);
    }
    // Note: If entrance is still active, entrance anim handles opacity.
    // If emphasis is active, emphasis anim handles opacity.

  }, [frame, fps, scales, animations, data, xField, yField, maxValue, sceneStartOffset, barColor, highlightColor, textColor, gridColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 40px' // Horizontal padding, vertical space managed by SVG/g transforms
    }}>
      {/* Title (positioned at top 30px, leaving ample space for subtitle overlay) */}
      <div style={{
        position: 'absolute',
        top: 30, 
        fontSize: '36px',
        fontWeight: '700',
        color: textColor, 
        textAlign: 'center',
        width: '100%', 
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各城市平均抵达延误时间
      </div>
      
      {/* Chart - centered, with space for labels and subtitle area */}
      <svg 
        ref={svgRef} 
        width={960} 
        height={550} // SVG height, positioned relative to AbsoluteFill
        style={{ 
          marginTop: '20px', // Pushes the SVG down, ensuring top 80-100px clear
          shapeRendering: 'geometricPrecision', // CRITICAL for SVG clarity
          textRendering: 'geometricPrecision' // CRITICAL for SVG clarity
        }} 
      />

      {/* Subtitle display logic */}
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