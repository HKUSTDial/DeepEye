import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 6.732;  // Start time of the scene in the original video
  
  const data = [
    {
      "sale_date": "2025-01-01",
      "sum_total_amount": 27482.0
    },
    {
      "sale_date": "2025-01-02",
      "sum_total_amount": 5432.0
    },
    {
      "sale_date": "2025-01-03",
      "sum_total_amount": 28966.0
    },
    {
      "sale_date": "2025-01-04",
      "sum_total_amount": 23170.0
    },
    {
      "sale_date": "2025-01-05",
      "sum_total_amount": 6860.0
    },
    {
      "sale_date": "2025-01-06",
      "sum_total_amount": 2856.0
    },
    {
      "sale_date": "2025-01-07",
      "sum_total_amount": 13720.0
    },
    {
      "sale_date": "2025-01-08",
      "sum_total_amount": 12110.0
    },
    {
      "sale_date": "2025-01-09",
      "sum_total_amount": 8540.0
    },
    {
      "sale_date": "2025-01-10",
      "sum_total_amount": 41454.0
    },
    {
      "sale_date": "2025-01-11",
      "sum_total_amount": 22820.0
    },
    {
      "sale_date": "2025-01-12",
      "sum_total_amount": 34580.0
    },
    {
      "sale_date": "2025-01-13",
      "sum_total_amount": 14700.0
    },
    {
      "sale_date": "2025-01-14",
      "sum_total_amount": 7084.0
    },
    {
      "sale_date": "2025-01-15",
      "sum_total_amount": 16142.0
    },
    {
      "sale_date": "2025-01-16",
      "sum_total_amount": 27720.0
    },
    {
      "sale_date": "2025-01-17",
      "sum_total_amount": 5040.0
    },
    {
      "sale_date": "2025-01-18",
      "sum_total_amount": 24640.0
    },
    {
      "sale_date": "2025-01-19",
      "sum_total_amount": 17080.0
    },
    {
      "sale_date": "2025-01-20",
      "sum_total_amount": 6930.0
    },
    {
      "sale_date": "2025-01-21",
      "sum_total_amount": 7616.0
    },
    {
      "sale_date": "2025-01-22",
      "sum_total_amount": 28672.0
    },
    {
      "sale_date": "2025-01-23",
      "sum_total_amount": 26194.0
    },
    {
      "sale_date": "2025-01-24",
      "sum_total_amount": 11452.0
    },
    {
      "sale_date": "2025-01-25",
      "sum_total_amount": 21924.0
    },
    {
      "sale_date": "2025-01-26",
      "sum_total_amount": 6160.0
    },
    {
      "sale_date": "2025-01-27",
      "sum_total_amount": 7882.0
    },
    {
      "sale_date": "2025-01-28",
      "sum_total_amount": 32410.0
    },
    {
      "sale_date": "2025-01-29",
      "sum_total_amount": 6664.0
    },
    {
      "sale_date": "2025-01-30",
      "sum_total_amount": 42042.0
    }
  ];
  
  const animations = [
    {
      "id": "entrance_daily_revenue_chart",
      "type": "entrance",
      "effect": "draw_line",
      "trigger_narration": 0,
      "description": "Line chart draws in showing daily revenue trend",
      "time_start": 6.732,
      "duration": 6.103999999999999
    },
    {
      "id": "emphasis_lowest_revenue",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "sale_date": "2025-01-06"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight lowest revenue point at $2.9K on January 6th",
      "time_start": 12.636,
      "duration": 9.091999999999999
    },
    {
      "id": "emphasis_highest_revenue",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "sale_date": "2025-01-30"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight highest revenue point at $42K on January 30th",
      "time_start": 12.636,
      "duration": 9.091999999999999
    }
  ];
  
  const narrations = [
    {
      "text": "Starting with our daily revenue pattern in January, we see significant volatility.",
      "time_start": 6.732,
      "time_end": 12.636,
      "audio_file": "public/audio/generated_20260115_184400_analysis_quarterly_revenue_trend_narr0.wav"
    },
    {
      "text": "Daily sales ranged from $2.9K to $42K, showing fluctuating customer demand throughout the month.",
      "time_start": 12.636,
      "time_end": 21.528,
      "audio_file": "public/audio/generated_20260115_184400_analysis_quarterly_revenue_trend_narr1.wav"
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
  
  const processedData = useMemo(() => {
    const parseDate = d3.timeParse('%Y-%m-%d');
    return data.map(d => ({
      ...d,
      parsedDate: parseDate(d[xField])
    })).filter(d => d.parsedDate !== null).sort((a, b) => a.parsedDate.getTime() - b.parsedDate.getTime());
  }, [data, xField]);
  
  const maxValue = d3.max(processedData, (d: any) => d[yField]) || 0;
  const minValue = d3.min(processedData, (d: any) => d[yField]) || 0;
  const maxItem = processedData.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const xScale = d3.scaleTime()
      .domain(d3.extent(processedData, (d: any) => d.parsedDate) as [Date, Date])
      .range([0, 800]);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([350, 0]);
    return { xScale, yScale };
  }, [processedData, maxValue]);
  
  const formatNumber = (value: number) => {
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(1)}K`;
    }
    return `$${value.toFixed(0)}`;
  };
  
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr => 
      currentTime >= (narr.time_start - sceneStartOffset) && 
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const gradient = defs.append('linearGradient')
      .attr('id', 'lineGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', lineColor).attr('stop-opacity', 0.8);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor).attr('stop-opacity', 0.3);
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 2)
      .attr('stdDeviation', 4)
      .attr('flood-color', highlightColor)
      .attr('flood-opacity', 0.4);
    
    const g = svg.append('g').attr('transform', 'translate(80, 80)');
    const {xScale, yScale} = scales;
    
    g.selectAll('.grid-x')
      .data(xScale.ticks(6))
      .enter()
      .append('line')
      .attr('class', 'grid-x')
      .attr('x1', d => xScale(d))
      .attr('x2', d => xScale(d))
      .attr('y1', 0)
      .attr('y2', 350)
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .style('opacity', 0);
    
    g.selectAll('.grid-y')
      .data(yScale.ticks(6))
      .enter()
      .append('line')
      .attr('class', 'grid-y')
      .attr('x1', 0)
      .attr('x2', 800)
      .attr('y1', d => yScale(d))
      .attr('y2', d => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .style('opacity', 0);
    
    const line = d3.line<any>()
      .x(d => xScale(d.parsedDate))
      .y(d => yScale(d[yField]))
      .curve(d3.curveMonotoneX);
    
    const area = d3.area<any>()
      .x(d => xScale(d.parsedDate))
      .y0(350)
      .y1(d => yScale(d[yField]))
      .curve(d3.curveMonotoneX);
    
    g.append('path')
      .datum(processedData)
      .attr('class', 'area-path')
      .attr('fill', 'url(#lineGradient)')
      .attr('d', area)
      .style('opacity', 0);
    
    g.append('path')
      .datum(processedData)
      .attr('class', 'line-path')
      .attr('fill', 'none')
      .attr('stroke', lineColor)
      .attr('stroke-width', 3)
      .attr('d', line)
      .style('opacity', 0);
    
    g.selectAll('.data-point')
      .data(processedData)
      .enter()
      .append('circle')
      .attr('class', 'data-point')
      .attr('cx', d => xScale(d.parsedDate))
      .attr('cy', d => yScale(d[yField]))
      .attr('r', d => d[yField] === maxValue ? 8 : 4)
      .attr('fill', d => d[yField] === maxValue ? highlightColor : lineColor)
      .attr('stroke', d => d[yField] === maxValue ? '#fff' : 'none')
      .attr('stroke-width', d => d[yField] === maxValue ? 2 : 0)
      .style('filter', d => d[yField] === maxValue ? 'url(#shadow)' : 'none')
      .style('opacity', 0);
    
    if (maxItem) {
      g.append('text')
        .attr('class', 'max-value-label')
        .attr('x', xScale(maxItem.parsedDate))
        .attr('y', yScale(maxItem[yField]) - 15)
        .attr('text-anchor', 'middle')
        .text(formatNumber(maxItem[yField]))
        .attr('fill', highlightColor)
        .style('font-size', '16px')
        .style('font-weight', '700')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision')
        .style('opacity', 0);
    }
    
    const xAxis = d3.axisBottom(xScale)
      .ticks(6)
      .tickFormat(d3.timeFormat('%m/%d'));
    
    const yAxis = d3.axisLeft(yScale)
      .ticks(6)
      .tickFormat(d => formatNumber(d as number));
    
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', 'translate(0, 350)')
      .call(xAxis);
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis);
    
    g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor);
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);
    g.selectAll('.x-axis text, .y-axis text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', 400)
      .attr('y', 390)
      .attr('text-anchor', 'middle')
      .text('Date')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', 175)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 175)')
      .text('Revenue ($)')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
  }, [scales, processedData, maxValue, maxItem, xField, yField]);
  
  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {xScale, yScale} = scales;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // Animation completed - force all elements to final state
      if (frame >= animEnd) {
        // Line chart elements
        g.selectAll('.line-path').style('opacity', 1);
        g.selectAll('.area-path').style('opacity', 0.4);
        g.selectAll('.data-point').style('opacity', 1);
        g.selectAll('.max-value-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        g.selectAll('.grid-x, .grid-y').style('opacity', 0.3);
        
        // Continue executing emphasis animations (don't return)
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds
        const totalDuration = entranceAnim.duration;
        
        // Line drawing effect - progressive reveal
        const lineProgress = Math.min(totalTime / (totalDuration * 0.7), 1);  // Line draws in first 70% of time
        const easedLineProgress = d3.easeCubicOut(lineProgress);
        
        // Calculate path length and animate stroke-dasharray
        const linePath = g.select('.line-path').node() as SVGPathElement;
        const areaPath = g.select('.area-path').node() as SVGPathElement;
        
        if (linePath) {
          const pathLength = linePath.getTotalLength();
          const currentLength = pathLength * easedLineProgress;
          
          g.select('.line-path')
            .style('stroke-dasharray', `${currentLength} ${pathLength}`)
            .style('opacity', 1);
        }
        
        if (areaPath) {
          const pathLength = areaPath.getTotalLength();
          const currentLength = pathLength * easedLineProgress;
          
          g.select('.area-path')
            .style('stroke-dasharray', `${currentLength} ${pathLength}`)
            .style('opacity', 0.4);
        }
        
        // Data points appear progressively
        g.selectAll<SVGCircleElement, any>('.data-point').each(function(d: any, i: number) {
          const point = d3.select(this);
          const pointDelay = 0.2;  // Points start appearing after 0.2s
          const delayPerPoint = 0.05;  // 0.05s delay between points
          const pointDuration = 0.4;   // Each point takes 0.4s to fully appear
          const pointStart = pointDelay + i * delayPerPoint;
          const pointEnd = pointStart + pointDuration;

          if (totalTime >= pointStart && totalTime <= pointEnd) {
            const pointProgress = (totalTime - pointStart) / pointDuration;
            const eased = d3.easeCubicOut(pointProgress);
            point.style('opacity', eased);
          } else if (totalTime > pointEnd) {
            point.style('opacity', 1);
          }
        });
        
        // Grid lines fade in
        const gridStart = totalDuration * 0.1;  // Grid appears early
        const gridDuration = totalDuration * 0.3;
        if (totalTime >= gridStart && totalTime <= gridStart + gridDuration) {
          const gridProgress = (totalTime - gridStart) / gridDuration;
          g.selectAll('.grid-x, .grid-y').style('opacity', gridProgress * 0.3);
        } else if (totalTime > gridStart + gridDuration) {
          g.selectAll('.grid-x, .grid-y').style('opacity', 0.3);
        }
        
        // Labels fade in
        const labelStart = totalDuration * 0.6;  // Labels appear near end
        const labelDuration = totalDuration * 0.4;
        if (totalTime >= labelStart && totalTime <= labelStart + labelDuration) {
          const labelProgress = (totalTime - labelStart) / labelDuration;
          const eased = d3.easeCubicOut(labelProgress);
          g.selectAll('.max-value-label').style('opacity', eased);
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', eased);
        } else if (totalTime > labelStart + labelDuration) {
          g.selectAll('.max-value-label').style('opacity', 1);
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - highlight specific data points
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
      
      // Calculate pulse effect from all active animations
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting
      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          processedData.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d[xField]);
            }
          });
        }
      });

      // Apply highlighting to all data points at once
      g.selectAll<SVGCircleElement, any>('.data-point').each(function(d: any) {
        const point = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          point
            .style('opacity', 1)
            .attr('stroke', '#ef4444')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(239, 68, 68, 0.8))');
        } else {
          point.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none');
        }
      });
      
      // Also highlight corresponding line segments if needed
      if (highlightedItems.size > 0) {
        g.select('.line-path').style('opacity', 0.6);
        g.select('.area-path').style('opacity', 0.2);
      }
    }

    // 3. Restore normal state when no emphasis is active
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      // Line chart elements
      g.selectAll('.data-point')
        .attr('stroke', (d: any) => d[yField] === maxValue ? '#fff' : 'none')
        .attr('stroke-width', (d: any) => d[yField] === maxValue ? 2 : 0)
        .style('opacity', 1)
        .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none');
      g.selectAll('.line-path').style('opacity', 1);
      g.selectAll('.area-path').style('opacity', 0.4);
      g.selectAll('.max-value-label').style('opacity', 1);
      g.selectAll('.grid-x, .grid-y').style('opacity', 0.3);
      g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, processedData, xField, yField, sceneStartOffset, maxValue]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
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
        color: textColor,
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        Daily Revenue Trend - January 2025
      </div>
      
      <svg 
        ref={svgRef} 
        width={960} 
        height={520} 
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
          {getCurrentNarration()?.text}
        </div>
      )}
    </AbsoluteFill>
  );
};