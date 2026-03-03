import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 11.0;
  
  const data = [
    {
      "gender": "男",
      "count": 11
    },
    {
      "gender": "女", 
      "count": 9
    }
  ];
  
  const categoryField = 'gender';
  const valueField = 'count';
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const maleColor = '#4A90E2';
  const femaleColor = '#E24A90';
  const highlightColor = '#FFD700';
  
  const processedData = useMemo(() => {
    const total = d3.sum(data, (d: any) => d[valueField]);
    return data.map(d => ({
      ...d,
      displayLabel: d[categoryField] === '男' ? '男生' : '女生',
      percentage: (d[valueField] / total) * 100,
      color: d[categoryField] === '男' ? maleColor : femaleColor
    }));
  }, [data]);
  
  const formatNumber = (num: number) => num.toString();
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_slices",
      "trigger_narration": 0,
      "description": "Pie chart entrance animation",
      "time_start": 11.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_male",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "gender": "男"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight male students slice when mentioned",
      "time_start": 14.0,
      "duration": 3.2
    },
    {
      "id": "emphasis_female",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "gender": "女"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight female students slice when mentioned",
      "time_start": 14.0,
      "duration": 3.2
    }
  ];

  const narrations = [
    {
      "text": "接下来分析性别分布情况。",
      "time_start": 11.0,
      "time_end": 14.0
    },
    {
      "text": "男生占比55%共11人，女生占比45%共9人，性别分布相对均衡。",
      "time_start": 14.0,
      "time_end": 17.0
    }
  ];

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
    
    const maleGradient = defs.append('linearGradient')
      .attr('id', 'maleGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    maleGradient.append('stop').attr('offset', '0%').attr('stop-color', '#6BB6FF');
    maleGradient.append('stop').attr('offset', '100%').attr('stop-color', '#4A90E2');
    
    const femaleGradient = defs.append('linearGradient')
      .attr('id', 'femaleGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    femaleGradient.append('stop').attr('offset', '0%').attr('stop-color', '#FF6BB6');
    femaleGradient.append('stop').attr('offset', '100%').attr('stop-color', '#E24A90');
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.3);
    
    const legendGroup = svg.append('g')
      .attr('transform', 'translate(100, 140)');
    
    const legendItems = legendGroup.selectAll('.legend-item')
      .data(processedData)
      .enter()
      .append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d: any, i: number) => `translate(0, ${i * 80})`);
    
    legendItems.append('rect')
      .attr('class', 'legend-rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', 24)
      .attr('height', 24)
      .attr('rx', 4)
      .attr('fill', (d: any) => d[categoryField] === '男' ? 'url(#maleGradient)' : 'url(#femaleGradient)')
      .style('filter', 'url(#shadow)')
      .style('opacity', 0);
    
    legendItems.append('text')
      .attr('class', 'legend-label')
      .attr('x', 40)
      .attr('y', 18)
      .text((d: any) => d.displayLabel)
      .attr('fill', textColor)
      .style('font-size', '20px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    legendItems.append('text')
      .attr('class', 'legend-metrics')
      .attr('x', 40)
      .attr('y', 45)
      .text((d: any) => `${formatNumber(d[valueField])}人 (${d.percentage.toFixed(1)}%)`)
      .attr('fill', '#b0b3b8')
      .style('font-size', '16px')
      .style('font-weight', '400')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const pieGroup = svg.append('g')
      .attr('transform', 'translate(640, 280)');
    
    const radius = 160;
    const pie = d3.pie<any>()
      .value((d: any) => d[valueField])
      .sort(null);
    
    const arc = d3.arc<any>()
      .innerRadius(0)
      .outerRadius(radius);
    
    const highlightArc = d3.arc<any>()
      .innerRadius(0)
      .outerRadius(radius + 8);
    
    const pieData = pie(processedData);
    
    const slices = pieGroup.selectAll('.slice')
      .data(pieData)
      .enter()
      .append('g')
      .attr('class', 'slice');
    
    slices.append('path')
      .attr('class', 'arc')
      .attr('d', (d: any) => d.data[valueField] === Math.max(...processedData.map(item => item[valueField])) ? highlightArc(d) : arc(d))
      .attr('fill', (d: any) => d.data[categoryField] === '男' ? 'url(#maleGradient)' : 'url(#femaleGradient)')
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 3)
      .style('filter', 'url(#shadow)')
      .style('opacity', 0)
      .style('transform', 'scale(0)');
    
    slices.append('text')
      .attr('class', 'percentage-label')
      .attr('transform', (d: any) => `translate(${arc.centroid(d)})`)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d.data.percentage.toFixed(1)}%`)
      .attr('fill', '#ffffff')
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('text-shadow', '0 2px 4px rgba(0,0,0,0.5)')
      .style('opacity', 0);
    
    const totalCount = d3.sum(processedData, (d: any) => d[valueField]);
    pieGroup.append('text')
      .attr('class', 'total-label')
      .attr('x', 0)
      .attr('y', radius + 50)
      .attr('text-anchor', 'middle')
      .text(`总计: ${totalCount}人`)
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
  }, [processedData]);

  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    
    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      if (frame >= animEnd) {
        // Animation completed, force all elements to final state
        svg.selectAll('.arc').style('opacity', 1).style('transform', 'scale(1)');
        svg.selectAll('.percentage-label').style('opacity', 1);
        svg.selectAll('.legend-rect, .legend-label, .legend-metrics').style('opacity', 1);
        svg.selectAll('.total-label').style('opacity', 1);
        
      } else if (frame >= animStart) {
        // Animation in progress
        const totalTime = (frame - animStart) / fps;
        
        // Pie slices grow animation
        svg.selectAll('.arc').each(function(d: any, i: number) {
          const slice = d3.select(this);
          const delayPerSlice = 0.15;
          const animDuration = 0.8;
          const sliceStart = i * delayPerSlice;
          const sliceEnd = sliceStart + animDuration;

          if (totalTime >= sliceStart && totalTime <= sliceEnd) {
            const sliceProgress = (totalTime - sliceStart) / animDuration;
            const eased = d3.easeCubicOut(sliceProgress);
            slice
              .style('opacity', eased)
              .style('transform', `scale(${eased})`);
          } else if (totalTime > sliceEnd) {
            slice
              .style('opacity', 1)
              .style('transform', 'scale(1)');
          }
        });

        // Percentage labels fade in
        svg.selectAll('.percentage-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerSlice = 0.15;
          const labelDelay = 0.4;
          const animDuration = 0.5;
          const labelStart = i * delayPerSlice + labelDelay;
          const labelEnd = labelStart + animDuration;

          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });

        // Legend items fade in
        svg.selectAll('.legend-rect, .legend-label, .legend-metrics').each(function(d: any, i: number) {
          const element = d3.select(this);
          const delayPerItem = 0.12;
          const legendDelay = 0.6;
          const animDuration = 0.4;
          const itemStart = i * delayPerItem + legendDelay;
          const itemEnd = itemStart + animDuration;

          if (totalTime >= itemStart && totalTime <= itemEnd) {
            const itemProgress = (totalTime - itemStart) / animDuration;
            const eased = d3.easeCubicOut(itemProgress);
            element.style('opacity', eased);
          } else if (totalTime > itemEnd) {
            element.style('opacity', 1);
          }
        });

        // Total label fade in
        const totalStart = 1.0;
        const totalDuration = 0.4;
        if (totalTime >= totalStart && totalTime <= totalStart + totalDuration) {
          const totalProgress = (totalTime - totalStart) / totalDuration;
          const eased = d3.easeCubicOut(totalProgress);
          svg.selectAll('.total-label').style('opacity', eased);
        } else if (totalTime > totalStart + totalDuration) {
          svg.selectAll('.total-label').style('opacity', 1);
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
              highlightedItems.add(d[categoryField]);
            }
          });
        }
      });

      // Highlight pie slices
      svg.selectAll('.arc').each(function(d: any) {
        const slice = d3.select(this);
        const isHighlighted = highlightedItems.has(d.data[categoryField]);

        if (isHighlighted) {
          slice
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'url(#shadow) drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
        } else {
          slice
            .style('opacity', 0.3)
            .attr('stroke', backgroundColor)
            .attr('stroke-width', 3)
            .style('filter', 'url(#shadow)');
        }
      });

      // Highlight legend items
      svg.selectAll('.legend-item').each(function(d: any) {
        const item = d3.select(this);
        const isHighlighted = highlightedItems.has(d[categoryField]);

        if (isHighlighted) {
          item.selectAll('.legend-rect, .legend-label, .legend-metrics').style('opacity', 1);
        } else {
          item.selectAll('.legend-rect, .legend-label, .legend-metrics').style('opacity', 0.3);
        }
      });
    }

    // 3. Restore normal state
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      svg.selectAll('.arc')
        .attr('stroke', backgroundColor)
        .attr('stroke-width', 3)
        .style('opacity', 1)
        .style('filter', 'url(#shadow)');
      svg.selectAll('.percentage-label').style('opacity', 1);
      svg.selectAll('.legend-rect, .legend-label, .legend-metrics').style('opacity', 1);
      svg.selectAll('.total-label').style('opacity', 1);
    }

  }, [frame, fps, animations, data, categoryField, sceneStartOffset]);
  
  return (
    <AbsoluteFill style={{ 
      background: '#0f1419',
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
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        性别分布统计
      </div>
      
      <svg 
        ref={svgRef} 
        width={960} 
        height={500} 
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