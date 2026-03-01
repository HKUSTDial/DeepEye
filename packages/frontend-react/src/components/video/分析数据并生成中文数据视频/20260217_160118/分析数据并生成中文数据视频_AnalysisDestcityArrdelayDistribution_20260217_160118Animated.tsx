import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 23.988;  // Start time of the scene in the original video

  // Animation Configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 23.988,
      "duration": 5.350000000000002
    },
    {
      "id": "emphasis_los_angeles",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "destcity": "Los Angeles"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Los Angeles when mentioned",
      "time_start": 23.988,
      "duration": 5.350000000000002
    },
    {
      "id": "emphasis_delay_5_13",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "avg_arrdelay": 5.13
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight the average delay of 5.13 minutes when mentioned",
      "time_start": 23.988,
      "duration": 5.350000000000002
    }
  ];

  // Subtitle Configuration
  const narrations = [
    {
      "text": "而洛杉矶则非常准时，平均延误仅5.13分钟。",
      "time_start": 23.988,
      "time_end": 29.138,
      "audio_file": "20260217_160118_analysis_destcity_arrdelay_distribution_narr0.wav"
    }
  ];

  // Hardcoded data
  const data = [
  {
    "destcity": "Minneapolis",
    "avg_arrdelay": 19.58,
    "count": 439
  },
  {
    "destcity": "Dallas",
    "avg_arrdelay": 15.78,
    "count": 608
  },
  {
    "destcity": "New York",
    "avg_arrdelay": 15.04,
    "count": 769
  },
  {
    "destcity": "Washington",
    "avg_arrdelay": 13.95,
    "count": 583
  },
  {
    "destcity": "San Francisco",
    "avg_arrdelay": 13.05,
    "count": 459
  },
  {
    "destcity": "Boston",
    "avg_arrdelay": 12.52,
    "count": 385
  },
  {
    "destcity": "Los Angeles",
    "avg_arrdelay": 5.13,
    "count": 514
  }
];
  
  // Data binding from prompt
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

  const xField = data_binding.x_axis?.field || 'destcity';
  const yField = data_binding.y_axis?.field || 'avg_arrdelay';
  
  // Sort data by avg_arrdelay in ascending order to highlight Los Angeles at one end
  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => (a as any)[yField] - (b as any)[yField]);
  }, [data, yField]);

  // Color configuration (CRITICAL: Background colors are fixed!)
  const backgroundColor = '#0f1419';
  
  // Scene-specific colors based on "delays" (negative) but highlighting a "punctual" (positive) outlier
  const textColor = '#e8eaed'; 
  const barColor = '#ef4444'; // Red for general delays
  const highlightColor = '#22c55e'; // Green for the lowest delay (Los Angeles)
  const gridColor = '#444444'; 
  const axisColor = '#777777'; 
  
  // Calculate metrics
  const maxValue = d3.max(sortedData, (d: any) => d[yField]) || 0;
  const lowestDelayCity = sortedData[0][xField]; // Los Angeles after sorting
  
  const scales = useMemo(() => {
    const chartWidth = 960;
    const chartHeight = 320; // Max height for the chart drawing area, reserving 180px for subtitles
    const marginLeft = 80;
    const marginRight = 80;

    const xScale = d3.scaleBand()
      .domain(sortedData.map((d: any) => d[xField]))
      .range([0, chartWidth - marginLeft - marginRight])
      .padding(0.2);
      
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Add some padding above max value
      .range([chartHeight, 0]);
      
    return { xScale, yScale, chartWidth, chartHeight, marginLeft, marginRight };
  }, [sortedData, xField, yField, maxValue]);
  
  // First useEffect for static rendering and initial state for animations
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Define SVG dimensions and margins
    const { xScale, yScale, chartWidth, chartHeight, marginLeft, marginRight } = scales;

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Shadow filter
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Chart group, positioned to allow for title and bottom subtitle space
    const g = svg.append('g').attr('transform', `translate(${marginLeft + 40}, 100)`);
    g.attr('class', 'chart-group'); // Add class for easier selection in animations

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-(xScale.range()[1]))
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .style('opacity', 0); // Initially hidden for animation

    // Y-axis
    const yAxisG = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `${d} min`));
      
    yAxisG.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('opacity', 0); // Initially hidden for animation

    yAxisG.selectAll('line, path').attr('stroke', axisColor).style('opacity', 0); // Initially hidden for animation

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label') // Added class for animation
      .attr('x', -70)
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`) 
      .text(data_binding.y_axis.label)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden for animation
    
    // Draw bars (highlight lowest delay city with accent color)
    g.selectAll('.bar')
      .data(sortedData)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', chartHeight) // Initial y for animation: bottom of chart
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial height for animation: 0
      .attr('fill', (d: any) => d[xField] === lowestDelayCity ? highlightColor : barColor)
      .attr('rx', 6) // Rounded corners for aesthetics
      .style('opacity', 0); // Initially hidden for animation
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(sortedData)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Final Y position
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) // Format to 2 decimal places
      .attr('fill', (d: any) => d[xField] === lowestDelayCity ? highlightColor : textColor)
      .style('font-size', '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden for animation
    
    // Category labels below chart
    g.selectAll('.category-label')
      .data(sortedData)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 30) // Final Y position
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden for animation

  }, [scales, sortedData, xField, yField, lowestDelayCity, highlightColor, barColor, textColor, gridColor, axisColor]);
  
  // Second useEffect for ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('.chart-group'); // Select the chart group
    if (g.empty()) return;

    const { yScale, chartHeight } = scales;
    const innerHeight = chartHeight; // Use chartHeight as the inner height for bar calculations

    // 1. ENTRANCE ANIMATION - Check if it's defined and active
    const entranceAnimConfig = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnimConfig) {
      const animStart = (entranceAnimConfig.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnimConfig.duration * fps;
      
      // CRITICAL: After animation ends, force all elements to final state
      if (frame >= animEnd) {
        // Bar Chart elements
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1)
            .attr('fill', (d: any) => d[xField] === lowestDelayCity ? highlightColor : barColor) // Restore original color
            .attr('stroke', 'none') // Ensure no emphasis stroke remains
            .style('filter', (d: any) => d[xField] === lowestDelayCity ? 'url(#shadow)' : 'none'); // Restore original shadow
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis-label, .y-axis text, .y-axis line, .y-axis path, .grid-y line').style('opacity', 1);
        
        // No return here, continue to check for emphasis animations
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

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

        // Labels (category + value) fade in
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
        
        // Axis labels and grid lines fade in
        const axisStart = 0.3; // Axis labels start delay
        const axisDuration = 0.4; // Axis labels fade-in duration
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.y-axis-label, .y-axis text, .y-axis line, .y-axis path, .grid-y line').style('opacity', eased);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis-label, .y-axis text, .y-axis line, .y-axis path, .grid-y line').style('opacity', 1);
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
      
      // Calculate average pulse for synchronous effect
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Pulse effect: sin wave for a gentle beat, range 1.0 to 1.1
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1.05;
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting
      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          data.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => (d as any)[key] === (filter as any)[key]
            );
            if (matches) {
              highlightedItems.add(d[xField]);  // Use xField (e.g., "destcity") as unique identifier
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
            .attr('stroke-width', 4 * maxPulse) // Pulse stroke width
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3) // Dim non-highlighted bars
             .attr('stroke', 'none')
             .style('filter', 'none');
        }
      });

      // Also dim labels for non-highlighted bars, keep highlighted labels at full opacity
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });
      
      // Dim axis labels and grid lines slightly during emphasis
      g.selectAll('.y-axis-label, .y-axis text, .y-axis line, .y-axis path, .grid-y line').style('opacity', 0.5);

    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation has finished)
    // This ensures elements revert to their non-emphasized, fully visible state.
    if (!hasActiveEmphasis && entranceAnimConfig && frame >= (entranceAnimConfig.time_start - sceneStartOffset + entranceAnimConfig.duration) * fps) {
      // Bar Chart elements
      g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          bar.attr('stroke', 'none')
             .style('opacity', 1)
             .attr('fill', (d: any) => d[xField] === lowestDelayCity ? highlightColor : barColor) // Restore original color
             .style('filter', (d: any) => d[xField] === lowestDelayCity ? 'url(#shadow)' : 'none'); // Restore original shadow
      });
      g.selectAll('.value-label, .category-label').style('opacity', 1);
      g.selectAll('.y-axis-label, .y-axis text, .y-axis line, .y-axis path, .grid-y line').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, lowestDelayCity, highlightColor, barColor, textColor, gridColor, axisColor]);

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
      justifyContent: 'flex-start', // Align to start to control top padding better
      padding: '0px 40px' // Horizontal padding
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned at top 30px, leaving space
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision',
      }}>
        目的地城市平均到达延误分布
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={1280} // Full width to position the chart group
        height={720} // Full height to control internal elements
        style={{ 
          marginTop: '20px', // Adjusted to fit title and overall layout
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />

      {/* Subtitle Display Area */}
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