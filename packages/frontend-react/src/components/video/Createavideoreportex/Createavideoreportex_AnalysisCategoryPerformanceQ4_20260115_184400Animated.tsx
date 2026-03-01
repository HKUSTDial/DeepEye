import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 49.968;
  
  const data = [
    {
      "category": "Electronics",
      "sum_total_amount": 6047230.0,
      "count": 1017
    },
    {
      "category": "Accessories", 
      "sum_total_amount": 1020222.0,
      "count": 742
    },
    {
      "category": "Furniture",
      "sum_total_amount": 621180.0,
      "count": 241
    }
  ];

  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_slices",
      "trigger_narration": 0,
      "description": "Pie chart slices grow from center",
      "time_start": 49.968,
      "duration": 5.275999999999994
    },
    {
      "id": "emphasis_electronics",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {
        "data_filter": {
          "category": "Electronics"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Electronics category when mentioned",
      "time_start": 55.093999999999994,
      "duration": 8.590000000000003,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "Electronics",
        "word_time": 55.093999999999994
      }
    }
  ];

  const narrations = [
    {
      "text": "Breaking down by category reveals the product mix behind our peak performance.",
      "time_start": 49.968,
      "time_end": 55.044,
      "audio_file": "public/audio/generated_20260115_184400_analysis_category_performance_q4_narr0.wav"
    },
    {
      "text": "Electronics dominated Q4 with $6.0M representing 79% of total revenue during the quarter.",
      "time_start": 55.044,
      "time_end": 63.684,
      "audio_file": "public/audio/generated_20260115_184400_analysis_category_performance_q4_narr1.wav"
    }
  ];

  const categoryField = 'category';
  const valueField = 'sum_total_amount';
  
  const backgroundColor = '#ffffff';
  const containerBackground = '#ffffff';
  const textColor = '#0f172a';
  const labelColor = '#64748b';
  
  // 饼图配色方案：蓝色系渐变，每个分类用不同深浅的蓝
  const categoryColors = [
    '#2563eb', // Electronics - 深蓝（主要）
    '#60a5fa', // Accessories - 中蓝
    '#93c5fd', // Furniture - 浅蓝
  ];

  const processedData = useMemo(() => {
    const total = d3.sum(data, (d: any) => d[valueField]);
    return data.map(d => ({
      ...d,
      displayLabel: d[categoryField],
      percentage: (d[valueField] / total) * 100
    })).sort((a, b) => b[valueField] - a[valueField]);
  }, [data]);

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `$${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `$${(num / 1000).toFixed(0)}K`;
    return `$${num.toFixed(0)}`;
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
    
    // 柔和的阴影效果（代替刺眼的发光）
    const shadow = defs.append('filter').attr('id', 'softShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 2)
      .attr('stdDeviation', 3)
      .attr('flood-color', '#000000')
      .attr('flood-opacity', 0.15);

    const legendGroup = svg.append('g')
      .attr('transform', 'translate(80, 120)');

    const legendItems = legendGroup.selectAll('.legend-item')
      .data(processedData)
      .enter()
      .append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d, i) => `translate(0, ${i * 45})`);

    legendItems.append('rect')
      .attr('class', 'legend-rect')
      .attr('width', 20)
      .attr('height', 20)
      .attr('rx', 4)
      .attr('fill', (d, i) => categoryColors[i])
      .style('opacity', 0);

    legendItems.append('text')
      .attr('class', 'legend-label')
      .attr('x', 35)
      .attr('y', 10)
      .attr('dy', '0.35em')
      .text(d => d.displayLabel)
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', (d, i) => i === 0 ? '700' : '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);

    legendItems.append('text')
      .attr('class', 'legend-value')
      .attr('x', 35)
      .attr('y', 28)
      .text(d => `${formatNumber(d[valueField])} (${d.percentage.toFixed(1)}%)`)
      .attr('fill', labelColor)
      .style('font-size', '14px')
      .style('font-weight', '400')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);

    const pieGroup = svg.append('g')
      .attr('transform', 'translate(640, 280)');

    const radius = 160;
    const pie = d3.pie<any>()
      .value(d => d[valueField])
      .sort(null);

    const arc = d3.arc<any>()
      .innerRadius(0)
      .outerRadius(radius);

    const highlightArc = d3.arc<any>()
      .innerRadius(0)
      .outerRadius(radius + 12);

    const arcs = pie(processedData);

    const slices = pieGroup.selectAll('.slice')
      .data(arcs)
      .enter()
      .append('g')
      .attr('class', 'slice');

    slices.append('path')
      .attr('class', 'arc')
      .attr('d', (d, i) => i === 0 ? highlightArc(d) : arc(d))
      .attr('fill', (d, i) => categoryColors[i])
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 3)
      .style('filter', 'url(#softShadow)')
      .style('opacity', 0)
      .style('transform', 'scale(0)');

    slices.append('text')
      .attr('class', 'percentage-label')
      .attr('transform', d => `translate(${arc.centroid(d)})`)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .text(d => `${d.data.percentage.toFixed(1)}%`)
      .attr('fill', backgroundColor)
      .style('font-size', '16px')
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
    if (svg.empty()) return;

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');
    
    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;
      
      // Animation ended - force all elements to final state
      if (frame >= animEnd) {
        svg.selectAll('.arc').style('opacity', 1).style('transform', 'scale(1)');
        svg.selectAll('.percentage-label').style('opacity', 1);
        svg.selectAll('.legend-rect, .legend-label, .legend-value').style('opacity', 1);
        
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;

        // Pie slices grow from center
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

        // Percentage labels fade in after slices
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
        svg.selectAll('.legend-rect, .legend-label, .legend-value').each(function(d: any, i: number) {
          const element = d3.select(this);
          const delayPerItem = 0.12;
          const legendDelay = 0.5;
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
          processedData.forEach((d: any) => {
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
            .attr('stroke', '#0891b2')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'drop-shadow(0 0 12px rgba(8, 145, 178, 0.6))');
        } else {
          slice.style('opacity', 0.3).attr('stroke', backgroundColor).style('filter', 'none');
        }
      });

      // Highlight legend items
      svg.selectAll('.legend-item').each(function(d: any) {
        const item = d3.select(this);
        const isHighlighted = highlightedItems.has(d[categoryField]);

        if (isHighlighted) {
          item.selectAll('.legend-rect')
            .attr('stroke', '#0891b2')
            .attr('stroke-width', 2 * maxPulse)
            .style('filter', 'drop-shadow(0 0 8px rgba(8, 145, 178, 0.5))');
          item.selectAll('.legend-label, .legend-value').style('opacity', 1);
        } else {
          item.selectAll('.legend-rect').attr('stroke', 'none').style('filter', 'none');
          item.selectAll('.legend-label, .legend-value').style('opacity', 0.4);
        }
      });
    }

    // 3. Restore normal state
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      svg.selectAll('.arc').attr('stroke', backgroundColor).style('opacity', 1).style('filter', 'url(#softShadow)');
      svg.selectAll('.percentage-label').style('opacity', 1);
      svg.selectAll('.legend-rect').attr('stroke', 'none').style('filter', 'none');
      svg.selectAll('.legend-label, .legend-value').style('opacity', 1);
    }

  }, [frame, fps, animations, processedData, categoryField, sceneStartOffset]);

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
        Q4 2025 Sales Distribution by Category
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