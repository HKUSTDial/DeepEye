import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 学生数据视频分析展示学生的年龄性别年级分_AnalysisGradeDistribution_20260203_072836Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  const data = [
    {
      "grade": 10,
      "count_grade": 10,
      "count": 10
    },
    {
      "grade": 11,
      "count_grade": 5,
      "count": 5
    },
    {
      "grade": 12,
      "count_grade": 5,
      "count": 5
    }
  ];
  
  const xField = 'grade';
  const yField = 'count';
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const barColor = '#4ade80';
  const highlightColor = '#22c55e';
  const gridColor = '#374151';
  const axisColor = '#6b7280';
  
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 600])
      .padding(0.3);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2])
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
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#6ee7b7');
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', '#86efac');
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.2);
    
    const g = svg.append('g').attr('transform', 'translate(180, 80)');
    const {xScale, yScale} = scales;
    
    g.selectAll('.grid-line')
      .data(yScale.ticks(5))
      .enter()
      .append('line')
      .attr('class', 'grid-line')
      .attr('x1', 0)
      .attr('x2', 600)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 1)
      .attr('opacity', 0.3);
    
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
      .attr('rx', 12)
      .attr('ry', 12)
      .style('filter', 'url(#shadow)')
      .attr('stroke', (d: any) => d[yField] === maxValue ? highlightColor : 'none')
      .attr('stroke-width', (d: any) => d[yField] === maxValue ? 3 : 0);
    
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 20)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField]}人`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '24px' : '18px')
      .style('font-weight', '700')
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
      .text((d: any) => `${d[xField]}年级`)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.append('text')
      .attr('x', -70)
      .attr('y', 160)
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90, -70, 160)')
      .text('学生人数')
      .attr('fill', axisColor)
      .style('font-size', '14px')
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
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        各年级学生人数分布
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
    </AbsoluteFill>
  );
};