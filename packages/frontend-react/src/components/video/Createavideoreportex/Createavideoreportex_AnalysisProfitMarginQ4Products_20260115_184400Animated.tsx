import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  // Scene time offset (for independent preview)
  const sceneStartOffset = 84.852;
  
  const data = [
    {
      "product_name": "Gaming Mouse",
      "profit_margin": 0.2857
    },
    {
      "product_name": "Mechanical Keyboard",
      "profit_margin": 0.2857
    },
    {
      "product_name": "NoiseCancel Headset",
      "profit_margin": 0.2857
    },
    {
      "product_name": "Ergo Chair",
      "profit_margin": 0.2857
    },
    {
      "product_name": "4K Monitor",
      "profit_margin": 0.2857
    },
    {
      "product_name": "Smart Watch Gen5",
      "profit_margin": 0.2857
    },
    {
      "product_name": "Laptop Pro X",
      "profit_margin": 0.2857
    },
    {
      "product_name": "SmartPhone Ultra",
      "profit_margin": 0.2857
    }
  ];
  
  const xField = 'product_name';
  const yField = 'profit_margin';
  
  const backgroundColor = '#ffffff';
  const containerBackground = '#ffffff';
  const textColor = '#0f172a';
  const barColor = '#2563eb';
  const highlightColor = '#7c3aed';
  const gridColor = '#cbd5e1';
  const axisColor = '#64748b';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const avgValue = d3.mean(data, (d: any) => d[yField]) || 0;
  
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation - bars grow from bottom",
      "time_start": 84.852,
      "duration": 5.671999999999994
    }
  ];
  
  const narrations = [
    {
      "text": "Finally, profitability remained consistent across our entire product portfolio.",
      "time_start": 84.852,
      "time_end": 90.324,
      "audio_file": "public/audio/generated_20260115_184400_analysis_profit_margin_q4_products_narr0.wav"
    },
    {
      "text": "All products maintained a healthy 28.6% profit margin, showing disciplined pricing strategy.",
      "time_start": 90.324,
      "time_end": 97.416,
      "audio_file": "public/audio/generated_20260115_184400_analysis_profit_margin_q4_products_narr1.wav"
    }
  ];
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.3);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2])
      .range([320, 0]);
    return { xScale, yScale };
  }, [data, maxValue]);
  
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
    
    // 柔和阴影
    const shadow = defs.append('filter').attr('id', 'softShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 2)
      .attr('stdDeviation', 3)
      .attr('flood-color', '#000000')
      .attr('flood-opacity', 0.12);
    
    const g = svg.append('g').attr('transform', 'translate(90, 50)');
    const {xScale, yScale} = scales;
    
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-800)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '3,3')
      .attr('opacity', 0.4);
    
    const bars = g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', 320)
      .attr('width', xScale.bandwidth())
      .attr('height', 0)
      .attr('fill', barColor)
      .attr('rx', 6)
      .style('filter', 'url(#softShadow)')
      .style('opacity', 0);
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${(d[yField] * 100).toFixed(1)}%`)
      .attr('fill', highlightColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '13px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0)
      .each(function(d: any) {
        const text = d3.select(this);
        const textNode = this as SVGTextElement;
        if (textNode.getComputedTextLength() > xScale.bandwidth()) {
          const words = d[xField].split(' ');
          text.text('');
          for (let i = 0; i < words.length; i++) {
            text.append('tspan')
              .attr('x', (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
              .attr('dy', i === 0 ? 0 : '1.1em')
              .text(words[i]);
          }
        }
      });
    
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 160)')
      .text('Profit Margin (%)')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', 400)
      .attr('y', 400)
      .attr('text-anchor', 'middle')
      .text('Products')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0);
    
    g.append('line')
      .attr('x1', 0)
      .attr('y1', 320)
      .attr('x2', 800)
      .attr('y2', 320)
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);
    
    g.append('line')
      .attr('x1', 0)
      .attr('y1', 0)
      .attr('x2', 0)
      .attr('y2', 320)
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);
    
    const avgLine = g.append('line')
      .attr('x1', 0)
      .attr('y1', yScale(avgValue))
      .attr('x2', 800)
      .attr('y2', yScale(avgValue))
      .attr('stroke', '#fbbf24')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '8,4')
      .attr('opacity', 0.8);
    
    g.append('text')
      .attr('x', 810)
      .attr('y', yScale(avgValue) + 5)
      .text(`Avg: ${(avgValue * 100).toFixed(1)}%`)
      .attr('fill', '#fbbf24')
      .style('font-size', '14px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
  }, [scales, maxValue, avgValue]);
  
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
      
      // Animation completed - force all elements to final state
      if (frame >= animEnd) {
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        
      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps;

        // Bars grow sequentially
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12;
          const animDuration = 0.6;
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
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Labels fade in with delay
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
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
        
        // Axis labels fade in
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

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset]);
  
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
        top: 25,
        fontSize: '34px',
        fontWeight: '700',
        color: '#111827',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}>
        Q4 2025 Average Profit Margin by Product
      </div>
      
      <svg 
        ref={svgRef} 
        width={1000} 
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