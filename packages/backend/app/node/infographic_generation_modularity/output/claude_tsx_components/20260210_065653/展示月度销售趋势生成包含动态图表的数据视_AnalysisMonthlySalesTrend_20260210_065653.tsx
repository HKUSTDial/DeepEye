import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 展示月度销售趋势生成包含动态图表的数据视_AnalysisMonthlySalesTrend_20260210_065653Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  const data = [
    { month: "1", sum_sales: 1200, count: 1 },
    { month: "2", sum_sales: 1500, count: 1 },
    { month: "3", sum_sales: 1800, count: 1 },
    { month: "4", sum_sales: 2000, count: 1 }
  ];
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const lineColor = '#10b981';
  const highlightColor = '#34d399';
  const gridColor = '#2a3441';
  const axisColor = '#4a5568';
  const accentGold = '#fbbf24';
  
  const maxValue = d3.max(data, (d: any) => d.sum_sales) || 0;
  const minValue = d3.min(data, (d: any) => d.sum_sales) || 0;
  
  const scales = useMemo(() => {
    const xScale = d3.scaleLinear()
      .domain([1, 4])
      .range([0, 900]);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15])
      .range([340, 0]);
    return { xScale, yScale };
  }, [maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const gradient = defs.append('linearGradient')
      .attr('id', 'lineGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', lineColor);
    
    const glowFilter = defs.append('filter').attr('id', 'glow');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'coloredBlur');
    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
    
    const pointShadow = defs.append('filter').attr('id', 'pointShadow');
    pointShadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 2)
      .attr('stdDeviation', 4)
      .attr('flood-opacity', 0.4);
    
    const g = svg.append('g').attr('transform', 'translate(100, 100)');
    const { xScale, yScale } = scales;
    
    g.selectAll('.grid-y')
      .data(yScale.ticks(5))
      .enter()
      .append('line')
      .attr('class', 'grid-y')
      .attr('x1', 0)
      .attr('x2', 900)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,4')
      .attr('opacity', 0.5);
    
    const line = d3.line()
      .x((d: any) => xScale(+d.month))
      .y((d: any) => yScale(d.sum_sales))
      .curve(d3.curveMonotoneX);
    
    const area = d3.area()
      .x((d: any) => xScale(+d.month))
      .y0(340)
      .y1((d: any) => yScale(d.sum_sales))
      .curve(d3.curveMonotoneX);
    
    g.append('path')
      .datum(data)
      .attr('fill', 'url(#lineGradient)')
      .attr('opacity', 0.15)
      .attr('d', area as any);
    
    g.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', lineColor)
      .attr('stroke-width', 3)
      .attr('d', line as any)
      .style('filter', 'url(#glow)');
    
    g.selectAll('.data-point')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'data-point')
      .attr('cx', (d: any) => xScale(+d.month))
      .attr('cy', (d: any) => yScale(d.sum_sales))
      .attr('r', (d: any) => d.sum_sales === maxValue ? 8 : 6)
      .attr('fill', (d: any) => d.sum_sales === maxValue ? accentGold : highlightColor)
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 2)
      .style('filter', 'url(#pointShadow)');
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => xScale(+d.month))
      .attr('y', (d: any) => yScale(d.sum_sales) - 20)
      .attr('text-anchor', 'middle')
      .text((d: any) => d.sum_sales)
      .attr('fill', (d: any) => d.sum_sales === maxValue ? accentGold : textColor)
      .style('font-size', (d: any) => d.sum_sales === maxValue ? '22px' : '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d: any) => d.toString());
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.select('.y-axis').selectAll('line, path')
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);
    
    g.append('text')
      .attr('x', -75)
      .attr('y', 170)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -75, 170)')
      .text('销售额')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.selectAll('.month-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'month-label')
      .attr('x', (d: any) => xScale(+d.month))
      .attr('y', 365)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d.month}月`)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('text')
      .attr('x', 450)
      .attr('y', 395)
      .attr('text-anchor', 'middle')
      .text('月份')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
  }, [scales, maxValue]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start',
      padding: '60px 40px'
    }}>
      <div style={{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}>
        月度销售额趋势
      </div>
      
      <svg 
        ref={svgRef} 
        width={1100} 
        height={600} 
        style={{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};