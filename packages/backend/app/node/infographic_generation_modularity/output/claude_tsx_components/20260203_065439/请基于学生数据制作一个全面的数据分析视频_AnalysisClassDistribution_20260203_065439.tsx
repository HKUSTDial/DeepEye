import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 请基于学生数据制作一个全面的数据分析视频_AnalysisClassDistribution_20260203_065439Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
    {
      "class_name": "高一(1)班",
      "count": 5
    },
    {
      "class_name": "高一(2)班",
      "count": 5
    },
    {
      "class_name": "高二(1)班",
      "count": 5
    },
    {
      "class_name": "高三(1)班",
      "count": 5
    }
  ];
  
  // Extract field names from data_binding
  const xField = 'class_name';
  const yField = 'count';
  
  // Color configuration - using uniform class distribution theme with purple/blue accents
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const barColor = '#8b5cf6';  // Purple for uniform distribution analysis
  const highlightColor = '#a855f7';  // Lighter purple accent
  const gridColor = '#2d3748';
  const axisColor = '#718096';
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const avgValue = d3.mean(data, (d: any) => d[yField]) || 0;
  
  // D3 scales for categorical bar chart
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
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create uniform distribution gradient
    const gradient = defs.append('linearGradient')
      .attr('id', 'uniformGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#a855f7');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#8b5cf6');
    
    // Glow effect for uniform bars
    const glow = defs.append('filter').attr('id', 'glow');
    glow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 0)
      .attr('stdDeviation', 8)
      .attr('flood-color', '#a855f7')
      .attr('flood-opacity', 0.6);
    
    // Draw chart
    const g = svg.append('g').attr('transform', 'translate(90, 60)');
    const {xScale, yScale} = scales;
    
    // Draw Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-800)
        .tickFormat(() => "")
        .ticks(5)
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.3);
    
    // Draw bars - all equal, emphasize uniformity
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => 320 - yScale(d[yField]))
      .attr('fill', 'url(#uniformGradient)')
      .attr('rx', 6)
      .style('filter', 'url(#glow)')
      .attr('stroke', highlightColor)
      .attr('stroke-width', 2);
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField])
      .attr('fill', highlightColor)
      .style('font-size', '20px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart
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
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Y-axis label
    g.append('text')
      .attr('x', -70)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 160)')
      .text('学生人数')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Uniformity indicator
    g.append('text')
      .attr('x', 400)
      .attr('y', 40)
      .attr('text-anchor', 'middle')
      .text('完全均衡分布')
      .attr('fill', highlightColor)
      .style('font-size', '18px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Clean up grid
    g.select('.grid-y').select('.domain').remove();
    
  }, [scales, data]);
  
  return (
    <AbsoluteFill style={{ 
      background: '#0f1419',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px'
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}>
        各班级学生人数分布
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={980} 
        height={500} 
        style={{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};