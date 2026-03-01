import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 学生数据视频分析展示学生的年龄性别年级分_AnalysisGenderDistribution_20260203_072836Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
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
      .attr('d', (d: any) => {
        const maxValue = d3.max(processedData, (item: any) => item[valueField]);
        return d.data[valueField] === maxValue ? highlightArc(d) : arc(d);
      })
      .attr('fill', (d: any, i: number) => {
        return i === 0 ? 'url(#maleGradient)' : 'url(#femaleGradient)';
      })
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 3)
      .style('filter', 'url(#shadow)');
    
    slices.append('text')
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
      .style('text-rendering', 'geometricPrecision');
    
    const legendItems = legendGroup.selectAll('.legend-item')
      .data(processedData)
      .enter()
      .append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d: any, i: number) => `translate(0, ${i * 60})`);
    
    legendItems.append('circle')
      .attr('cx', 15)
      .attr('cy', 15)
      .attr('r', 15)
      .attr('fill', (d: any, i: number) => i === 0 ? primaryColor : secondaryColor)
      .style('filter', 'url(#shadow)');
    
    legendItems.append('text')
      .attr('x', 50)
      .attr('y', 12)
      .text((d: any) => d.displayLabel)
      .attr('fill', textColor)
      .style('font-size', '24px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    legendItems.append('text')
      .attr('x', 50)
      .attr('y', 35)
      .text((d: any) => `${d[valueField]}人 (${d.percentage.toFixed(1)}%)`)
      .attr('fill', (d: any, i: number) => i === 0 ? primaryColor : secondaryColor)
      .style('font-size', '18px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    const totalStudents = d3.sum(processedData, (d: any) => d[valueField]);
    pieGroup.append('text')
      .attr('x', 0)
      .attr('y', 200)
      .attr('text-anchor', 'middle')
      .text(`总计: ${totalStudents}人`)
      .attr('fill', highlightColor)
      .style('font-size', '20px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
  }, [processedData]);
  
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
    </AbsoluteFill>
  );
};