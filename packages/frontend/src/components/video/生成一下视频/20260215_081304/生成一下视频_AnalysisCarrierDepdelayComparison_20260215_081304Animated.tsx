import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 5.0;  // Start time of the scene in the original video

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
  
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "avg_depdelay",
      "label": "平均出发延误 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  
  // Color configuration (CRITICAL: MUST use fixed background colors!)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Scene-specific colors for "延误时间" (delay time) - problem/warning theme
  const textColor = '#e8eaed';
  const barColor = '#f97316'; // Orange for general delays
  const highlightColor = '#ea580c'; // Deeper orange for the highest delay
  const gridColor = '#4a5568';
  const axisColor = '#6b7280';
  
  // Animation Configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 5.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_MQ",
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
      "time_start": 5.0,
      "duration": 3.2
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
      "description": "Highlight AA airline and its average departure delay",
      "time_start": 5.0,
      "duration": 3.2
    }
  ];

  // Subtitle Configuration
  const narrations = [
    {
      "text": "MQ航空公司 的平均出发延误时间最高，达到33.98分钟，而AA航空公司延误时间最低，为15.41分钟。",
      "time_start": 5.0,
      "time_end": 8.0
    }
  ];
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const chartWidth = 800; // Inner chart width
    const innerHeight = 400; // Inner chart height (leaving space for titles/subtitles)

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.4); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Add some buffer above max value
      .range([innerHeight, 0]);

    return { xScale, yScale, chartWidth, innerHeight };
  }, [data, xField, yField, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Define chart dimensions
    const margin = { top: 100, right: 80, bottom: 180, left: 80 }; // Adjusted margins for subtitle space
    const { xScale, yScale, chartWidth, innerHeight } = scales;
    
    const defs = svg.append('defs');
    
    // Shadow filter (using feDropShadow to avoid blurring the shape itself)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5))
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Remove y-axis line
    g.select('.y-axis').selectAll('path').attr('stroke', 'none');
    g.select('.y-axis').selectAll('line').attr('stroke', axisColor);

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Positioned further left from the ticks
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${innerHeight / 2})`)
      .text(data_binding.y_axis.label)
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
      .attr('y', innerHeight) // Start at bottom for grow animation
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with 0 height for grow animation
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? highlightColor : barColor)
      .attr('rx', 8)
      .attr('ry', 8)
      .style('filter', 'url(#shadow)')
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
      .text((d: any) => d[yField].toFixed(2)) // Format to 2 decimal places
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? highlightColor : textColor)
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
      .attr('y', innerHeight + 20) // Positioned 20px below the chart base
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation
    
    // X-axis line (optional, but can provide clear separation)
    g.append('line')
      .attr('x1', 0)
      .attr('y1', innerHeight)
      .attr('x2', chartWidth)
      .attr('y2', innerHeight)
      .attr('stroke', axisColor)
      .attr('stroke-width', 1)
      .attr('class', 'x-axis-line'); // Add class for potential animation/selection

  }, [scales, data, xField, yField, maxValue, maxItem, barColor, highlightColor, textColor, gridColor, axisColor]);
  
  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { yScale, innerHeight } = scales;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    let entranceAnimEnded = false;

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
            .attr('y', yScale(d[yField]))
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label, .y-axis-label').style('opacity', 1);
        entranceAnimEnded = true; // Mark as ended to allow emphasis
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

        // Bars grow animation
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;  // Fixed delay 0.12 seconds
          const animDuration = 0.6;  // Fixed duration 0.6 seconds
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
              .attr('y', yScale(d[yField]))
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
            label.style('opacity', d3.easeCubicOut(labelProgress));
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });

        // Y-axis label fade in
        const axisStart = 0.3; // Delay for axis labels
        const axisDuration = 0.4; // Duration for axis labels fade in
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.y-axis-label').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - Highlight specific data
    let hasActiveEmphasis = false;
    
    // Collect all currently active emphasis animations
    const activeEmphasisAnims = animations.filter((anim: any) => {
      if (anim.type !== 'emphasis') return false;
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
        // Pulse effect: oscillates between 1 and 1.05
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
            .attr('stroke', '#ff6b6b') // Red border for highlight
            .attr('stroke-width', 4 * maxPulse) // Pulsing border width
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3) // Dim non-highlighted bars
             .attr('stroke', 'none')
             .style('filter', 'url(#shadow)'); // Restore original shadow
        }
      });

      // Apply emphasis styles to value labels
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1)
               .attr('fill', '#ff6b6b'); // Highlight label color
        } else {
          label.style('opacity', 0.3)
               .attr('fill', textColor); // Restore original label color
        }
      });
      
      // Apply emphasis styles to category labels (X-axis labels)
      g.selectAll<SVGTextElement, any>('.category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1)
               .attr('fill', '#ff6b6b'); // Highlight label color
        } else {
          label.style('opacity', 0.3)
               .attr('fill', textColor); // Restore original label color
        }
      });

    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation has completed)
    if (!hasActiveEmphasis && entranceAnimEnded) {
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        d3.select(this)
          .attr('stroke', 'none')
          .style('opacity', 1)
          .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? highlightColor : barColor)
          .style('filter', 'url(#shadow)'); // Restore original shadow
      });
      g.selectAll<SVGTextElement, any>('.value-label').style('opacity', 1).attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? highlightColor : textColor);
      g.selectAll<SVGTextElement, any>('.category-label').style('opacity', 1).attr('fill', textColor);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, barColor, highlightColor, textColor, maxItem]);

  // Subtitle logic
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
      justifyContent: 'flex-start', // Align to start to manage top space
      padding: '0 40px' // Horizontal padding
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top edge
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均出发延误时间对比
      </div>
      
      {/* Chart container */}
      <svg 
        ref={svgRef} 
        width={1280} // Full canvas width
        height={720} // Full canvas height
        style={{ 
          marginTop: '0px', // Handled by g transform
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
          {getCurrentNarration().text}
        </div>
      )}
    </AbsoluteFill>
  );
};