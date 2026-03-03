import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

// Animation Configuration:
const animations = [
  {
    "id": "entrance_analysis_carrier_depdelay_comparison",
    "type": "entrance",
    "effect": "grow_bars",
    "trigger_narration": 0,
    "description": "Chart entrance animation",
    "time_start": 7.162,
    "duration": 11.201
  },
  {
    "id": "emphasis_mq_carrier",
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
    "description": "Highlight MQ airline",
    "time_start": 11.161999999999999,
    "duration": 7.001000000000001,
    "_debug_info": {
      "word_aligned": true,
      "keyword": "MQ",
      "word_time": 11.161999999999999
    }
  },
  {
    "id": "emphasis_mq_depdelay_value",
    "type": "emphasis",
    "effect": "pulse",
    "trigger_narration": 0,
    "target_data": {
      "data_filter": {
        "carrier": "MQ",
        "avg_depdelay": 33.98
      }
    },
    "style": {
      "intensity": 0.1
    },
    "description": "Highlight MQ's average departure delay value of 33.98 minutes",
    "time_start": 7.162, // This duration is too long for value emphasis. Assuming it's meant to overlap with carrier emphasis.
    "duration": 11.201
  },
  {
    "id": "emphasis_aa_carrier",
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
    "description": "Highlight AA airline",
    "time_start": 15.562000000000001,
    "duration": 2.600999999999999,
    "_debug_info": {
      "word_aligned": true,
      "keyword": "AA",
      "word_time": 15.562000000000001
    }
  }
];

// Subtitle Configuration:
const narrations = [
  {
    "text": "首先，我们分析各航空公司的起飞延误。MQ航空平均延误高达33.98分钟，而AA航空表现相对出色。",
    "time_start": 7.162,
    "time_end": 18.163,
    "audio_file": "20260217_143314_analysis_carrier_depdelay_comparison_narr0.wav"
  }
];

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Add Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 7.162;  // Start time of the scene in the original video

  // Hardcoded data for the scene
  const data = [
    {"carrier": "AA", "avg_depdelay": 15.41, "count": 1880},
    {"carrier": "EV", "avg_depdelay": 16.53, "count": 144},
    {"carrier": "MQ", "avg_depdelay": 33.98, "count": 56},
    {"carrier": "OO", "avg_depdelay": 25.3, "count": 319},
    {"carrier": "UA", "avg_depdelay": 25.24, "count": 1358}
  ];
  
  // Data binding fields
  const xField = "carrier";
  const yField = "avg_depdelay";
  const xLabel = "航空公司";
  const yLabel = "平均延误时间 (分钟)";

  // CRITICAL: Background colors are ALREADY determined by JSON config. DO NOT CHANGE!
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; // This is also #0f1419, consistent.
  
  // Other colors chosen based on scene semantics (Delays -> Orange/Red scheme)
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f97316'; // Primary orange for bars, signifies "problem" (delay)
  const highlightColor = '#ea580c'; // Deeper orange for the highest bar/highlight
  const gridColor = '#374151'; // Subtle gray for grid lines
  const axisColor = '#555555'; // Slightly darker gray for axis lines
  
  // Calculate max value for Y-axis domain and to identify the highest bar
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;

  // SVG dimensions (canvas size)
  const svgWidth = 1280;
  const svgHeight = 720;

  // Chart area dimensions within the SVG
  const chartWidth = 960; // Represents the width available for the bars/plot area
  const chartHeight = 340; // Represents the height available for the bars/plot area

  // Translation for the main chart group (g element) to position it within the SVG
  // g_translateX centers the chart horizontally: (1280 - 960) / 2 = 160
  const g_translateX = (svgWidth - chartWidth) / 2; 
  // g_translateY provides space from the top for the title and a small gap.
  // Title is at top 30px, approx 40px height. So title ends at ~70px.
  // g_translateY = 120 means chart content starts 50px below title.
  const g_translateY = 120; 

  // D3 Scales memoization
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Padding between bars

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% buffer above max value
      .range([chartHeight, 0]); // Range is [max_height, 0] because SVG y-coords are top-down
      
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField]);
  
  // D3 rendering logic in useEffect (static initial render + initial state for animations)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders

    // Define SVG filters and gradients
    const defs = svg.append('defs');
    
    // Linear gradient for the highlighted bar (from highlightColor to barColor)
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    // Drop shadow filter for visual depth (uses feDropShadow to avoid blurring the shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group, translated to its position within the SVG canvas
    const g = svg.append('g').attr('transform', `translate(${g_translateX}, ${g_translateY})`);
    const {xScale, yScale} = scales;

    // Y-axis grid lines (behind the bars)
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across the chart width
        .tickFormat(() => "") // No labels for grid lines
        .ticks(5) // Approximately 5 grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2'); // Dashed lines for subtlety
    // Initial state for animation: hidden
    g.select('.grid-y').style('opacity', 0);
    
    // Y-axis (ticks and labels)
    const yAxisGroup = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5));
      
    // Style Y-axis tick labels
    yAxisGroup.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Style Y-axis line and ticks
    yAxisGroup.selectAll('path, line').attr('stroke', axisColor);
    // Initial state for animation: hidden
    g.select('.y-axis').style('opacity', 0);

    // Y-axis label (rotated)
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -g_translateX + 40) // Positioned relative to g's origin, adjusted to be left of Y-axis
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      // Rotation transform must match the x,y coordinates
      .attr('transform', `rotate(-90, ${-g_translateX + 40}, ${chartHeight / 2})`)
      .text(yLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    // Initial state for animation: hidden
    g.select('.y-axis-label').style('opacity', 0);

    // Draw bars for each data point
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      // Initial state for animation: height 0, y at bottom
      .attr('y', chartHeight) 
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Initial state for animation
      // Highlight the bar with the maximum value using the gradient
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners
      .style('filter', 'url(#shadow)') // Apply shadow filter
      .style('opacity', 0); // Initial state for animation
    
    // Value labels on top of each bar
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position slightly above the bar (final position)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) // Format to 2 decimal places
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? 'bold' : 'normal')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation
    
    // Category labels (X-axis tick labels) below the bars
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 35) // Positioned 35px below the chart baseline (chartHeight)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? 'bold' : 'normal') // Highlight category too
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    // X-axis label (overall label for the categories)
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 70) // Positioned 70px below the chart baseline (below category labels)
      .attr('text-anchor', 'middle')
      .text(xLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

  }, [scales, maxValue, chartWidth, chartHeight, g_translateX, g_translateY, barColor, highlightColor, textColor, gridColor, axisColor, xField, yField, xLabel, yLabel]);
  
  // Second useEffect: ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale} = scales;
    const innerHeight = chartHeight; // Use chartHeight as the inner height for bar calculations

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance' && a.effect === 'grow_bars');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // ✅ CRITICAL: 动画结束后，强制所有元素到最终状态
      if (frame >= animEnd) {
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1)
            .attr('stroke', 'none') // Ensure no leftover stroke from emphasis
            .style('filter', 'url(#shadow)');
        });
        g.selectAll('.value-label, .category-label, .x-axis-label, .y-axis-label, .y-axis, .grid-y').style('opacity', 1);
        
        // Continue executing emphasis animations (don't return)
      } else if (frame >= animStart) {
        // 入场动画进行中
        const totalTime = (frame - animStart) / fps;  // 当前经过的秒数

        // 柱子逐个生长
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;  // 每个柱子延迟 0.12 秒（固定值）
          const animDuration = 0.6;   // 单个柱子动画时长 0.6 秒
          const barStart = i * delayPerBar;
          const barEnd = barStart + animDuration;

          if (totalTime >= barStart && totalTime <= barEnd) {
            // 柱子动画进行中
            const barProgress = (totalTime - barStart) / animDuration;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight))
              .style('opacity', eased)
              .attr('stroke', 'none')
              .style('filter', 'url(#shadow)');
          } else if (totalTime > barEnd) {
            // 柱子动画完成
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1)
              .attr('stroke', 'none')
              .style('filter', 'url(#shadow)');
          }
        });

        // 标签延迟淡入（category + value 同时）
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3;  // 额外延迟 0.3 秒（固定值）
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
        
        // 轴和轴标签淡入
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.x-axis-label, .y-axis-label, .y-axis, .grid-y').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.x-axis-label, .y-axis-label, .y-axis, .grid-y').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - 高亮特定数据
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;
    
    // 先收集所有当前激活的 emphasis 动画
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      // 计算所有激活动画的平均 pulse（用于同步效果）
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1; // Pulse between 0.95 and 1.05
        maxPulse = Math.max(maxPulse, pulse);
      });

      // 收集所有需要高亮的数据项（使用 Set 避免重复）
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

      // 一次性处理所有柱子和相关标签
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
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'url(#shadow)'); // Non-highlighted bars
        }
      });
      
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        if (isHighlighted) {
          label.style('opacity', 1)
               .attr('fill', highlightColor) // Keep original highlight color for value if it was max
               .style('font-weight', 'bold')
               .style('filter', 'drop-shadow(0 0 5px rgba(255, 107, 107, 0.5))');
        } else {
          label.style('opacity', 0.3)
               .attr('fill', textColor) // Restore original text color for non-highlighted
               .style('font-weight', 'normal')
               .style('filter', 'none');
        }
      });

      // Also dim the axes and grid lines if there's an active emphasis
      g.selectAll('.x-axis-label, .y-axis-label, .y-axis, .grid-y').style('opacity', 0.3);

    }

    // 3. 恢复正常状态（仅在没有 emphasis 且入场动画已完成时）
    const entranceAnimEndFrame = entranceAnim ? (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps : -1;
    
    if (!hasActiveEmphasis && frame >= entranceAnimEndFrame) {
      g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1).style('filter', 'url(#shadow)');
      g.selectAll('.value-label').style('opacity', 1).attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor).style('font-weight', (d: any) => d[yField] === maxValue ? 'bold' : 'normal').style('filter', 'none');
      g.selectAll('.category-label').style('opacity', 1).attr('fill', textColor).style('font-weight', (d: any) => d[yField] === maxValue ? 'bold' : 'normal').style('filter', 'none');
      g.selectAll('.x-axis-label, .y-axis-label, .y-axis, .grid-y').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, chartHeight, barColor, highlightColor, textColor]);
  
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };

  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // Uses the unified background color
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align content to the top
    }}>
      {/* Scene Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned 30px from the top of the canvas
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Light text for title
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均起飞延误时间
      </div>
      
      {/* D3 Chart SVG Container */}
      <svg 
        ref={svgRef} 
        width={svgWidth} // Full canvas width
        height={svgHeight} // Full canvas height
        style={{ 
          // SVG element itself takes full canvas, its content is translated by the 'g' element
          shapeRendering: 'geometricPrecision', // Ensures sharp lines and shapes
          textRendering: 'geometricPrecision' // Ensures sharp text rendering
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