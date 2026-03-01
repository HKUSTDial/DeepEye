import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析2015年航班延误统计数据展示不同航_AnalysisCarrierPassengerVolume_20260213_170659Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  const data = [
    {
      "carrier": "AA",
      "sum_passengers": 7446,
      "count": 58
    },
    {
      "carrier": "EV",
      "sum_passengers": 214,
      "count": 3
    },
    {
      "carrier": "MQ",
      "sum_passengers": 184,
      "count": 3
    },
    {
      "carrier": "OO",
      "sum_passengers": 625,
      "count": 7
    },
    {
      "carrier": "UA",
      "sum_passengers": 4894,
      "count": 29
    }
  ];
  
  const xField = 'carrier';
  const yField = 'sum_passengers';
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const barColor = '#3b82f6';
  const highlightColor = '#60a5fa';
  const gridColor = '#374151';
  const axisColor = '#6b7280';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.3);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([320, 0]);
    return { xScale, yScale };
  }, [data, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const gradient = defs.append('linearGradient')
      .attr('id', 'barGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#60a5fa');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#3b82f6');
    
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', '#fbbf24');
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', '#f59e0b');
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.25);
    
    const g = svg.append('g').attr('transform', 'translate(80, 80)');
    const {xScale, yScale} = scales;
    
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => 320 - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : 'url(#barGradient)')
      .attr('rx', 6)
      .style('filter', 'url(#shadow)');
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toLocaleString())
      .attr('fill', (d: any) => d[yField] === maxValue ? '#fbbf24' : textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
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
      .style('font-size', '18px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('text')
      .attr('x', 400)
      .attr('y', 380)
      .attr('text-anchor', 'middle')
      .text('航空公司')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('text')
      .attr('x', -60)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -60, 160)')
      .text('乘客总数')
      .attr('fill', axisColor)
      .style('font-size', '14px')
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
      padding: '40px'
    }}>
      <div style={{
        position: 'absolute',
        top: 25,
        fontSize: '32px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        各航空公司乘客总量对比
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
    </AbsoluteFill>
  );
};