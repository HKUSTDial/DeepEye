import React, {useEffect, useRef, useMemo, useCallback} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  // All times in the configuration are absolute video times.
  // Subtract sceneStartOffset to make them relative to the component's start (frame 0).
  const sceneStartOffset = 30.938;

  // Hardcoded data
  const data = [
  {
    "destcity": "明尼阿波利斯",
    "avg_arrdelay": 120.33
  },
  {
    "destcity": "波士顿",
    "avg_arrdelay": -4.38
  },
  {
    "destcity": "华盛顿",
    "avg_arrdelay": -9.0
  },
  {
    "destcity": "纽约",
    "avg_arrdelay": -9.2
  },
  {
    "destcity": "洛杉矶",
    "avg_arrdelay": -12.17
  },
  {
    "destcity": "旧金山",
    "avg_arrdelay": -22.0
  }
];
  
  // Extract field names from data_binding
  const xField = "destcity";
  const yField = "avg_arrdelay";
  
  // Color configuration (MUST use fixed background, other colors chosen based on scene semantics)
  const backgroundColor = '#0f1419'; // CRITICAL: DO NOT CHANGE - from JSON config
  const containerBackground = '#0f1419'; // CRITICAL: DO NOT CHANGE - from JSON config
  
  const textColor = '#e8ea99'; // Light text for dark background
  const delayColor = '#f97316'; // Vibrant orange for delays
  const earlyColor = '#38bdf8'; // Sky blue for early arrivals
  const highlightDelayColor = '#fbbf24'; // Amber for the highest delay (Minneapolis)
  const gridColor = '#333333'; // Subtle grid lines
  const axisColor = '#666666'; // Subtle axis lines

  // Animation configuration
  const animations = useMemo(() => ([
    {
      "id": "entrance_analysis_destcity_arrdelay_distribution",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation for destination city arrival delay distribution.",
      "time_start": 30.938,
      "duration": 11.512
    },
    {
      "id": "emphasis_minneapolis_delay",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "destcity": "明尼阿波利斯"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Minneapolis bar as the city with highest average arrival delay.",
      "time_start": 34.9,
      "duration": 7.350000000000001,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "明尼阿波利斯",
        "word_time": 34.9
      }
    }
  ]), []);

  // Subtitle configuration
  const narrations = useMemo(() => ([
    {
      "text": "现在，我们分析目的地城市的到达延误。明尼阿波利斯平均延误高达120分钟，而多数城市航班甚至提前抵达。",
      "time_start": 30.938,
      "time_end": 42.25,
      "audio_file": "20260217_143314_analysis_destcity_arrdelay_distribution_narr0.wav"
    }
  ]), []);
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // D3 scales
  const scales = useMemo(() => {
    // Chart dimensions within the SVG
    // SVG total height is 460 (720 - 80px top reserve - 180px bottom reserve)
    // g transform translate(80, 20) means 20px top padding inside SVG, 80px left padding
    const chartWidth = 960 - 80 * 2; // 800px
    const chartHeight = 460 - 20 - 20; // 420px (leaving space for x-axis labels at bottom)
    
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2); // Padding between bars
    
    const yScale = d3.scaleLinear()
      .domain([minValue * 1.1, maxValue * 1.1]) // Add padding to min/max values
      .range([chartHeight, 0]); // Invert range for SVG coordinates (y=0 is top)
      
    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, maxValue, minValue]);
  
  // First useEffect for static rendering and initial animation state
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders
    
    const { xScale, yScale, chartWidth, chartHeight } = scales;

    // Define SVG filters for shadow
    const defs = svg.append('defs');
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    // Main chart group, translated to leave margins
    // CRITICAL: svg top: 80, g transform translate(80, 20)
    // Lowest content y (relative to g) should be <= 440 (20 + 420 (chartHeight) + 20 (x-axis labels))
    const g = svg.append('g').attr('transform', 'translate(80, 20)');

    // Add X-axis (line at y=0) - no actual axis line, just the category labels
    // We'll draw a horizontal line at yScale(0) to represent the zero-delay line
    g.append('line')
      .attr('x1', 0)
      .attr('y1', yScale(0))
      .attr('x2', chartWidth)
      .attr('y2', yScale(0))
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);

    // Add Y-axis grid lines and labels
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickSizeInner(-chartWidth)
      .tickSizeOuter(0)
      .tickFormat((d: any) => `${d} min`);

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .call(g => g.select('.domain').remove()) // Remove the axis line
      .call(g => g.selectAll('.tick line')
        .attr('stroke-opacity', 0.2)
        .attr('stroke', gridColor)
        .style('opacity', 0) // Initial state for animation
      )
      .call(g => g.selectAll('.tick text')
        .attr('fill', axisColor)
        .style('font-size', '14px')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision')
        .style('opacity', 0) // Initial state for animation
      );

    // Draw bars for positive and negative values
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', yScale(0)) // Initial state for animation: start at zero line
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial state for animation: zero height
      .attr('fill', (d: any) => {
        if (d === maxItem) return highlightDelayColor; // Highest delay
        return d[yField] > 0 ? delayColor : earlyColor; // Other delays vs. early arrivals
      })
      .attr('rx', 8) // Rounded corners
      .style('filter', (d: any) => d === maxItem ? 'url(#shadow)' : 'none')
      .style('opacity', 0); // Initial state for animation

    // Value labels on top/bottom of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => d[yField] >= 0 ? yScale(d[yField]) - 10 : yScale(d[yField]) + 20) // Position for final state, will animate opacity
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(1))
      .attr('fill', (d: any) => d === maxItem ? highlightDelayColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // Category labels (X-axis labels)
    // CRITICAL: Position at y <= 440 (relative to g) to reserve bottom 180px for subtitles
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 20) // Position below the chart area
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

  }, [scales, maxValue, minValue, maxItem, textColor, delayColor, earlyColor, highlightDelayColor, gridColor, axisColor]);
  
  // Second useEffect for animation logic
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { yScale, chartHeight } = scales;
    const innerHeight = chartHeight; // This corresponds to the range[0] of yScale

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStartFrame = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEndFrame = animStartFrame + entranceAnim.duration * fps;
      
      // ✅ CRITICAL: After entrance animation ends, force all elements to final state
      if (frame >= animEndFrame) {
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = Math.abs(yScale(d[yField]) - yScale(0));
          const targetY = d[yField] >= 0 ? yScale(d[yField]) : yScale(0);
          bar
            .attr('height', targetHeight)
            .attr('y', targetY)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis .tick text, .y-axis .tick line').style('opacity', 1);
        
        // Continue to check for emphasis animations
      } else if (frame >= animStartFrame) {
        // Entrance animation in progress
        const totalTime = (frame - animStartFrame) / fps; // Current elapsed seconds in animation

        // Bars grow from bottom
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

            const targetHeight = Math.abs(yScale(d[yField]) - yScale(0));
            const currentHeight = targetHeight * eased;

            // For positive values, bar grows upwards from yScale(0)
            // For negative values, bar grows downwards from yScale(0)
            const currentY = d[yField] >= 0 ? yScale(0) - currentHeight : yScale(0);

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', currentY)
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            // Bar animation completed
            const targetHeight = Math.abs(yScale(d[yField]) - yScale(0));
            const targetY = d[yField] >= 0 ? yScale(d[yField]) : yScale(0);
            bar
              .attr('height', targetHeight)
              .attr('y', targetY)
              .style('opacity', 1);
          }
        });

        // Labels fade in (category + value simultaneously)
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3;  // Additional delay 0.3 seconds
          const animDuration = 0.4; // Fade-in duration 0.4 seconds
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
        
        // Y-axis labels and grid lines fade in
        const axisStart = 0.3; // Relative to totalTime
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.y-axis .tick text, .y-axis .tick line').style('opacity', eased);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis .tick text, .y-axis .tick line').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;
    
    // Collect all currently active emphasis animations
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStartFrame = (anim.time_start - sceneStartOffset) * fps;
      const animDurationFrames = anim.duration * fps;
      return frame >= animStartFrame && frame < animStartFrame + animDurationFrames;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      // Calculate max pulse for all active animations to synchronize effect
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStartFrame = (anim.time_start - sceneStartOffset) * fps;
        const animDurationFrames = anim.duration * fps;
        const progress = (frame - animStartFrame) / animDurationFrames;
        // Pulse effect: sin wave for 3 cycles (PI*6) from 1 to 1.05
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

      // Apply emphasis styles to bars
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red border
            .attr('stroke-width', 4 * maxPulse) // Pulsating border
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none');
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

    // 3. Restore to normal state (only if no active emphasis and entrance animation is done)
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.bar')
        .attr('stroke', 'none')
        .style('opacity', 1)
        .style('filter', (d: any) => d === maxItem ? 'url(#shadow)' : 'none'); // Restore original shadow for maxItem

      g.selectAll('.value-label, .category-label').style('opacity', 1);
      g.selectAll('.y-axis .tick text, .y-axis .tick line').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, maxItem, highlightDelayColor]);

  // Helper function to get current narration
  const getCurrentNarration = useCallback(() => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  }, [frame, fps, narrations, sceneStartOffset]);

  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value: #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align items to the start to precisely control SVG position
      padding: '0 40px' // Horizontal padding
    }}>
      {/* Title - positioned at the top, within the 80px subtitle-safe zone */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from the absolute top
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
      }}>
        按目的地城市平均到达延误
      </div>
      
      {/* Chart - positioned absolutely to fit within the 80px to 540px vertical range */}
      <svg 
        ref={svgRef} 
        width={960} // Total width of the SVG
        height={460} // CRITICAL: SVG height (720 - 80px top - 180px bottom = 460px)
        style={{ 
          position: 'absolute',
          top: 80, // CRITICAL: positioned at 80px from absolute top
          left: '50%',
          transform: 'translateX(-50%)', // Center horizontally
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
        }}>
          {getCurrentNarration()?.text}
        </div>
      )}
    </AbsoluteFill>
  );
};