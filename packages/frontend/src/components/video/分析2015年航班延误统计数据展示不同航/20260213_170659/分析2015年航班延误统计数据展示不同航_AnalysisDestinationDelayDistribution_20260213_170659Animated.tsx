import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 10.0;
  
  const data = [
    {
      "destcity": "Boston",
      "avg_depdelay": 6.67,
      "avg_arrdelay": -8.08,
      "count": 12
    },
    {
      "destcity": "Dallas",
      "avg_depdelay": 40.62,
      "avg_arrdelay": 47.44,
      "count": 16
    },
    {
      "destcity": "Los Angeles",
      "avg_depdelay": 1.62,
      "avg_arrdelay": -14.31,
      "count": 16
    },
    {
      "destcity": "Minneapolis",
      "avg_depdelay": 55.8,
      "avg_arrdelay": 51.1,
      "count": 10
    },
    {
      "destcity": "New York",
      "avg_depdelay": 7.68,
      "avg_arrdelay": -7.47,
      "count": 19
    },
    {
      "destcity": "San Francisco",
      "avg_depdelay": 10.23,
      "avg_arrdelay": -15.69,
      "count": 13
    },
    {
      "destcity": "Washington",
      "avg_depdelay": 3.21,
      "avg_arrdelay": -9.07,
      "count": 14
    }
  ];
  
  const xField = 'destcity';
  const yAxisFields = [
    { field: 'avg_depdelay', label: '平均起飞延误(分钟)' },
    { field: 'avg_arrdelay', label: '平均到达延误(分钟)' }
  ];
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 10.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_minneapolis",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "destcity": "Minneapolis"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Minneapolis when mentioned",
      "time_start": 10.0,
      "duration": 3.2
    }
  ];
  
  const narrations = [
    {
      "text": "Minneapolis延误最严重，平均起飞延误55.8分钟，到达延误51.1分钟。多数城市到达延误为负值，表明航班能够弥补起飞延误。",
      "time_start": 10.0,
      "time_end": 13.0
    }
  ];
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const depDelayColor = '#ef4444';
  const arrDelayColor = '#f97316';
  const highlightColor = '#fbbf24';
  const gridColor = '#2a2a2a';
  const axisColor = '#666666';
  
  const maxDepDelay = d3.max(data, (d: any) => d.avg_depdelay) || 0;
  const minArrDelay = d3.min(data, (d: any) => d.avg_arrdelay) || 0;
  const maxValue = Math.max(maxDepDelay, Math.abs(minArrDelay));
  const minneapolisData = data.find(d => d.destcity === 'Minneapolis');
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.3);
    
    const subGroups = yAxisFields.map(y => y.field);
    const xSubgroup = d3.scaleBand()
      .domain(subGroups)
      .range([0, xScale.bandwidth()])
      .padding(0.1);
    
    const yScale = d3.scaleLinear()
      .domain([minArrDelay * 1.2, maxDepDelay * 1.2])
      .range([320, 0]);
    
    return { xScale, yScale, xSubgroup };
  }, [data, maxDepDelay, minArrDelay]);
  
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
    
    const depGradient = defs.append('linearGradient')
      .attr('id', 'depGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    depGradient.append('stop').attr('offset', '0%').attr('stop-color', '#fca5a5');
    depGradient.append('stop').attr('offset', '100%').attr('stop-color', depDelayColor);
    
    const arrGradient = defs.append('linearGradient')
      .attr('id', 'arrGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    arrGradient.append('stop').attr('offset', '0%').attr('stop-color', '#fed7aa');
    arrGradient.append('stop').attr('offset', '100%').attr('stop-color', arrDelayColor);
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 3)
      .attr('stdDeviation', 4)
      .attr('flood-opacity', 0.25);
    
    const g = svg.append('g').attr('transform', 'translate(80, 80)');
    const {xScale, yScale, xSubgroup} = scales;
    
    g.append('line')
      .attr('x1', 0)
      .attr('x2', 800)
      .attr('y1', yScale(0))
      .attr('y2', yScale(0))
      .attr('stroke', gridColor)
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '5,5');
    
    yAxisFields.forEach((yAxisConfig, i) => {
      const yField = yAxisConfig.field;
      const barColor = i === 0 ? 'url(#depGradient)' : 'url(#arrGradient)';
      
      g.selectAll(`.bar-${yField}`)
        .data(data)
        .enter()
        .append('rect')
        .attr('class', `bar bar-${yField}`)
        .attr('x', (d: any) => (xScale(d[xField]) || 0) + xSubgroup(yField))
        .attr('y', 320)
        .attr('width', xSubgroup.bandwidth())
        .attr('height', 0)
        .attr('fill', (d: any) => d.destcity === 'Minneapolis' ? highlightColor : barColor)
        .attr('rx', 4)
        .style('filter', 'url(#shadow)')
        .style('opacity', 0);
      
      g.selectAll(`.value-label-${yField}`)
        .data(data)
        .enter()
        .append('text')
        .attr('class', `value-label value-label-${yField}`)
        .attr('x', (d: any) => (xScale(d[xField]) || 0) + xSubgroup(yField) + xSubgroup.bandwidth() / 2)
        .attr('y', (d: any) => d[yField] >= 0 ? yScale(d[yField]) - 8 : yScale(0) + 20)
        .attr('text-anchor', 'middle')
        .text((d: any) => d[yField].toFixed(1))
        .attr('fill', (d: any) => d.destcity === 'Minneapolis' ? '#fbbf24' : textColor)
        .style('font-size', '13px')
        .style('font-weight', '600')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision')
        .style('opacity', 0);
    });
    
    g.selectAll('.city-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label city-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', (d: any) => d.destcity === 'Minneapolis' ? highlightColor : textColor)
      .style('font-size', '14px')
      .style('font-weight', (d: any) => d.destcity === 'Minneapolis' ? '700' : '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const legend = g.append('g')
      .attr('transform', 'translate(580, 30)');
    
    yAxisFields.forEach((yAxisConfig, i) => {
      const legendColor = i === 0 ? depDelayColor : arrDelayColor;
      
      legend.append('rect')
        .attr('class', 'x-axis-label')
        .attr('x', 0)
        .attr('y', i * 30)
        .attr('width', 18)
        .attr('height', 18)
        .attr('fill', legendColor)
        .attr('rx', 3)
        .style('opacity', 0);
      
      legend.append('text')
        .attr('class', 'y-axis-label')
        .attr('x', 25)
        .attr('y', i * 30 + 14)
        .text(yAxisConfig.label)
        .attr('fill', textColor)
        .style('font-size', '14px')
        .style('font-weight', '500')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision')
        .style('opacity', 0);
    });
    
  }, [scales, data]);
  
  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const {yScale} = scales;
    const innerHeight = 320;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      if (frame >= animEnd) {
        // Animation completed, force all elements to final state
        yAxisFields.forEach((yAxisConfig) => {
          const yField = yAxisConfig.field;
          g.selectAll(`.bar-${yField}`).each(function(d: any) {
            const bar = d3.select(this);
            const targetHeight = Math.abs(yScale(d[yField]) - yScale(0));
            bar
              .attr('height', targetHeight)
              .attr('y', d[yField] >= 0 ? yScale(d[yField]) : yScale(0))
              .style('opacity', 1);
          });
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        
      } else if (frame >= animStart) {
        // Animation in progress
        const totalTime = (frame - animStart) / fps;

        // Bar animation
        yAxisFields.forEach((yAxisConfig) => {
          const yField = yAxisConfig.field;
          g.selectAll(`.bar-${yField}`).each(function(d: any, i: number) {
            const bar = d3.select(this);
            const delayPerBar = 0.12;
            const animDuration = 0.6;
            const barStart = i * delayPerBar;
            const barEnd = barStart + animDuration;

            if (totalTime >= barStart && totalTime <= barEnd) {
              const barProgress = (totalTime - barStart) / animDuration;
              const eased = d3.easeCubicOut(barProgress);
              const targetHeight = Math.abs(yScale(d[yField]) - yScale(0));
              const currentHeight = targetHeight * eased;

              bar
                .attr('height', Math.max(0, currentHeight))
                .attr('y', d[yField] >= 0 ? innerHeight - Math.max(0, currentHeight) : yScale(0))
                .style('opacity', eased);
            } else if (totalTime > barEnd) {
              const targetHeight = Math.abs(yScale(d[yField]) - yScale(0));
              bar
                .attr('height', targetHeight)
                .attr('y', d[yField] >= 0 ? yScale(d[yField]) : yScale(0))
                .style('opacity', 1);
            }
          });
        });

        // Label animation
        g.selectAll('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3;
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
        
        // Axis labels animation
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', axisProgress);
        } else if (totalTime > axisStart + axisDuration) {
          g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;
    
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });
    
    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;
      
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

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

      g.selectAll('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'url(#shadow)');
        }
      });
    }

    // 3. Restore normal state
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1).style('filter', 'url(#shadow)');
      g.selectAll('.value-label, .category-label').style('opacity', 1);
      g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, sceneStartOffset]);
  
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
        top: 25,
        fontSize: '34px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        各城市平均起飞延误与到达延误对比
      </div>
      
      <svg 
        ref={svgRef} 
        width={960} 
        height={500} 
        style={{ 
          marginTop: '40px',
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