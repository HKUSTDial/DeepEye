import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion'; // Added useCurrentFrame, useVideoConfig
import * as d3 from 'd3';

// Animation configuration (provided)
const animations = [
  {
    "id": "entrance_analysis_carrier_depdelay_comparison",
    "type": "entrance",
    "effect": "grow_bars",
    "trigger_narration": 0,
    "description": "Chart entrance animation",
    "time_start": 7.525,
    "duration": 10.499999999999998
  },
  {
    "id": "emphasis_mq_carrier_depdelay",
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
    "description": "Highlight MQ airline and its average departure delay",
    "time_start": 11.913,
    "duration": 5.911999999999999,
    "_debug_info": {
      "word_aligned": true,
      "keyword": "MQ",
      "word_time": 11.913
    }
  }
];

// Subtitle configuration (provided)
const narrations = [
  {
    "text": "首先，我们关注各航空公司的平均出发延误。MQ航空公司表现不佳，平均延误高达33.98分钟。",
    "time_start": 7.525,
    "time_end": 17.825,
    "audio_file": "20260217_160118_analysis_carrier_depdelay_comparison_narr0.wav"
  }
];

export const SceneComponentAnimated: React.FC = () => { // Renamed component
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "avg_depdelay": 15.41,
    "count": 1880
  },
  {
    "carrier": "EV",
    "avg_depdelay": 16.53,
    "count": 144
  },
  {
    "carrier": "MQ",
    "avg_depdelay": 33.98,
    "count": 56
  },
  {
    "carrier": "OO",
    "avg_depdelay": 25.3,
    "count": 319
  },
  {
    "carrier": "UA",
    "avg_depdelay": 25.24,
    "count": 1358
  }
];
  
  // Extract field names from data_binding
  const xField = "carrier";
  const yField = "avg_depdelay";
  const yAxisLabel = "平均出发延误时间 (分钟)";
  
  // Color configuration - CRITICAL: Background colors are fixed!
  const backgroundColor = '#0f1419';
  
  // Other colors chosen based on scene semantics (delays/problems -> red/orange)
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f97316'; // Warm orange for general bars
  const highlightColor = '#ef4444'; // Intense red for the highest delay
  const gridColor = '#2d333b'; // Subtle dark gray for grid lines
  const axisColor = '#5a626a'; // Slightly brighter gray for axis lines and ticks
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // D3 scales
  // SVG size is 960x550 from template.
  // We apply a 'g' transform of translate(80, 40) for chart margins.
  // This leaves 960 - 80 (left margin) - 80 (right margin/padding) = 800px for the chartWidth.
  // For chartHeight: 550 (SVG height) - 40 (top margin) - 180 (bottom subtitle safe zone) - 0 (padding) = 330px.
  const chartWidth = 800; 
  const chartHeight = 330; 
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2); // Padding between bars
      
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% padding above max value for labels
      .range([chartHeight, 0]); // Invert Y-axis for SVG (0 at top)
      
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField]);

  // Remotion hooks and scene time offset
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sceneStartOffset = 7.525; // Start time of the scene in the original video
  
  // Helper to get current narration
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };

  // Static D3 rendering (initial state for animations)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous drawings
    
    // Add definitions for gradients and shadows
    const defs = svg.append('defs');
    
    // Create linear gradient for the highlighted bar (red/orange theme)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', barColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    // Drop shadow filter for clarity (CRITICAL: use feDropShadow, not feGaussianBlur+feOffset!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Chart group with margins applied via transform
    const g = svg.append('g').attr('transform', 'translate(80, 40)');
    const {xScale, yScale} = scales;
    
    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .ticks(5) // Approximately 5 ticks
        .tickSize(-chartWidth) // Extend grid lines across the chart width
        .tickFormat(() => "") // No labels for grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .style('opacity', 0); // Initial state for animation
      
    // Y-axis (only path and text, no line for the axis itself)
    const yAxis = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat((d: any) => `${d.toFixed(0)} 分钟`)); // Format ticks to whole numbers
      
    yAxis.selectAll('path').remove(); // Remove the main Y-axis line
    yAxis.selectAll('line') // Keep only the tick lines and color them
      .attr('stroke', axisColor);
    yAxis.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label') // Added class for easier selection
      .attr('x', -70) // CRITICAL: Position at least -70px to the left of the axis to avoid overlap with tick numbers!
      .attr('y', chartHeight / 2) // Center vertically relative to chart height
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`) // Rotate around its own position
      .text(yAxisLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
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
      .attr('y', chartHeight) // Initial state for animation (start from bottom)
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial state for animation (start from 0 height)
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for a softer look
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none')
      .style('opacity', 0); // Initial state for animation
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) 
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) 
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
      .attr('y', chartHeight + 30) 
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

  }, [scales, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight, xField, yField, yAxisLabel, data]); 
  
  // Animation logic
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale} = scales;
    const innerHeight = chartHeight; // Use chartHeight as innerHeight for bar animations

    // 1. ENTRANCE ANIMATION - Check if active
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // ✅ CRITICAL: After animation ends, force all elements to final state
      if (frame >= animEnd) {
        // Bar Chart elements
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis-label, .y-axis text').style('opacity', 1); // Select y-axis label and ticks text
        g.selectAll('.grid-y line').style('opacity', 0.3); // Grid lines opacity
        
        // Continue executing emphasis animations (do not return)
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps; // Current elapsed seconds

        // Bars grow
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12; // Each bar delayed by 0.12 seconds
          const animDuration = 0.6; // Single bar animation duration 0.6 seconds
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

        // Labels fade in (category + value simultaneously)
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3; // Additional delay 0.3 seconds
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
        
        // Axis labels and grid lines fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.y-axis-label, .y-axis text').style('opacity', eased);
          g.selectAll('.grid-y line').style('opacity', eased * 0.3); // Grid lines to 0.3 opacity
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis-label, .y-axis text').style('opacity', 1);
          g.selectAll('.grid-y line').style('opacity', 0.3);
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
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // Pulse between 0.95 and 1.05
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

      // Process all bars at once
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
          bar.style('opacity', 0.3) // Non-highlighted bars reduce opacity
             .attr('stroke', 'none')
             .style('filter', 'none');
        }
      });
      
      // Also dim labels for non-highlighted bars
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });
      g.selectAll<SVGTextElement, any>('.category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });
    }

    // 3. Restore normal state (only when no emphasis is active AND entrance animation is complete)
    // CRITICAL: Ensure all elements are restored, avoid missing elements
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      // Bar Chart elements
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        // Revert to original fill and filter logic
        bar.attr('fill', d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
           .attr('stroke', 'none')
           .style('filter', d[yField] === maxValue ? 'url(#shadow)' : 'none')
           .style('opacity', 1);
      });
      g.selectAll('.value-label, .category-label').style('opacity', 1);
      g.selectAll('.y-axis-label, .y-axis text').style('opacity', 1);
      g.selectAll('.grid-y line').style('opacity', 0.3);
    }

  }, [frame, fps, scales, data, xField, yField, maxValue, sceneStartOffset, barColor, highlightColor]); 
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px' // Overall padding for the scene
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned 30px from top, leaving space for subtitle overlay
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Bright text color for visibility on dark background
        textAlign: 'center',
        width: '100%', // Ensure title text can span full width for centering
      }}>
        各航空公司平均出发延误时间
      </div>
      
      {/* Chart SVG container */}
      <svg 
        ref={svgRef} 
        width={960} // Template width
        height={550} // Template height
        style={{ 
          marginTop: '20px', // Push chart down slightly from the title
          shapeRendering: 'geometricPrecision', // CRITICAL: For sharper SVG rendering
          textRendering: 'geometricPrecision' // CRITICAL: For sharper text rendering
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