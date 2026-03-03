import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 5.0;
  
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
  const primaryColor = '#ff6b6b';
  const secondaryColor = '#4ecdc4';
  const highlightColor = '#ffd93d';
  const gridColor = '#2a3441';
  
  const processedData = useMemo(() => {
    const total = d3.sum(data, (d: any) => d[valueField]);
    return data.map(d => ({
      ...d,
      percentage: (d[valueField] / total) * 100,
      displayLabel: d[categoryField]
    }));
  }, [data]);
  
  const colorScale = d3.scaleOrdinal()
    .domain(processedData.map(d => d.displayLabel))
    .range([primaryColor, secondaryColor]);
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_slices",
      "trigger_narration": 0,
      "description": "Pie chart slices grow from center",
      "time_start": 5.0,
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
      "time_start": 8.0,
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
      "time_start": 8.0,
      "duration": 3.2
    }
  ];

  const narrations = [
    {
      "text": "首先来看学生的性别分布情况。",
      "time_start": 5.0,
      "time_end": 8.0
    },
    {
      "text": "男学生占比55%共11人，女学生占比45%共9人，男女比例相对均衡。",
      "time_start": 8.0,
      "time_end": 11.0
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
    
    const gradient1 = defs.append('linearGradient')
      .attr('id', 'maleGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '100%').attr('y2', '100%');
    gradient1.append('stop').attr('offset', '0%').attr('stop-color', primaryColor);
    gradient1.append('stop').attr('offset', '100%').attr('stop-color', '#ff8a80');
    
    const gradient2 = defs.append('linearGradient')
      .attr('id', 'femaleGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '100%').attr('y2', '100%');
    gradient2.append('stop').attr('offset', '0%').attr('stop-color', secondaryColor);
    gradient2.append('stop').attr('offset', '100%').attr('stop-color', '#80e5d1');
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 2)
      .attr('dy', 4)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.25);
    
    const legendGroup = svg.append('g').attr('transform', 'translate(80, 120)');
    const pieGroup = svg.append('g').attr('transform', 'translate(640, 280)');
    
    const pie = d3.pie()
      .value((d: any) => d[valueField])
      .sort(null)
      .startAngle(-Math.PI / 2)
      .endAngle(3 * Math.PI / 2);
    
    const arc = d3.arc()
      .innerRadius(0)
      .outerRadius(160);
    
    const highlightArc = d3.arc()
      .innerRadius(0)
      .outerRadius(170);
    
    const pieData = pie(processedData);
    
    const slices = pieGroup.selectAll('.slice')
      .data(pieData)
      .enter()
      .append('g')
      .attr('class', 'slice');
    
    slices.append('path')
      .attr('class', 'arc')
      .attr('d', (d: any) => {
        const maxValue = d3.max(processedData, (item: any) => item[valueField]);
        return d.data[valueField] === maxValue ? highlightArc(d) : arc(d);
      })
      .attr('fill', (d: any, i: number) => {
        return i === 0 ? 'url(#maleGradient)' : 'url(#femaleGradient)';
      })
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 3)
      .style('filter', 'url(#shadow)')
      .style('opacity', 0)
      .style('transform', 'scale(0)');
    
    slices.append('text')
      .attr('class', 'percentage-label')
      .attr('transform', (d: any) => `translate(${arc.centroid(d)})`)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .text((d: any) => `${d.data.percentage.toFixed(1)}%`)
      .attr('fill', '#ffffff')
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('text-shadow', '2px 2px 4px rgba(0,0,0,0.5)')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const legendItems = legendGroup.selectAll('.legend-item')
      .data(processedData)
      .enter()
      .append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d: any, i: number) => `translate(0, ${i * 60})`);
    
    legendItems.append('circle')
      .attr('class', 'legend-rect')
      .attr('cx', 15)
      .attr('cy', 15)
      .attr('r', 15)
      .attr('fill', (d: any, i: number) => i === 0 ? primaryColor : secondaryColor)
      .style('filter', 'url(#shadow)')
      .style('opacity', 0);
    
    legendItems.append('text')
      .attr('class', 'legend-destination')
      .attr('x', 50)
      .attr('y', 12)
      .text((d: any) => d.displayLabel)
      .attr('fill', textColor)
      .style('font-size', '24px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    legendItems.append('text')
      .attr('class', 'legend-percentage')
      .attr('x', 50)
      .attr('y', 35)
      .text((d: any) => `${d[valueField]}人 (${d.percentage.toFixed(1)}%)`)
      .attr('fill', (d: any, i: number) => i === 0 ? primaryColor : secondaryColor)
      .style('font-size', '18px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    const totalStudents = d3.sum(processedData, (d: any) => d[valueField]);
    pieGroup.append('text')
      .attr('class', 'total-label')
      .attr('x', 0)
      .attr('y', 200)
      .attr('text-anchor', 'middle')
      .text(`总计: ${totalStudents}人`)
      .attr('fill', highlightColor)
      .style('font-size', '20px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
  }, [processedData]);
  
  // ANIMATION UPDATES
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const pieG = svg.selectAll('g').filter(function() {
      const transform = d3.select(this).attr('transform');
      return transform && transform.includes('translate(640, 280)');
    });
    const legendG = svg.selectAll('g').filter(function() {
      const transform = d3.select(this).attr('transform');
      return transform && transform.includes('translate(80, 120)');
    });
    
    if (pieG.empty()) return;

    // 1. ENTRANCE ANIMATION - grow_slices
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // Animation ended, force all elements to final state
      if (frame >= animEnd) {
        // Pie chart elements
        svg.selectAll('.arc').style('opacity', 1).style('transform', 'scale(1)');
        svg.selectAll('.percentage-label').style('opacity', 1);
        svg.selectAll('.total-label').style('opacity', 1);
        svg.selectAll('.legend-rect').style('opacity', 1);
        svg.selectAll('.legend-destination').style('opacity', 1);
        svg.selectAll('.legend-percentage').style('opacity', 1);
        
        // Continue executing emphasis animations (don't return)
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

        // Pie slices grow from center with stagger
        svg.selectAll('.arc').each(function(d: any, i: number) {
          const slice = d3.select(this);
          const delayPerSlice = 0.15;  // 0.15 seconds per slice
          const animDuration = 0.8;   // 0.8 seconds per slice
          const sliceStart = i * delayPerSlice;
          const sliceEnd = sliceStart + animDuration;

          if (totalTime >= sliceStart && totalTime <= sliceEnd) {
            // Slice animation in progress
            const sliceProgress = (totalTime - sliceStart) / animDuration;
            const eased = d3.easeCubicOut(sliceProgress);
            
            slice
              .style('opacity', eased)
              .style('transform', `scale(${eased})`);
          } else if (totalTime > sliceEnd) {
            // Slice animation completed
            slice
              .style('opacity', 1)
              .style('transform', 'scale(1)');
          }
        });

        // Percentage labels fade in with delay
        svg.selectAll('.percentage-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerSlice = 0.15;
          const labelDelay = 0.4;  // Additional delay 0.4 seconds
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
        svg.selectAll('.legend-rect, .legend-destination, .legend-percentage').each(function(d: any, i: number) {
          const element = d3.select(this);
          const legendStart = 0.3;
          const legendDuration = 0.6;
          const itemDelay = i * 0.1;
          const itemStart = legendStart + itemDelay;
          const itemEnd = itemStart + legendDuration;

          if (totalTime >= itemStart && totalTime <= itemEnd) {
            const itemProgress = (totalTime - itemStart) / legendDuration;
            const eased = d3.easeCubicOut(itemProgress);
            element.style('opacity', eased);
          } else if (totalTime > itemEnd) {
            element.style('opacity', 1);
          }
        });

        // Total label fade in
        const totalStart = 0.5;
        const totalDuration = 0.4;
        if (totalTime >= totalStart && totalTime <= totalStart + totalDuration) {
          const totalProgress = (totalTime - totalStart) / totalDuration;
          svg.selectAll('.total-label').style('opacity', d3.easeCubicOut(totalProgress));
        } else if (totalTime > totalStart + totalDuration) {
          svg.selectAll('.total-label').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION - highlight matching slices
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
      
      // Calculate pulse effect for all active animations
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all items that need highlighting
      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          // Find matching data items
          processedData.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d[categoryField]);  // Use categoryField as unique identifier
            }
          });
        }
      });

      // Process all pie slices at once (avoid loop overwriting)
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
            .attr('stroke', '#ffffff')
            .attr('stroke-width', 3)
            .style('filter', 'url(#shadow)');
        }
      });
      
      // Handle legend items emphasis
      svg.selectAll('.legend-rect').each(function(d: any) {
        const rect = d3.select(this);
        const isHighlighted = highlightedItems.has(d[categoryField]);
        
        if (isHighlighted) {
          rect
            .style('opacity', 1)
            .style('filter', 'url(#shadow) drop-shadow(0 0 10px rgba(255, 107, 107, 0.6))');
        } else {
          rect.style('opacity', 0.3).style('filter', 'url(#shadow)');
        }
      });
      
      svg.selectAll('.legend-destination, .legend-percentage').each(function(d: any) {
        const text = d3.select(this);
        const isHighlighted = highlightedItems.has(d[categoryField]);
        text.style('opacity', isHighlighted ? 1 : 0.3);
      });
    }

    // 3. Restore normal state (only when no emphasis is active)
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      // Pie chart elements
      svg.selectAll('.arc')
        .attr('stroke', '#ffffff')
        .attr('stroke-width', 3)
        .style('opacity', 1)
        .style('filter', 'url(#shadow)');
      svg.selectAll('.percentage-label').style('opacity', 1);
      svg.selectAll('.total-label').style('opacity', 1);
      
      // Legend elements
      svg.selectAll('.legend-rect').style('opacity', 1).style('filter', 'url(#shadow)');
      svg.selectAll('.legend-destination, .legend-percentage').style('opacity', 1);
    }

  }, [frame, fps, animations, processedData, sceneStartOffset]);
  
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
      }}>
        学生性别分布情况
      </div>
      
      <svg 
        ref={svgRef} 
        width={960} 
        height={550} 
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