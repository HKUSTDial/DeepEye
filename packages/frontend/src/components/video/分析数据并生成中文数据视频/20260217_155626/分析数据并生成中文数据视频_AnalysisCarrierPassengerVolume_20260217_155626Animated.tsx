import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  // CRITICAL: All times in the configuration (`time_start`, `time_end`) are based on absolute video time.
  // Since this component is for independent preview, you need to subtract `sceneStartOffset` from all times to start playback from frame 0.
  const sceneStartOffset = 65.1;  // Start time of the scene in the original video

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
  
  // Data Binding (from prompt)
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "sum_passengers",
      "label": "客运总量"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  
  // Animation Configuration (from prompt)
  const animations = [
    {
      "id": "entrance_analysis_carrier_passenger_volume",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation for carrier passenger volume.",
      "time_start": 65.1,
      "duration": 10.550000000000008
    },
    {
      "id": "emphasis_AA_passengers",
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
      "description": "Highlight AA carrier when mentioned.",
      "time_start": 69.5,
      "duration": 5.950000000000003,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "AA",
        "word_time": 69.5
      }
    },
    {
      "id": "emphasis_UA_passengers",
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
      "description": "Highlight UA carrier when mentioned.",
      "time_start": 72.41199999999999,
      "duration": 3.038000000000011,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "UA",
        "word_time": 72.41199999999999
      }
    },
    {
      "id": "emphasis_MQ_passengers",
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
      "description": "Highlight MQ carrier when mentioned.",
      "time_start": 73.375,
      "duration": 2.075000000000003,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "MQ",
        "word_time": 73.375
      }
    }
  ];

  // Subtitle Configuration (from prompt)
  const narrations = [
    {
      "text": "最后，让我们了解各航空公司客运量的背景。AA航空的客运总量最高，其次是UA，而MQ的客运量最低。",
      "time_start": 65.1,
      "time_end": 75.45,
      "audio_file": "20260217_155626_analysis_carrier_passenger_volume_narr0.wav"
    },
    {
      "text": "这为我们理解不同规模航空公司在延误表现上的差异提供了额外视角。",
      "time_start": 75.45,
      "time_end": 81.975,
      "audio_file": "20260217_155626_analysis_carrier_passenger_volume_narr1.wav"
    }
  ];
  
  // Color configuration - MUST use these background colors, others chosen based on scene semantics
  const backgroundColor = '#0f1419'; 
  // const containerBackground = '#0f1419'; // Not directly used in this component, but for consistency

  // Scene semantics: Neutral analysis, comparison of passenger volume.
  // Using a harmonious blue/cyan scheme with the dark background.
  const textColor = '#e8eaed'; // Off-white for readability on dark background
  const barColor = '#3b82f6'; // A vibrant blue for general bars
  const highlightColor = '#82d0fe'; // A brighter sky blue to highlight the max value
  const gridColor = '#2a3440'; // Subtle dark gray-blue for grid lines
  const axisColor = '#888888'; // Medium gray for axis labels and ticks

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  // const maxItem = data.find((d: any) => d[yField] === maxValue); // Needed for conditional styling

  // D3 dimensions
  const svgWidth = 960; // Chart-Dominant layout, 80% of 1280px is 1024, using 960 for good margins
  const svgHeight = 550; // Total SVG element height. Actual chart drawing area within this.

  // Margins for the chart group within the SVG
  const margin = { top: 40, right: 60, bottom: 0, left: 80 }; // Bottom margin handled by overall SVG height and positioning
  
  // Inner chart dimensions (where the bars will be drawn, relative to 'g' transform)
  // This value is critical for `yScale` range and bar heights.
  // It ensures bars and their value labels fit above the reserved bottom 180px for subtitles.
  const innerChartHeight = 320; // Consistent with example range([320, 0])
  const innerChartWidth = svgWidth - margin.left - margin.right; // 960 - 80 - 60 = 820

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerChartWidth])
      .padding(0.3); // Space between bars

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Y-axis starts at 0, ends slightly above max value
      .range([innerChartHeight, 0]); // Maps data values to pixel range (bottom to top)

    return { xScale, yScale };
  }, [data, xField, yField, maxValue, innerChartWidth, innerChartHeight]);
  
  // Static D3 rendering useEffect (first useEffect)
  // This useEffect sets up the D3 elements in their initial state (often hidden or zero-sized for animation).
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    // Add SVG clarity optimizations
    svg.attr('shapeRendering', 'geometricPrecision')
       .attr('textRendering', 'geometricPrecision');

    const defs = svg.append('defs');
    
    // Gradient for the highlighted bar (AA)
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColor)!.brighter(0.5).toString());
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);

    // Shadow filter for the highlighted bar
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 8) // Vertical offset for shadow
      .attr('stdDeviation', 10) // Blur radius
      .attr('flood-color', highlightColor) // Shadow color matches highlight
      .attr('flood-opacity', 0.4); // Semi-transparent shadow

    // Main chart group, translated by margins
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    const { xScale, yScale } = scales;

    // Y-axis grid lines - Start hidden
    g.append('g')
      .attr('class', 'grid-y')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0) // Initial opacity 0 for animation
      .call(d3.axisLeft(yScale)
        .tickSize(-innerChartWidth) // Extend grid lines across chart width
        .tickFormat(() => "") // No labels for grid lines
      )
      .select('.domain').remove(); // Remove the axis line itself

    // Y-axis labels (numbers) - Start hidden
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).tickSize(0).tickPadding(10).tickFormat(d3.format(".2s"))) // Format for thousands/millions/etc.
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0 for animation
    g.select('.y-axis').select('.domain').remove(); // Remove Y-axis domain line

    // Bars - Start with height 0 at the bottom, hidden
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField])!)
      .attr('y', innerChartHeight) // Initial y for animation: at the bottom
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial height for animation: 0
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for aesthetics
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none')
      .style('opacity', 0); // Initial opacity 0 for animation

    // Value labels on top of bars - Start hidden
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => xScale(d[xField])! + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Positioned slightly above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(",")(d[yField])) // Format with commas for large numbers
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0 for animation

    // Category labels (X-axis labels) - Start hidden
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => xScale(d[xField])! + xScale.bandwidth() / 2)
      .attr('y', innerChartHeight + 25) // Positioned below the bars, within safe zone for subtitles
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0 for animation

    // Y-axis label - Start hidden
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Positioned to the left of the y-axis ticks
      .attr('y', innerChartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${innerChartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity 0 for animation
    
  }, [scales, data, xField, yField, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, innerChartHeight, innerChartWidth, margin.left]);

  // Animation logic useEffect (second useEffect)
  // This useEffect handles all dynamic animation based on the current frame.
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return; // Ensure the main chart group exists

    const { yScale } = scales;

    // 1. ENTRANCE ANIMATION - "grow_bars" effect
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // CRITICAL: If entrance animation is completed, force all elements to their final state.
      // This prevents elements from disappearing or staying in an intermediate state if the frame
      // goes beyond the animation duration.
      if (frame >= animEnd) {
        // Bar Chart Elements
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerChartHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerChartHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label, .y-axis-label').style('opacity', 1);
        g.select('.grid-y').attr('opacity', 0.4); // Grid uses attr opacity, restore to 0.4
        
      } else if (frame >= animStart) {
        // Entrance animation is in progress
        const totalTime = (frame - animStart) / fps; // Current elapsed seconds since animation start

        // Bars grow from bottom up with delay
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12; // Fixed delay of 0.12 seconds per bar
          const animDuration = 0.6; // Fixed animation duration of 0.6 seconds for each bar
          const barStart = i * delayPerBar;
          const barEnd = barStart + animDuration;

          if (totalTime >= barStart && totalTime <= barEnd) {
            // Bar animation in progress
            const barProgress = (totalTime - barStart) / animDuration;
            const eased = d3.easeCubicOut(barProgress); // Smooth cubic ease out
            const targetHeight = innerChartHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight)) // Ensure height doesn't go negative
              .attr('y', innerChartHeight - Math.max(0, currentHeight))
              .style('opacity', eased); // Use style for opacity for consistency with labels
          } else if (totalTime > barEnd) {
            // Bar animation completed for this specific bar, set to final state
            const targetHeight = innerChartHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerChartHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Value and Category labels fade in with delay
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3; // Additional delay of 0.3 seconds before labels start fading
          const animDuration = 0.4; // Fade-in duration of 0.4 seconds for labels
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
        
        // Y-axis label and Grid lines fade in
        const axisStart = 0.3; // Delay for axis labels and grid
        const axisDuration = 0.4; // Duration for axis labels and grid fade-in
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.select('.y-axis-label').style('opacity', axisProgress);
          g.select('.grid-y').attr('opacity', axisProgress * 0.4); // Grid's final opacity is 0.4
        } else if (totalTime > axisStart + axisDuration) {
          g.select('.y-axis-label').style('opacity', 1);
          g.select('.grid-y').attr('opacity', 0.4);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - "pulse" effect
    // CRITICAL: Handle multiple simultaneously active emphasis animations correctly.
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;
    
    // First, collect all currently active emphasis animations
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      // Calculate a combined pulse value for synchronized effect across all highlighted items
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Pulse effect: sin wave for smooth in/out, small amplitude for subtle effect (1.0-1.05x scale)
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // 6 pulses over the duration of the animation
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting from all active emphasis animations
      const highlightedItems = new Set<string>(); // Use a Set to store unique identifiers (carrier names)
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          data.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d[xField]); // Add the carrier name (e.g., "AA", "UA") to the set
            }
          });
        }
      });

      // Process all bars at once based on the collected highlightedItems (avoiding loop overwrites)
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1) // Ensure highlighted bar is fully visible
            .attr('stroke', '#ff6b6b') // Red border for highlight
            .attr('stroke-width', 3 * maxPulse) // Pulse stroke width (3-5px)
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Glow effect
        } else {
          bar.style('opacity', 0.3) // Reduce opacity of non-highlighted bars
             .attr('stroke', 'none') // Remove stroke
             .style('filter', 'none'); // Remove any existing filter
        }
      });
      
      // Also adjust opacity for value and category labels associated with the bars
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1); // Ensure highlighted label is fully visible
        } else {
          label.style('opacity', 0.3); // Reduce opacity of non-highlighted labels
        }
      });

    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation is done)
    // This ensures elements revert to their default non-highlighted state after emphasis animations end.
    // It also ensures that if entrance animation is still running, it doesn't prematurely restore state.
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      // Bar Chart Elements
      g.selectAll('.bar')
        .attr('stroke', 'none')
        .style('opacity', 1)
        // Restore original filter for the max value bar if it had one, otherwise 'none'
        .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none'); 
      g.selectAll('.value-label, .category-label').style('opacity', 1);
      
      // General elements (axes, grid)
      g.select('.y-axis-label').style('opacity', 1);
      g.select('.grid-y').attr('opacity', 0.4); // Restore grid to its default opacity
    }

  }, [frame, fps, scales, animations, data, xField, yField, maxValue, sceneStartOffset, barColor, highlightColor]);


  // Helper function to get the current narration text based on video time.
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };

  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: Use the determined background color
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to ensure title space
      padding: '0px 40px' // Horizontal padding
    }}>
      {/* Title - positioned at the top, outside of the SVG chart area */}
      <div style={{
        position: 'absolute',
        top: 30, // Top 30px from the absolute fill top
        fontSize: '36px',
        fontWeight: '700',
        color: textColor, // Use consistent text color
        textAlign: 'center',
        width: '100%', // Ensure title spans full width
      }}>
        {/* Dynamic title using data binding labels */}
        {data_binding.x_axis.label} {data_binding.y_axis.label}对比
      </div>
      
      {/* Chart SVG container */}
      <svg 
        ref={svgRef} 
        width={svgWidth} 
        height={svgHeight} 
        style={{ 
          marginTop: '100px', // Pushes the SVG down to account for title and top buffer
          // The bottom 180px for subtitles are reserved by ensuring chart elements
          // (bars, x-axis labels) do not extend below `innerChartHeight + margin.top + X-axis_label_offset`
          // which in this case calculates to 40 (svg.top) + 320 (chartHeight) + 25 (x_label_offset) = 385px
          // from the SVG's top. The SVG itself is pushed down 100px, so absolute y=485px.
          // Canvas height is 720px. 720 - 485 = 235px remaining, which is > 180px for subtitles.
          overflow: 'visible' // Allow elements like shadows to render outside svg bounds
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