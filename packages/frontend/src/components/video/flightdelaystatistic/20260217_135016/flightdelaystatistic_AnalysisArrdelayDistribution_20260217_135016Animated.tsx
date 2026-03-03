import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 63.925;  // Start time of the scene in the original video

  // Hardcoded data
  const data = [
  {
    "delay_range": "小于 -20",
    "count": 7
  },
  {
    "delay_range": "[-20, -1]",
    "count": 15
  },
  {
    "delay_range": "[0, 19]",
    "count": 3
  },
  {
    "delay_range": "[20, 39]",
    "count": 0
  },
  {
    "delay_range": "[40, 59]",
    "count": 1
  },
  {
    "delay_range": "[60, 79]",
    "count": 1
  },
  {
    "delay_range": "[80, 99]",
    "count": 1
  },
  {
    "delay_range": "[100, 119]",
    "count": 0
  },
  {
    "delay_range": "[120, 139]",
    "count": 0
  },
  {
    "delay_range": "[140, 159]",
    "count": 0
  },
  {
    "delay_range": "[160, 179]",
    "count": 1
  },
  {
    "delay_range": "[180, 199]",
    "count": 1
  }
];
  
  // Data binding configuration
  const data_binding = {
    "x_axis": {
      "field": "delay_range",
      "label": "延误时长 (分钟)"
    },
    "y_axis": {
      "field": "count",
      "label": "航班数量"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field; // Explicitly cast for single y_axis

  // Color configuration (MUST use JSON config values for background)
  const backgroundColor = '#0f1419';
  // const containerBackground = '#0f1419'; // Not used directly in JSX background

  // Scene-specific colors based on "Arrival Delay Duration Distribution" (delays, distribution, concern)
  const textColor = '#e8eaed'; 
  const barColor = '#fca311'; // Golden-orange for delays, not overly aggressive but distinct
  const highlightColor = '#f77f00'; // More vibrant orange for highlighted elements
  const gridColor = '#3a4149'; // Subtle grid color, slightly lighter than background
  const axisColor = '#6f7e8a'; // Medium grey for axis lines and labels
  const emphasisStrokeColor = '#ff6b6b'; // Red for emphasis stroke

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions and margins
  const chartWidth = 960 - 80 * 2; // SVG width - left/right margins
  const chartHeight = 300; // Height of the actual bar drawing area (reserving bottom for subtitles)
  const margin = { top: 40, right: 80, bottom: 40, left: 80 }; // For 'g' element transform

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([chartHeight, 0]);
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField]);
  
  // Animation configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 63.925,
      "duration": 5.886999999999998
    },
    {
      "id": "emphasis_delay_less_than_neg20",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "delay_range": "小于 -20"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay less than -20 minutes (early arrival)",
      "time_start": 63.925,
      "duration": 5.886999999999998
    },
    {
      "id": "emphasis_delay_neg20_to_neg1",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "delay_range": "[-20, -1]"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay from -20 to -1 minutes (early arrival)",
      "time_start": 63.925,
      "duration": 5.886999999999998
    },
    {
      "id": "emphasis_delay_0_to_19",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "delay_range": "[0, 19]"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay from 0 to 19 minutes (on-time or slightly delayed)",
      "time_start": 63.925,
      "duration": 5.886999999999998
    },
    {
      "id": "emphasis_delay_40_to_59",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "delay_range": "[40, 59]"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay from 40 to 59 minutes (longer delay)",
      "time_start": 69.612,
      "duration": 5.900000000000003
    },
    {
      "id": "emphasis_delay_60_to_79",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "delay_range": "[60, 79]"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay from 60 to 79 minutes (longer delay)",
      "time_start": 69.612,
      "duration": 5.900000000000003
    },
    {
      "id": "emphasis_delay_80_to_99",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "delay_range": "[80, 99]"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay from 80 to 99 minutes (longer delay)",
      "time_start": 69.612,
      "duration": 5.900000000000003
    },
    {
      "id": "emphasis_delay_160_to_179",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "delay_range": "[160, 179]"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay from 160 to 179 minutes (longer delay)",
      "time_start": 69.612,
      "duration": 5.900000000000003
    },
    {
      "id": "emphasis_delay_180_to_199",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "delay_range": "[180, 199]"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight flights with delay from 180 to 199 minutes (longer delay)",
      "time_start": 69.612,
      "duration": 5.900000000000003
    }
  ];

  // Subtitle configuration
  const narrations = [
    {
      "text": "抵达延误分布与起飞类似，多数航班准点或提前抵达。",
      "time_start": 63.925,
      "time_end": 69.612,
      "audio_file": "20260217_135016_analysis_arrdelay_distribution_narr0.wav"
    },
    {
      "text": "然而，仍有少数航班遭遇较长的抵达延误，值得我们关注。",
      "time_start": 69.612,
      "time_end": 75.312,
      "audio_file": "20260217_135016_analysis_arrdelay_distribution_narr1.wav"
    }
  ];

  // Helper function to get current narration text
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  // Static D3 rendering - initial state for animations
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create gradient for highlighted bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); 
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor); 
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Draw chart with proper spacing
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    const {xScale, yScale} = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
        .ticks(5)
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-opacity', 0) // Initial opacity for animation
      .style('opacity', 0); // Ensure CSS opacity is also 0

    // Y-axis
    const yAxisGroup = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5));
      
    yAxisGroup.selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity for animation
    
    yAxisGroup.select('path') // Y-axis line
      .attr('stroke', axisColor)
      .attr('stroke-opacity', 0) // Initial opacity for animation
      .style('opacity', 0); // Ensure CSS opacity is also 0
    yAxisGroup.selectAll('line') // Y-axis ticks
      .attr('stroke', axisColor) // Using axisColor for ticks
      .attr('stroke-opacity', 0) // Initial opacity for animation
      .style('opacity', 0); // Ensure CSS opacity is also 0

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 10) // Positioned to the left of the axis line
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 10}, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity for animation

    // Draw bars (highlight max value)
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', chartHeight) // Start at bottom for animation
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with 0 height for animation
      .attr('fill', (d: any) => d[yField] === maxValue && maxItem?.delay_range === d.delay_range ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for bars
      .style('filter', 'url(#shadow)')
      .style('opacity', 0); // Start invisible for animation
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField] > 0 ? d[yField] : '') // Only show non-zero counts
      .attr('fill', (d: any) => d[yField] === maxValue && maxItem?.delay_range === d.delay_range ? highlightColor : textColor)
      .style('font-size', '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible for animation
    
    // X-axis (invisible line, just for ticks and labels)
    const xAxisGroup = g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`)
      .call(d3.axisBottom(xScale).tickSizeOuter(0)); // Hide outer ticks
      
    // X-axis tick labels
    xAxisGroup.selectAll('text')
      .attr('fill', axisColor)
      .attr('y', 15) // Adjust position below the axis line
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible for animation

    // X-axis line/path
    xAxisGroup.selectAll('path')
      .attr('stroke', axisColor)
      .attr('stroke-opacity', 0) // Initial opacity for animation
      .style('opacity', 0); // Ensure CSS opacity is also 0
    xAxisGroup.selectAll('line') // X-axis ticks
      .attr('stroke', gridColor)
      .attr('stroke-opacity', 0) // Initial opacity for animation
      .style('opacity', 0); // Ensure CSS opacity is also 0

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 45) // Position below x-axis ticks
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible for animation

  }, [scales, maxValue, maxItem, chartWidth, chartHeight, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, data_binding]);

  // Animation updates
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale} = scales;
    const innerHeight = chartHeight; // Use chartHeight as the inner height for bars

    // Animation timing constants (in seconds)
    const BAR_DELAY_PER_ITEM = 0.12;
    const BAR_ANIM_DURATION = 0.6;
    const LABEL_ADDITIONAL_DELAY = 0.3;
    const LABEL_ANIM_DURATION = 0.4;
    const AXIS_FADE_IN_DELAY = 0.3;
    const AXIS_FADE_IN_DURATION = 0.4;
    const GRID_FADE_IN_DELAY = 0.3;
    const GRID_FADE_IN_DURATION = 0.4;

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
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        g.selectAll('.grid-y line').attr('stroke-opacity', 0.7).style('opacity', 1); // Grid lines
        g.selectAll('.x-axis path, .y-axis path').attr('stroke-opacity', 1).style('opacity', 1); // Axis lines
        g.selectAll('.x-axis line, .y-axis line').attr('stroke-opacity', 0.3).style('opacity', 1); // Axis ticks
        g.selectAll('.x-axis text, .y-axis text').style('opacity', 1); // Axis tick labels
        
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

        // Bars grow animation
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const barStart = i * BAR_DELAY_PER_ITEM;
          const barEnd = barStart + BAR_ANIM_DURATION;

          if (totalTime >= barStart && totalTime <= barEnd) {
            const barProgress = (totalTime - barStart) / BAR_ANIM_DURATION;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Labels fade in (value labels)
        g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const labelStart = i * BAR_DELAY_PER_ITEM + LABEL_ADDITIONAL_DELAY;
          const labelEnd = labelStart + LABEL_ANIM_DURATION;

          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / LABEL_ANIM_DURATION;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });
        
        // Axis labels fade in
        const axisAnimStart = AXIS_FADE_IN_DELAY;
        const axisAnimDuration = AXIS_FADE_IN_DURATION;
        if (totalTime >= axisAnimStart && totalTime <= axisAnimStart + axisAnimDuration) {
          const axisProgress = (totalTime - axisAnimStart) / axisAnimDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', eased);
          g.selectAll('.x-axis text, .y-axis text').style('opacity', eased); // Tick labels
          g.selectAll('.x-axis path, .y-axis path').attr('stroke-opacity', eased).style('opacity', eased); // Axis lines
          g.selectAll('.x-axis line, .y-axis line').attr('stroke-opacity', eased * 0.3).style('opacity', eased); // Axis ticks
        } else if (totalTime > axisAnimStart + axisAnimDuration) {
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
          g.selectAll('.x-axis text, .y-axis text').style('opacity', 1);
          g.selectAll('.x-axis path, .y-axis path').attr('stroke-opacity', 1).style('opacity', 1);
          g.selectAll('.x-axis line, .y-axis line').attr('stroke-opacity', 0.3).style('opacity', 1);
        }

        // Grid lines fade in
        const gridAnimStart = GRID_FADE_IN_DELAY;
        const gridAnimDuration = GRID_FADE_IN_DURATION;
        if (totalTime >= gridAnimStart && totalTime <= gridAnimStart + gridAnimDuration) {
          const gridProgress = (totalTime - gridAnimStart) / gridAnimDuration;
          const eased = d3.easeCubicOut(gridProgress);
          g.selectAll('.grid-y line').attr('stroke-opacity', eased * 0.7).style('opacity', eased); // Grid lines
        } else if (totalTime > gridAnimStart + gridAnimDuration) {
          g.selectAll('.grid-y line').attr('stroke-opacity', 0.7).style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION
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
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // Pulse effect 1.0 - 1.05
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items to be highlighted
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

      // Process all bars at once
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', emphasisStrokeColor)
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', `drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))`);
        } else {
          bar.style('opacity', 0.3)
             .attr('stroke', 'none')
             .attr('stroke-width', 0)
             .style('filter', 'url(#shadow)'); // Revert to original shadow
        }
      });

      // Also adjust value labels
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1).attr('fill', emphasisStrokeColor);
        } else {
          label.style('opacity', 0.3).attr('fill', textColor);
        }
      });
      
    }

    // 3. Restore to normal state (only if no emphasis is active AND entrance is complete)
    const entranceFinished = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;
    if (!hasActiveEmphasis && entranceFinished) {
      g.selectAll('.bar').attr('stroke', 'none')
                         .attr('stroke-width', 0)
                         .style('opacity', 1)
                         .style('filter', 'url(#shadow)'); // Restore original shadow
      g.selectAll('.value-label').style('opacity', 1).attr('fill', (d: any) => d[yField] === maxValue && maxItem?.delay_range === d.delay_range ? highlightColor : textColor); // Restore original color
      
      // Ensure other elements are at their final state after entrance
      g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
      g.selectAll('.x-axis text, .y-axis text').style('opacity', 1);
      g.selectAll('.x-axis path, .y-axis path').attr('stroke-opacity', 1).style('opacity', 1);
      g.selectAll('.x-axis line, .y-axis line').attr('stroke-opacity', 0.3).style('opacity', 1);
      g.selectAll('.grid-y line').attr('stroke-opacity', 0.7).style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, barColor, highlightColor, textColor, gridColor, axisColor, maxValue, maxItem, emphasisStrokeColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to control space
      padding: '60px 40px' // Overall padding
    }}>
      {/* Title - Positioned at the top, reserving space for potential subtitles */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top of AbsoluteFill
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        到达延误时长分布
      </div>
      
      {/* Chart - Centered horizontally, positioned vertically to leave space */}
      <svg 
        ref={svgRef} 
        width={960} // Total SVG width (1280 - 2*160 for side margins in AbsoluteFill)
        height={550} // Total SVG height (720 - 60 top padding - 110 bottom for subtitle)
        style={{ 
          marginTop: '80px', // Pushes chart down from top, leaving space for title/subtitle
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision',
          overflow: 'visible' // Ensure shadows/labels are not clipped
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