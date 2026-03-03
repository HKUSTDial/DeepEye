import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

// Define animation and narration configurations
const animations = [
  {
    "id": "entrance_analysis_carrier_delay_comparison",
    "type": "entrance",
    "effect": "grow_bars",
    "trigger_narration": 0,
    "description": "Chart entrance animation for average departure delay by carrier",
    "time_start": 7.513,
    "duration": 4.537
  },
  {
    "id": "emphasis_mq_carrier",
    "type": "emphasis",
    "effect": "pulse",
    "trigger_narration": 1,
    "target_data": {
      "data_filter": {
        "carrier": "MQ"
      }
    },
    "style": {
      "intensity": 0.1
    },
    "description": "Highlight MQ airline for longest delay",
    "time_start": 13.138,
    "duration": 9.15,
    "_debug_info": {
      "word_aligned": true,
      "keyword": "MQ",
      "word_time": 13.138
    }
  },
  {
    "id": "emphasis_aa_carrier",
    "type": "emphasis",
    "effect": "pulse",
    "trigger_narration": 1,
    "target_data": {
      "data_filter": {
        "carrier": "AA"
      }
    },
    "style": {
      "intensity": 0.1
    },
    "description": "Highlight AA airline for shortest delay",
    "time_start": 17.575,
    "duration": 4.713000000000001,
    "_debug_info": {
      "word_aligned": true,
      "keyword": "AA",
      "word_time": 17.575
    }
  }
];

const narrations = [
  {
    "text": "首先，我们关注各航空公司平均出发延误。",
    "time_start": 7.513,
    "time_end": 11.85,
    "audio_file": "20260217_150441_analysis_carrier_delay_comparison_narr0.wav"
  },
  {
    "text": "数据显示，MQ航空公司延误最长，达33.98分钟；AA航空公司则表现最佳，仅15.41分钟。",
    "time_start": 11.85,
    "time_end": 22.288,
    "audio_file": "20260217_150441_analysis_carrier_delay_comparison_narr1.wav"
  }
];

export const SceneComponentAnimated: React.FC = () => {
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
  
  // Data binding configuration
  const data_binding = {
    "x_axis": { "field": "carrier", "label": "航空公司" },
    "y_axis": { "field": "avg_depdelay", "label": "平均出发延误 (分钟)" }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field;
  
  // Color configuration
  const backgroundColor = '#0f1419';
  
  const textColor = '#e8eaed';
  const barColor = '#f97316';
  const highlightColor = '#facc15';
  const gridColor = '#374151';
  const axisColor = '#888888';

  // Format numbers to two decimal places
  const formatValue = d3.format(".2f");
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // Chart dimensions and margins
  const svgWidth = 1280;
  const svgHeight = 720;
  const marginTop = 100;
  const marginRight = 80;
  const marginBottom = 180;
  const marginLeft = 80;

  const chartWidth = svgWidth - marginLeft - marginRight;
  const chartHeight = svgHeight - marginTop - marginBottom;

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([chartHeight, 0]);

    return { xScale, yScale };
  }, [data, xField, yField, chartWidth, chartHeight, maxValue]);
  
  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 7.513;

  // Helper for subtitles
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime < (narr.time_end - sceneStartOffset)
    );
  };

  // 1. Initial Render / Static Setup (modifications for animation initial state)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create linear gradient for the highlighted bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    // Shadow filter
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group
    const g = svg.append('g')
      .attr('transform', `translate(${marginLeft}, ${marginTop})`);
    
    const { xScale, yScale } = scales;

    // Horizontal grid lines (initially dimmed, animation will handle fade in)
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,4')
      .style('opacity', 0); // Initially hidden for animation
    
    // Y-axis label (initially hidden, animation will handle)
    g.append('text')
      .attr('class', 'y-axis-label') // Added class for selection
      .attr('x', -marginLeft / 2 - 10)
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-marginLeft / 2 - 10}, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden

    // Y-axis tick labels (initially hidden, animation will handle)
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => formatValue(d as number)))
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden
    
    // Draw bars (initially height 0, y at bottom, opacity 0 for animation)
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', chartHeight) // Start from bottom
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with 0 height
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8)
      .attr('ry', 8)
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none')
      .style('opacity', 0); // Initially hidden
    
    // Value labels on top of bars (initially hidden)
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15)
      .attr('text-anchor', 'middle')
      .text((d: any) => formatValue(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden
    
    // Category labels below chart (initially hidden)
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 25)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden

  }, [scales, maxValue, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight, marginLeft]);


  // 2. Animation Logic
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { yScale } = scales;
    const innerHeight = chartHeight; // Use chartHeight as innerHeight for consistency

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // CRITICAL: After animation ends, force all elements to final state
      if (frame >= animEnd) {
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis-label, .y-axis text').style('opacity', 1);
        g.selectAll('.grid-y line').style('opacity', 0.3); // Restore grid opacity
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps; // Current elapsed seconds

        // Bars grow
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12; // Each bar delayed by 0.12s
          const animDuration = 0.6; // Single bar animation duration
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
            // Bar animation completed
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Value and category labels fade in
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3; // Additional delay for labels
          const animDuration = 0.4; // Label fade-in duration
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

        // Y-axis label and ticks fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.y-axis-label, .y-axis text').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis-label, .y-axis text').style('opacity', 1);
        }
        
        // Grid lines fade in
        const gridStart = 0.2;
        const gridDuration = 0.3;
        if (totalTime >= gridStart && totalTime <= gridStart + gridDuration) {
          const gridProgress = (totalTime - gridStart) / gridDuration;
          g.selectAll('.grid-y line').style('opacity', d3.easeCubicOut(gridProgress) * 0.3); // Fade to 0.3 opacity
        } else if (totalTime > gridStart + gridDuration) {
          g.selectAll('.grid-y line').style('opacity', 0.3);
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
      
      // Calculate max pulse for all active animations (for synchronized effect)
      let maxPulseScale = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Pulse effect: sin wave for oscillating stroke width, clamped to 1-1.05
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; 
        maxPulseScale = Math.max(maxPulseScale, pulse);
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

      // Process all bars at once
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red border for highlight
            .attr('stroke-width', 3 * maxPulseScale) // Pulse stroke width
            .style('filter', `drop-shadow(0 0 ${15 * maxPulseScale}px rgba(255, 107, 107, 0.8))`); // Glow effect
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none'); // Dim others
        }
      });

      // Value labels for highlighted bars
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1).attr('fill', '#ff6b6b'); // Highlight label color
        } else {
          label.style('opacity', 0.3).attr('fill', textColor);
        }
      });
      
      // Category labels for highlighted bars
      g.selectAll<SVGTextElement, any>('.category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1).attr('fill', '#ff6b6b'); // Highlight label color
        } else {
          label.style('opacity', 0.3).attr('fill', textColor);
        }
      });

    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation is done)
    const entranceFinished = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;
    if (!hasActiveEmphasis && entranceFinished) {
      g.selectAll<SVGRectElement, any>('.bar')
        .attr('stroke', 'none')
        .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none') // Restore max value shadow
        .style('opacity', 1);
      g.selectAll('.value-label, .category-label').style('opacity', 1).attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor);
      g.selectAll('.y-axis-label, .y-axis text').style('opacity', 1);
      g.selectAll('.grid-y line').style('opacity', 0.3);
    }

  }, [frame, fps, scales, xField, yField, chartHeight, sceneStartOffset, barColor, highlightColor, textColor, maxValue]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 40px'
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
      }}>
        按航空公司划分的平均出发延误
      </div>
      
      {/* Chart */}
      <svg 
        ref={svgRef} 
        width={svgWidth} 
        height={svgHeight} 
        style={{ 
          marginTop: '0px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />

      {/* Subtitle Display */}
      {getCurrentNarration() && (
        <div style={{
          position: 'absolute',
          bottom: 35,
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