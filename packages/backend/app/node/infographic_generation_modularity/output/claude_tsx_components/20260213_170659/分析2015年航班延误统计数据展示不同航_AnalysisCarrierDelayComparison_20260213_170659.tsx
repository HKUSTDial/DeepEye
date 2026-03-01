import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析2015年航班延误统计数据展示不同航_AnalysisCarrierDelayComparison_20260213_170659Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  const data = [
    {
      "carrier": "AA",
      "avg_depdelay": 19.14,
      "avg_arrdelay": 10.79,
      "count": 58
    },
    {
      "carrier": "EV",
      "avg_depdelay": 0.0,
      "avg_arrdelay": -11.67,
      "count": 3
    },
    {
      "carrier": "MQ",
      "avg_depdelay": 8.0,
      "avg_arrdelay": 2.33,
      "count": 3
    },
    {
      "carrier": "OO",
      "avg_depdelay": 33.43,
      "avg_arrdelay": 30.14,
      "count": 7
    },
    {
      "carrier": "UA",
      "avg_depdelay": 9.31,
      "avg_arrdelay": -11.66,
      "count": 29
    }
  ];
  
  const xField = 'carrier';
  const yAxisFields = [
    { field: 'avg_depdelay', label: '平均起飞延误(分钟)' },
    { field: 'avg_arrdelay', label: '平均到达延误(分钟)' }
  ];
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const barColors = ['#ef4444', '#f97316'];
  const highlightColor = '#fbbf24';
  const gridColor = '#2a2a2a';
  const axisColor = '#666666';
  
  const maxValue = useMemo(() => {
    return Math.max(
      d3.max(data, (d: any) => d.avg_depdelay) || 0,
      d3.max(data, (d: any) => d.avg_arrdelay) || 0
    );
  }, [data]);
  
  const minValue = useMemo(() => {
    return Math.min(
      d3.min(data, (d: any) => d.avg_depdelay) || 0,
      d3.min(data, (d: any) => d.avg_arrdelay) || 0
    );
  }, [data]);
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.3);
    
    const xSubgroup = d3.scaleBand()
      .domain(yAxisFields.map(y => y.field))
      .range([0, xScale.bandwidth()])
      .padding(0.1);
    
    const yScale = d3.scaleLinear()
      .domain([minValue - 5, maxValue + 5])
      .range([320, 0]);
    
    return { xScale, yScale, xSubgroup };
  }, [data, maxValue, minValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const redGradient = defs.append('linearGradient')
      .attr('id', 'redGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    redGradient.append('stop').attr('offset', '0%').attr('stop-color', '#ef4444');
    redGradient.append('stop').attr('offset', '100%').attr('stop-color', '#dc2626');
    
    const orangeGradient = defs.append('linearGradient')
      .attr('id', 'orangeGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    orangeGradient.append('stop').attr('offset', '0%').attr('stop-color', '#f97316');
    orangeGradient.append('stop').attr('offset', '100%').attr('stop-color', '#ea580c');
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 3)
      .attr('stdDeviation', 4)
      .attr('flood-opacity', 0.25);
    
    const g = svg.append('g').attr('transform', 'translate(80, 80)');
    const {xScale, yScale, xSubgroup} = scales;
    
    const yAxis = d3.axisLeft(yScale)
      .ticks(6)
      .tickFormat((d: any) => `${d}分钟`);
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis);
    
    g.selectAll('.y-axis line, .y-axis path')
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);
    
    g.selectAll('.y-axis text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.selectAll('.grid-y')
      .data(yScale.ticks(6))
      .enter()
      .append('line')
      .attr('class', 'grid-y')
      .attr('x1', 0)
      .attr('x2', 800)
      .attr('y1', (d: any) => yScale(d))
      .attr('y2', (d: any) => yScale(d))
      .attr('stroke', gridColor)
      .attr('stroke-width', 0.5)
      .attr('opacity', 0.3);
    
    yAxisFields.forEach((yAxisConfig, i) => {
      const yField = yAxisConfig.field;
      const barColor = i === 0 ? 'url(#redGradient)' : 'url(#orangeGradient)';
      
      g.selectAll(`.bar-${yField}`)
        .data(data)
        .enter()
        .append('rect')
        .attr('class', `bar-${yField}`)
        .attr('x', (d: any) => (xScale(d[xField]) || 0) + xSubgroup(yField))
        .attr('y', (d: any) => d[yField] >= 0 ? yScale(d[yField]) : yScale(0))
        .attr('width', xSubgroup.bandwidth())
        .attr('height', (d: any) => Math.abs(yScale(d[yField]) - yScale(0)))
        .attr('fill', barColor)
        .attr('rx', 4)
        .style('filter', 'url(#shadow)');
      
      g.selectAll(`.value-label-${yField}`)
        .data(data)
        .enter()
        .append('text')
        .attr('class', `value-label-${yField}`)
        .attr('x', (d: any) => (xScale(d[xField]) || 0) + xSubgroup(yField) + xSubgroup.bandwidth() / 2)
        .attr('y', (d: any) => d[yField] >= 0 ? yScale(d[yField]) - 8 : yScale(0) + 20)
        .attr('text-anchor', 'middle')
        .text((d: any) => d[yField].toFixed(1))
        .attr('fill', textColor)
        .style('font-size', '13px')
        .style('font-weight', '600')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });
    
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    const legend = g.append('g')
      .attr('transform', 'translate(600, 20)');
    
    yAxisFields.forEach((yAxisConfig, i) => {
      const legendItem = legend.append('g')
        .attr('transform', `translate(0, ${i * 30})`);
      
      legendItem.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', 18)
        .attr('height', 18)
        .attr('fill', i === 0 ? barColors[0] : barColors[1])
        .attr('rx', 3);
      
      legendItem.append('text')
        .attr('x', 25)
        .attr('y', 14)
        .text(yAxisConfig.label)
        .attr('fill', textColor)
        .style('font-size', '14px')
        .style('font-weight', '500')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });
    
    g.append('line')
      .attr('x1', 0)
      .attr('x2', 800)
      .attr('y1', yScale(0))
      .attr('y2', yScale(0))
      .attr('stroke', '#666666')
      .attr('stroke-width', 2);
    
  }, [scales, data]);
  
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
        fontSize: '32px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        各航空公司平均起飞延误与到达延误对比
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
    </AbsoluteFill>
  );
};