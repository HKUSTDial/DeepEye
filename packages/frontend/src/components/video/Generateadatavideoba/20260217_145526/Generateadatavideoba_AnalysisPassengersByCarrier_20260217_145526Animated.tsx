import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

// Animation Configuration
const animations = [
  {
    "id": "entrance_anim",
    "type": "entrance",
    "effect": "grow_bars",
    "trigger_narration": 0,
    "description": "Chart entrance animation",
    "time_start": 18.212,
    "duration": 8.613
  },
  {
    "id": "emphasis_AA",
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
    "description": "Highlight AA when mentioned",
    "time_start": 19.487,
    "duration": 7.138000000000002,
    "_debug_info": {
      "word_aligned": true,
      "keyword": "AA",
      "word_time": 19.487
    }
  },
  {
    "id": "emphasis_UA",
    "type": "emphasis",
    "effect": "pulse",
    "trigger_narration": 0,
    "target_data": {
      "data_filter": {
        "carrier": "UA"
      }
    },
    "style": {
      "intensity": 0.1
    },
    "description": "Highlight UA when mentioned",
    "time_start": 20.15,
    "duration": 6.475000000000001,
    "_debug_info": {
      "word_aligned": true,
      "keyword": "UA",
      "word_time": 20.15
    }
  }
];

// Subtitle Configuration
const narrations = [
  {
    "text": "进一步观察，AA和UA承运的旅客数量远超其他航空公司，这让他们延误的影响更为显著。",
    "time_start": 18.212,
    "time_end": 26.625,
    "audio_file": "20260217_145526_analysis_passengers_by_carrier_narr0.wav"
  }
];

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "sum_passengers": 239676,
    "count": 1880
  },
  {
    "carrier": "EV",
    "sum_passengers": 9876,
    "count": 144
  },
  {
    "carrier": "MQ",
    "sum_passengers": 3344,
    "count": 56
  },
  {
    "carrier": "OO",
    "sum_passengers": 29825,
    "count": 319
  },
  {
    "carrier": "UA",
    "sum_passengers": 210452,
    "count": 1358
  }
];
  
  // Data Binding
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "sum_passengers",
      "label": "旅客总数"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  
  // Color configuration (MUST use JSON config values for background)
  const backgroundColor = '#0f1419';
  
  // Scene semantics: "各航空公司旅客总数对比" (Comparison of total passengers for each airline)
  // Narration hints at "延误影响更为显著" (delay impact more significant) for larger carriers.
  // Choosing a blue/purple scheme for data analysis and magnitude, with purple highlight for impact/prominence.
  const textColor = '#e8eaed'; // Light grey for dark background
  const barColor = '#3b82f6'; // Blue for general data visualization
  const highlightColor = '#8b5cf6'; // Purple for highlighting the maximum value
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // D3 scales
  const scales = useMemo(() => {
    // Chart drawing area dimensions within the SVG
    const chartWidth = 960 - 80 * 2; // SVG width (960) - left/right g margin (80*2) = 800
    // Max height for bars, ensuring category labels clear the bottom 180px subtitle zone
    const chartHeightForBars = 320; 

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Padding between bars

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% padding above max value for labels
      .range([chartHeightForBars, 0]); // Invert range for SVG (y=0 is top)
      
    return { xScale, yScale, chartWidth, chartHeightForBars };
  }, [data, xField, yField, maxValue]);

  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 18.212;  // Start time of the scene in the original video

  // Helper function to get current narration
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  // Static D3 rendering (first useEffect)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    const { xScale, yScale, chartHeightForBars } = scales;

    // Define gradients and shadow filters
    const defs = svg.append('defs');
    
    // Linear gradient for the highlighted bar (from highlightColor to a darker shade)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8).toString());
    
    // Drop shadow filter for bars (feDropShadow ensures original shape isn't blurred)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group, translated to provide margins
    const g = svg.append('g').attr('transform', 'translate(80, 40)'); // 80px left, 40px top margin

    // Draw bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      // Initial state for animation: height 0, y at the bottom
      .attr('y', chartHeightForBars) 
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial height 0
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners
      .attr('ry', 8)
      .style('filter', 'url(#shadow)') // Apply shadow filter
      .style('opacity', 0); // Initial opacity 0
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position 15px above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(',')(d[yField])) // Format numbers with commas
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0
    
    // Category labels below the chart (e.g., airline codes)
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeightForBars + 40) // 40px below the highest bar point in chart area
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0
  }, [scales, data, xField, yField, maxValue, barColor, highlightColor, textColor]);

  // Second useEffect for ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { xScale, yScale, chartHeightForBars } = scales;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // CRITICAL: After animation ends, force all elements to final state
      if (frame >= animEnd) {
        // Bar Chart elements
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = chartHeightForBars - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', chartHeightForBars - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        // No explicit x-axis-label, y-axis-label in this chart
        
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
            const targetHeight = chartHeightForBars - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', chartHeightForBars - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            // Bar animation completed
            const targetHeight = chartHeightForBars - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', chartHeightForBars - targetHeight)
              .style('opacity', 1);
          }
        });

        // Labels fade in (category + value simultaneously)
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3;  // Fixed additional delay 0.3 seconds
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
        // No explicit axis labels to animate in this chart
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
      
      // Calculate all active animations' average pulse (for synchronized effect)
      let maxPulse = 1; // Base pulse value
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Pulse effect: sin wave for oscillating size/intensity, range 1.0 to 1.05
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; 
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting (use Set to avoid duplicates)
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
              highlightedItems.add(d[xField]);  // Use xField (e.g., "carrier") as unique identifier
            }
          });
        }
      });

      // Process all bars at once (avoid loop overwriting)
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
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'url(#shadow)'); // Non-highlighted bars reduce opacity, keep original shadow
        }
      });
      
      // Also adjust value and category labels for highlighted items
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1).attr('fill', '#ff6b6b'); // Highlight label color
        } else {
          label.style('opacity', 0.3).attr('fill', textColor); // Dim non-highlighted labels
        }
      });

    }

    // 3. Restore normal state (only when no emphasis is active AND entrance animation is complete)
    // The entranceAnim check ensures we don't restore before the chart is fully drawn.
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      // Bar Chart elements
      g.selectAll('.bar')
        .attr('stroke', 'none')
        .style('opacity', 1)
        .style('filter', 'url(#shadow)'); // Restore original shadow filter
      g.selectAll('.value-label, .category-label')
        .style('opacity', 1)
        .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor); // Restore original colors
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, barColor, highlightColor, textColor, maxValue]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // Unified background from JSON config
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px' // Overall padding for the scene
    }}>
      {/* Scene Title - positioned at the top, allowing space for subtitles below */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top for title
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Bright white for title readability
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司旅客总数对比
      </div>
      
      {/* D3 Chart Container */}
      <svg 
        ref={svgRef} 
        width={960} // Width of the SVG canvas
        height={550} // Height of the SVG canvas, accommodating chart and labels
        style={{ 
          marginTop: '20px', // Push chart down from the title
          shapeRendering: 'geometricPrecision', // Ensures crisp lines and shapes
          textRendering: 'geometricPrecision' // Ensures crisp text
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