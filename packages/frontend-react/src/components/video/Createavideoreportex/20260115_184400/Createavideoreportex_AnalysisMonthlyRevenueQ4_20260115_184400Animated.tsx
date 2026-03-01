import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 21.528;  // Start time of the scene in the original video
  
  const data = [
    {
      "sale_date": "2025-01",
      "sum_total_amount": 555366.0
    },
    {
      "sale_date": "2025-02",
      "sum_total_amount": 576366.0
    },
    {
      "sale_date": "2025-03",
      "sum_total_amount": 663054.0
    },
    {
      "sale_date": "2025-04",
      "sum_total_amount": 595014.0
    },
    {
      "sale_date": "2025-05",
      "sum_total_amount": 694638.0
    },
    {
      "sale_date": "2025-06",
      "sum_total_amount": 506422.0
    },
    {
      "sale_date": "2025-07",
      "sum_total_amount": 684376.0
    },
    {
      "sale_date": "2025-08",
      "sum_total_amount": 499268.0
    },
    {
      "sale_date": "2025-09",
      "sum_total_amount": 540932.0
    },
    {
      "sale_date": "2025-10",
      "sum_total_amount": 738178.0
    },
    {
      "sale_date": "2025-11",
      "sum_total_amount": 742616.0
    },
    {
      "sale_date": "2025-12",
      "sum_total_amount": 892402.0
    }
  ];
  
  const xField = 'sale_date';
  const yField = 'sum_total_amount';
  
  const backgroundColor = '#ffffff';
  const containerBackground = '#ffffff';
  const textColor = '#0f172a';
  const lineColor = '#2563eb';
  const highlightColor = '#0891b2';
  const gridColor = '#cbd5e1';
  const axisColor = '#64748b';
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "draw_line",
      "trigger_narration": 0,
      "description": "Line chart entrance animation",
      "time_start": 21.528,
      "duration": 5.240000000000003
    },
    {
      "id": "emphasis_december",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "sale_date": "2025-12"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight December data point when mentioned",
      "time_start": 26.568,
      "duration": 10.135999999999996
    },
    {
      "id": "emphasis_november",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "sale_date": "2025-11"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight November data point when mentioned",
      "time_start": 26.568,
      "duration": 10.135999999999996
    }
  ];

  const narrations = [
    {
      "text": "Looking at the full year trend, Q4 shows remarkable momentum building.",
      "time_start": 21.528,
      "time_end": 26.568,
      "audio_file": "public/audio/generated_20260115_184400_analysis_monthly_revenue_q4_narr0.wav"
    },
    {
      "text": "December reached our highest monthly revenue at $892K, with November close behind at $743K.",
      "time_start": 26.568,
      "time_end": 36.504,
      "audio_file": "public/audio/generated_20260115_184400_analysis_monthly_revenue_q4_narr1.wav"
    }
  ];

  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  const formatNumber = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  };

  const formatMonth = (dateStr: string) => {
    const [year, month] = dateStr.split('-');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return monthNames[parseInt(month) - 1];
  };

  const processedData = useMemo(() => {
    return data.map(d => ({
      ...d,
      monthIndex: parseInt(d[xField].split('-')[1]) - 1,
      formattedMonth: formatMonth(d[xField])
    }));
  }, [data, xField]);
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const xScale = d3.scaleLinear()
      .domain([0, 11])
      .range([0, 800]);
    const yScale = d3.scaleLinear()
      .domain([minValue * 0.9, maxValue * 1.1])
      .range([320, 0]);
    return { xScale, yScale };
  }, [processedData, maxValue, minValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const gradient = defs.append('linearGradient')
      .attr('id', 'revenueGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', lineColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    const shadow = defs.append('filter').attr('id', 'glowShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 3)
      .attr('stdDeviation', 8)
      .attr('flood-color', lineColor)
      .attr('flood-opacity', 0.4);
    
    const g = svg.append('g').attr('transform', 'translate(80, 60)');
    const {xScale, yScale} = scales;
    
    g.selectAll('.grid-y')
      .data(yScale.ticks(6))
      .enter()
      .append('line')
      .attr('class', 'grid-y')
      .attr('x1', 0)
      .attr('x2', 800)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .style('opacity', 0);
    
    const line = d3.line<any>()
      .x((d: any) => xScale(d.monthIndex))
      .y((d: any) => yScale(d[yField]))
      .curve(d3.curveMonotoneX);
    
    const path = g.append('path')
      .datum(processedData)
      .attr('class', 'line')
      .attr('fill', 'none')
      .attr('stroke', lineColor)
      .attr('stroke-width', 4)
      .attr('d', line)
      .style('filter', 'url(#glowShadow)')
      .style('opacity', 0);
    
    g.selectAll('.data-point')
      .data(processedData)
      .enter()
      .append('circle')
      .attr('class', 'data-point')
      .attr('cx', (d: any) => xScale(d.monthIndex))
      .attr('cy', (d: any) => yScale(d[yField]))
      .attr('r', (d: any) => d[yField] === maxValue ? 8 : 5)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : lineColor)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#glowShadow)' : 'none')
      .style('opacity', 0);
    
    g.selectAll('.value-label')
      .data(processedData.filter((d: any, i: number) => i % 2 === 0 || d[yField] === maxValue))
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => xScale(d.monthIndex))
      .attr('y', (d: any) => yScale(d[yField]) - 15)
      .attr('text-anchor', 'middle')
      .text((d: any) => formatNumber(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '20px' : '14px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? '700' : '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.selectAll('.month-label')
      .data(processedData)
      .enter()
      .append('text')
      .attr('class', 'month-label')
      .attr('x', (d: any) => xScale(d.monthIndex))
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => d.formattedMonth)
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.selectAll('.y-tick-label')
      .data(yScale.ticks(6))
      .enter()
      .append('text')
      .attr('class', 'y-tick-label')
      .attr('x', -15)
      .attr('y', (d: any) => yScale(d))
      .attr('text-anchor', 'end')
      .attr('alignment-baseline', 'middle')
      .text((d: any) => formatNumber(d))
      .attr('fill', axisColor)
      .style('font-size', '12px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 160)')
      .text('Total Sales ($)')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', 400)
      .attr('y', 370)
      .attr('text-anchor', 'middle')
      .text('Month')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
      
  }, [scales, maxValue, processedData]);

  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale} = scales;

    // 1. ENTRANCE ANIMATION - draw line effect
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // ✅ CRITICAL: 动画结束后，强制所有元素到最终状态
      if (frame >= animEnd) {
        // Line Chart elements
        g.selectAll('.line').style('opacity', 1);
        g.selectAll('.data-point').style('opacity', 1);
        g.selectAll('.value-label, .month-label, .y-tick-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        g.selectAll('.grid-y').style('opacity', 0.3);
        
        // 继续执行 emphasis 动画（不 return）
      } else if (frame >= animStart) {
        // 入场动画进行中
        const totalTime = (frame - animStart) / fps;  // 当前经过的秒数

        // Line path animation - draw from left to right
        const lineDuration = 2.0; // 2 seconds for line drawing
        if (totalTime <= lineDuration) {
          const lineProgress = totalTime / lineDuration;
          const eased = d3.easeCubicOut(lineProgress);
          
          // Get the path element and animate its stroke-dasharray
          const path = g.select('.line');
          const pathLength = (path.node() as SVGPathElement)?.getTotalLength() || 0;
          
          path
            .style('opacity', 1)
            .style('stroke-dasharray', `${pathLength * eased} ${pathLength}`)
            .style('stroke-dashoffset', 0);
        } else {
          // Line drawing complete
          g.select('.line')
            .style('opacity', 1)
            .style('stroke-dasharray', 'none');
        }

        // Data points appear with delay
        g.selectAll<SVGCircleElement, any>('.data-point').each(function(d: any, i: number) {
          const dot = d3.select(this);
          const delayPerPoint = 0.15;  // 每个点延迟 0.15 秒
          const animDuration = 0.4;   // 单个点动画时长 0.4 秒
          const pointStart = 1.5 + i * delayPerPoint; // 线条画完后开始
          const pointEnd = pointStart + animDuration;

          if (totalTime >= pointStart && totalTime <= pointEnd) {
            // 点动画进行中
            const pointProgress = (totalTime - pointStart) / animDuration;
            const eased = d3.easeBackOut(pointProgress);
            
            dot
              .style('opacity', eased)
              .attr('transform', `scale(${eased})`);
          } else if (totalTime > pointEnd) {
            // 点动画完成
            dot
              .style('opacity', 1)
              .attr('transform', 'scale(1)');
          }
        });

        // Labels fade in after points
        g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerLabel = 0.15;
          const labelDelay = 2.5;  // 额外延迟 2.5 秒
          const animDuration = 0.4;
          const labelStart = i * delayPerLabel + labelDelay;
          const labelEnd = labelStart + animDuration;

          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });

        // Month labels fade in
        g.selectAll<SVGTextElement, any>('.month-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerLabel = 0.08;
          const labelDelay = 2.0;  // 额外延迟 2.0 秒
          const animDuration = 0.4;
          const labelStart = i * delayPerLabel + labelDelay;
          const labelEnd = labelStart + animDuration;

          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });
        
        // Grid and axis labels fade in
        const gridStart = 0.5;
        const gridDuration = 0.6;
        if (totalTime >= gridStart && totalTime <= gridStart + gridDuration) {
          const gridProgress = (totalTime - gridStart) / gridDuration;
          g.selectAll('.grid-y').style('opacity', gridProgress * 0.3);
          g.selectAll('.y-tick-label').style('opacity', gridProgress);
        } else if (totalTime > gridStart + gridDuration) {
          g.selectAll('.grid-y').style('opacity', 0.3);
          g.selectAll('.y-tick-label').style('opacity', 1);
        }

        const axisStart = 1.0;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - 高亮特定数据点
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
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      // 收集所有需要高亮的数据项（使用 Set 避免重复）
      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          // 找到匹配的数据项
          data.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d[xField]);  // 使用 xField 作为唯一标识
            }
          });
        }
      });

      // 一次性处理所有数据点（避免循环覆盖）
      g.selectAll<SVGCircleElement, any>('.data-point').each(function(d: any) {
        const dot = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          dot
            .style('opacity', 1)
            .attr('stroke', '#ef4444')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(239, 68, 68, 0.8))');
        } else {
          dot.style('opacity', 0.3).attr('stroke', '#fff').style('filter', 'none');
        }
      });

      // 高亮对应的标签
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          label
            .style('opacity', 1)
            .attr('fill', '#ef4444')
            .style('font-weight', '700');
        } else {
          label.style('opacity', 0.3);
        }
      });
    }

    // 3. 恢复正常状态（仅在没有 emphasis 时）
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      // Line Chart 元素
      g.selectAll('.data-point')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('opacity', 1)
        .style('filter', (d: any) => d[yField] === maxValue ? 'url(#glowShadow)' : 'none');
      
      g.selectAll('.value-label')
        .style('opacity', 1)
        .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
        .style('font-weight', (d: any) => d[yField] === maxValue ? '700' : '500');
      
      g.selectAll('.month-label, .y-tick-label').style('opacity', 1);
      g.selectAll('.grid-y').style('opacity', 0.3);
      g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, maxValue]);
  
  return (
    <AbsoluteFill style={{ 
      background: '#ffffff',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px'
    }}>
      <div style={{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#111827',
        textAlign: 'center',
      }}>
        Monthly Sales Revenue Trend 2025
      </div>
      
      <svg 
        ref={svgRef} 
        width={960} 
        height={480} 
        style={{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />

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