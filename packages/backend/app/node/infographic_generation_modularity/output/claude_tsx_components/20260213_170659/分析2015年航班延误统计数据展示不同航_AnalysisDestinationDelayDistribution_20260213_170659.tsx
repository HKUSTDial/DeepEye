import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析2015年航班延误统计数据展示不同航_AnalysisDestinationDelayDistribution_20260213_170659Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  const data = [
    {
      "destcity": "Boston",
      "avg_depdelay": 6.67,
      "avg_arrdelay": -8.08,
      "count": 12
    },
    {
      "destcity": "Dallas",
      "avg_depdelay": 40.62,
      "avg_arrdelay": 47.44,
      "count": 16
    },
    {
      "destcity": "Los Angeles",
      "avg_depdelay": 1.62,
      "avg_arrdelay": -14.31,
      "count": 16
    },
    {
      "destcity": "Minneapolis",
      "avg_depdelay": 55.8,
      "avg_arrdelay": 51.1,
      "count": 10
    },
    {
      "destcity": "New York",
      "avg_depdelay": 7.68,
      "avg_arrdelay": -7.47,
      "count": 19
    },
    {
      "destcity": "San Francisco",
      "avg_depdelay": 10.23,
      "avg_arrdelay": -15.69,
      "count": 13
    },
    {
      "destcity": "Washington",
      "avg_depdelay": 3.21,
      "avg_arrdelay": -9.07,
      "count": 14
    }
  ];
  
  const xField = 'destcity';
  const yAxisFields = [
    { field: 'avg_depdelay', label: '平均起飞延误(分钟)' },
    { field: 'avg_arrdelay', label: '平均到达延误(分钟)' }
  ];
  
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  const textColor = '#e8eaed';
  const depDelayColor = '#ef4444';
  const arrDelayColor = '#f97316';
  const highlightColor = '#fbbf24';
  const gridColor = '#2a2a2a';
  const axisColor = '#666666';
  
  const maxDepDelay = d3.max(data, (d: any) => d.avg_depdelay) || 0;
  const minArrDelay = d3.min(data, (d: any) => d.avg_arrdelay) || 0;
  const maxValue = Math.max(maxDepDelay, Math.abs(minArrDelay));
  const minneapolisData = data.find(d => d.destcity === 'Minneapolis');
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 800])
      .padding(0.3);
    
    const subGroups = yAxisFields.map(y => y.field);
    const xSubgroup = d3.scaleBand()
      .domain(subGroups)
      .range([0, xScale.bandwidth()])
      .padding(0.1);
    
    const yScale = d3.scaleLinear()
      .domain([minArrDelay * 1.2, maxDepDelay * 1.2])
      .range([320, 0]);
    
    return { xScale, yScale, xSubgroup };
  }, [data, maxDepDelay, minArrDelay]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const depGradient = defs.append('linearGradient')
      .attr('id', 'depGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    depGradient.append('stop').attr('offset', '0%').attr('stop-color', '#fca5a5');
    depGradient.append('stop').attr('offset', '100%').attr('stop-color', depDelayColor);
    
    const arrGradient = defs.append('linearGradient')
      .attr('id', 'arrGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    arrGradient.append('stop').attr('offset', '0%').attr('stop-color', '#fed7aa');
    arrGradient.append('stop').attr('offset', '100%').attr('stop-color', arrDelayColor);
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 3)
      .attr('stdDeviation', 4)
      .attr('flood-opacity', 0.25);
    
    const g = svg.append('g').attr('transform', 'translate(80, 80)');
    const {xScale, yScale, xSubgroup} = scales;
    
    g.append('line')
      .attr('x1', 0)
      .attr('x2', 800)
      .attr('y1', yScale(0))
      .attr('y2', yScale(0))
      .attr('stroke', gridColor)
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '5,5');
    
    yAxisFields.forEach((yAxisConfig, i) => {
      const yField = yAxisConfig.field;
      const barColor = i === 0 ? 'url(#depGradient)' : 'url(#arrGradient)';
      
      g.selectAll(`.bar-${yField}`)
        .data(data)
        .enter()
        .append('rect')
        .attr('class', `bar-${yField}`)
        .attr('x', (d: any) => (xScale(d[xField]) || 0) + xSubgroup(yField))
        .attr('y', (d: any) => d[yField] >= 0 ? yScale(d[yField]) : yScale(0))
        .attr('width', xSubgroup.bandwidth())
        .attr('height', (d: any) => Math.abs(yScale(d[yField]) - yScale(0)))
        .attr('fill', (d: any) => d.destcity === 'Minneapolis' ? highlightColor : barColor)
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
        .attr('fill', (d: any) => d.destcity === 'Minneapolis' ? '#fbbf24' : textColor)
        .style('font-size', '13px')
        .style('font-weight', '600')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });
    
    g.selectAll('.city-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 350)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', (d: any) => d.destcity === 'Minneapolis' ? highlightColor : textColor)
      .style('font-size', '14px')
      .style('font-weight', (d: any) => d.destcity === 'Minneapolis' ? '700' : '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    const legend = g.append('g')
      .attr('transform', 'translate(580, 30)');
    
    yAxisFields.forEach((yAxisConfig, i) => {
      const legendColor = i === 0 ? depDelayColor : arrDelayColor;
      
      legend.append('rect')
        .attr('x', 0)
        .attr('y', i * 30)
        .attr('width', 18)
        .attr('height', 18)
        .attr('fill', legendColor)
        .attr('rx', 3);
      
      legend.append('text')
        .attr('x', 25)
        .attr('y', i * 30 + 14)
        .text(yAxisConfig.label)
        .attr('fill', textColor)
        .style('font-size', '14px')
        .style('font-weight', '500')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });
    
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
        fontSize: '34px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        各城市平均起飞延误与到达延误对比
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