import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 展示月度销售趋势生成包含动态图表的数据视_AnalysisMonthlySalesTrend_20260212_101834Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  const data = [
    {
      "month": "1",
      "sum_sales": 1200,
      "count": 1
    },
    {
      "month": "2",
      "sum_sales": 1500,
      "count": 1
    },
    {
      "month": "3",
      "sum_sales": 1800,
      "count": 1
    },
    {
      "month": "4",
      "sum_sales": 2000,
      "count": 1
    }
  ];
  
  const xField = 'month';
  const yField = 'sum_sales';
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const lineColor = '#10b981';
  const highlightColor = '#34d399';
  const gridColor = '#2d3748';
  const axisColor = '#718096';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const xScale = d3.scaleLinear()
      .domain([1, 4])
      .range([0, 700]);
    const yScale = d3.scaleLinear()
      .domain([minValue * 0.9, maxValue * 1.1])
      .range([300, 0]);
    return { xScale, yScale };
  }, [data, maxValue, minValue]);
  
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
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    const g = svg.append('g').attr('transform', 'translate(100, 80)');
    const {xScale, yScale} = scales;
    
    // Grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .selectAll('line')
      .data(yScale.ticks(5))
      .enter()
      .append('line')
      .attr('x1', 0)
      .attr('x2', 700)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .attr('opacity', 0.3);
    
    // Line path
    const line = d3.line()
      .x((d: any) => xScale(+d[xField]))
      .y((d: any) => yScale(d[yField]))
      .curve(d3.curveMonotoneX);
    
    g.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', 'url(#lineGradient)')
      .attr('stroke-width', 4)
      .attr('d', line)
      .style('filter', 'url(#shadow)');
    
    // Data points
    g.selectAll('.dot')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'dot')
      .attr('cx', (d: any) => xScale(+d[xField]))
      .attr('cy', (d: any) => yScale(d[yField]))
      .attr('r', (d: any) => d[yField] === maxValue ? 8 : 6)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : lineColor)
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 2)
      .style('filter', 'url(#shadow)');
    
    // Value labels
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => xScale(+d[xField]))
      .attr('y', (d: any) => yScale(d[yField]) - 20)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField])
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Y-axis
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
    
    // X-axis
    const xAxis = d3.axisBottom(xScale)
      .ticks(4)
      .tickFormat((d: any) => `${d}月`);
    
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', 'translate(0, 300)')
      .call(xAxis)
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Axis styling
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);
    g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor);
    
    // Axis labels
    g.append('text')
      .attr('x', -70)
      .attr('y', 150)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 150)')
      .text('销售额')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('text')
      .attr('x', 350)
      .attr('y', 340)
      .attr('text-anchor', 'middle')
      .text('月份')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
  }, [scales, maxValue]);
  
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
        月度销售趋势
      </div>
      
      <svg 
        ref={svgRef} 
        width={900} 
        height={480} 
        style={{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};