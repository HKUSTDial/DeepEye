import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

// Easing functions for smooth animations
import { easeCubicOut, easeSinOut } from 'd3-ease';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
   
  // Scene time offset (for independent preview)
  const sceneStartOffset = 6.55;  // Start time of the scene in the original video

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
  
  // Data binding from prompt
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
  
  // Color configuration
  const backgroundColor = '#0f1419';
  
  // Other colors: Chosen based on scene semantics ("delays" -> red/orange scheme)
  const textColor = '#e8eaed'; // Light grey for dark background for readability
  const barColor = '#f97316'; // Orange for the 'delays' theme (Tailwind orange-500)
  const highlightColor = '#ea580c'; // Deeper orange for emphasis (Tailwind orange-600)
  const gridColor = '#555555'; // Subtle grey for grid lines
  const axisColor = '#888888'; // Subtle grey for axis labels and lines

  // Animation configuration from prompt
  const animations = [
    {
      "id": "entrance_analysis_carrier_depdelay_comparison",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation for different carrier average departure delay comparison.",
      "time_start": 6.55,
      "duration": 5.125
    },
    {
      "id": "emphasis_mq_depdelay",
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
      "description": "Highlight MQ airline due to longest average departure delay.",
      "time_start": 11.525,
      "duration": 8.674999999999999,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "MQ",
        "word_time": 11.525
      }
    },
    {
      "id": "emphasis_aa_depdelay",
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
      "description": "Highlight AA airline due to shortest average departure delay.",
      "time_start": 16.55,
      "duration": 3.6499999999999986,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "AA",
        "word_time": 16.55
      }
    }
  ];

  // Subtitle configuration from prompt
  const narrations = [
    {
      "text": "首先，我们来看看不同航空公司的起飞延误表现。",
      "time_start": 6.55,
      "time_end": 11.475,
      "audio_file": "20260217_135016_analysis_carrier_depdelay_comparison_narr0.wav"
    },
    {
      "text": "MQ航空公司平均延误最长达33.98分钟，而AA则最短，仅15.41分钟。",
      "time_start": 11.475,
      "time_end": 20.2,
      "audio_file": "20260217_135016_analysis_carrier_depdelay_comparison_narr1.wav"
    }
  ];
  
  // Helper to get current narration
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // D3 scales
  const scales = useMemo(() => {
    // Chart dimensions within the SVG
    // SVG width is 1200 (1280 - 40*2 padding from AbsoluteFill)
    // SVG height is 600 (720 - 60*2 padding from AbsoluteFill)
    const margin = {top: 40, right: 80, bottom: 180, left: 80}; // Bottom for subtitle, top for title buffer
    const innerWidth = (1280 - 40 * 2) - margin.left - margin.right; // 1200 - 80 - 80 = 1040
    const innerHeight = (720 - 60 * 2) - margin.top - margin.bottom; // 600 - 40 - 180 = 380
    
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerWidth])
      .padding(0.2);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% padding for top
      .range([innerHeight, 0]); // Invert range for SVG coordinates

    return { xScale, yScale, innerWidth, innerHeight, margin };
  }, [data, xField, yField, maxValue]);
  
  // useEffect 1: Static rendering (with initial animation states)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create linear gradient for the highlighted bar (from lighter to darker orange)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', barColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    // Shadow filter (using feDropShadow to avoid blurring the actual shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Chart group with margins
    const {xScale, yScale, innerWidth, innerHeight, margin} = scales;
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth) // Extend grid lines across the chart
        .tickFormat(() => "") // No labels for grid lines
        .ticks(5) // Approximately 5 grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-opacity', 0); // Initially hidden for animation

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis') // Add class for selection
      .call(d3.axisLeft(yScale).ticks(5))
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden for animation
    
    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label') // Add class for selection
      .attr('x', -margin.left + 15) // Position to the left of tick labels
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 15}, ${innerHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden for animation

    // Draw bars - initial state for animation
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar') // Add class for selection
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', innerHeight) // Start at the bottom for growth animation
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with zero height
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for a softer look
      .style('filter', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#shadow)' : 'none')
      .style('opacity', 0); // Initially hidden for animation
    
    // Value labels on top of bars - initial state for animation
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label') // Add class for selection
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Will animate to this position
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2) + ' min') // Format as "XX.XX min"
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden for animation
    
    // Category labels below chart - initial state for animation
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label') // Add class for selection
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', innerHeight + 30) // Position below the bars
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[xField] === maxItem?.[xField] ? 'bold' : 'normal') // Bold the max item label
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initially hidden for animation

  }, [scales, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, maxItem]); 
  
  // useEffect 2: ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale, innerHeight} = scales;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStartFrame = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEndFrame = animStartFrame + entranceAnim.duration * fps;
      
      // ✅ CRITICAL: 动画结束后，强制所有元素到最终状态
      if (frame >= animEndFrame) {
        // Bar Chart elements
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', yScale(d[yField]))
            .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#accentGradient)' : barColor) // Restore original fill
            .style('filter', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#shadow)' : 'none') // Restore original filter
            .attr('stroke', 'none') // Ensure no emphasis stroke
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.y-axis text, .y-axis-label').style('opacity', 1); // Restore axis labels
        g.selectAll('.grid-y line').attr('stroke-opacity', 0.3); // Restore grid lines
        
        // Continue executing emphasis animations (don't return)
      } else if (frame >= animStartFrame) {
        // 入场动画进行中
        const totalTime = (frame - animStartFrame) / fps;  // 当前经过的秒数

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
            const eased = easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            // 柱子动画完成
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', yScale(d[yField])) // Correct final Y position
              .style('opacity', 1);
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
            const eased = easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });
        
        // 轴标签和网格线淡入
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = easeCubicOut(axisProgress); // Corrected typo easeCCubicOut -> easeCubicOut
          g.selectAll('.y-axis text, .y-axis-label').style('opacity', eased);
          g.selectAll('.grid-y line').attr('stroke-opacity', eased * 0.3); // Fade in to 0.3
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.y-axis text, .y-axis-label').style('opacity', 1);
          g.selectAll('.grid-y line').attr('stroke-opacity', 0.3);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - 高亮特定数据
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
      
      // Calculate max pulse for all active animations (using progress relative to each anim's start)
      let maxPulseScale = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStartFrame = (anim.time_start - sceneStartOffset) * fps;
        const animDurationFrames = anim.duration * fps;
        const progress = (frame - animStartFrame) / animDurationFrames;
        const pulse = easeSinOut(progress * Math.PI * 6) * 0.05 + 1; // 6 pulses per duration, range 1.0 to 1.05
        maxPulseScale = Math.max(maxPulseScale, pulse);
      });

      // Collect all data items that need highlighting
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

      // Process all bars at once
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red border for highlight
            .attr('stroke-width', 4 * maxPulseScale) // Pulsing stroke width
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))') // Glow effect
            .attr('fill', barColor); // Use solid barColor for highlighted, not gradient
        } else {
          bar
            .style('opacity', 0.3) // Reduce opacity for non-highlighted bars
            .attr('stroke', 'none')
            .style('filter', 'none')
            .attr('fill', barColor); // Ensure non-highlighted bars also use solid color
        }
      });
      
      // Also dim labels for non-highlighted items
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });

    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation is done)
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      // Restore all bars to their default (post-entrance) appearance
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        bar
          .attr('stroke', 'none')
          .style('filter', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#shadow)' : 'none') // Restore original filter
          .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#accentGradient)' : barColor) // Restore original fill
          .style('opacity', 1);
      });
      // Restore labels
      g.selectAll('.value-label, .category-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, barColor, highlightColor, maxItem]); 
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px' // Padding for the AbsoluteFill container
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned at the top, leaving space for the subtitle overlay below
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        '-webkit-font-smoothing': 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        不同航空公司平均出发延误比较
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={1280 - 40 * 2} // Total video width minus AbsoluteFill horizontal padding
        height={720 - 60 * 2} // Total video height minus AbsoluteFill vertical padding
        style={{ 
          marginTop: '20px', // Push chart down from the title for better separation
          shapeRendering: 'geometricPrecision', // SVG clarity optimization
          textRendering: 'geometricPrecision' // SVG clarity optimization
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