import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 请基于学生数据制作一个全面的数据分析视频_AnalysisGenderDistribution_20260203_065439Component: React.FC = () => {
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
  const maleColor = '#4A90E2';
  const femaleColor = '#E24A90';
  const highlightColor = '#FFD700';
  
  const processedData = useMemo(() => {
    const total = d3.sum(data, (d: any) => d[valueField]);
    return data.map(d => ({
      ...d,
      displayLabel: d[categoryField] === '男' ? '男生' : '女生',
      percentage: (d[valueField] / total) * 100,
      color: d[categoryField] === '男' ? maleColor : femaleColor
    }));
  }, [data]);
  
  const formatNumber = (num: number) => num.toString();
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const defs = svg.append('defs');
    
    const maleGradient = defs.append('linearGradient')
      .attr('id', 'maleGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    maleGradient.append('stop').attr('offset', '0%').attr('stop-color', '#6BB6FF');
    maleGradient.append('stop').attr('offset', '100%').attr('stop-color', '#4A90E2');
    
    const femaleGradient = defs.append('linearGradient')
      .attr('id', 'femaleGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    femaleGradient.append('stop').attr('offset', '0%').attr('stop-color', '#FF6BB6');
    femaleGradient.append('stop').attr('offset', '100%').attr('stop-color', '#E24A90');
    
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.3);
    
    const legendGroup = svg.append('g')
      .attr('transform', 'translate(100, 140)');
    
    const legendItems = legendGroup.selectAll('.legend-item')
      .data(processedData)
      .enter()
      .append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d: any, i: number) => `translate(0, ${i * 80})`);
    
    legendItems.append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', 24)
      .attr('height', 24)
      .attr('rx', 4)
      .attr('fill', (d: any) => d[categoryField] === '男' ? 'url(#maleGradient)' : 'url(#femaleGradient)')
      .style('filter', 'url(#shadow)');
    
    legendItems.append('text')
      .attr('class', 'legend-label')
      .attr('x', 40)
      .attr('y', 18)
      .text((d: any) => d.displayLabel)
      .attr('fill', textColor)
      .style('font-size', '20px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    legendItems.append('text')
      .attr('class', 'legend-metrics')
      .attr('x', 40)
      .attr('y', 45)
      .text((d: any) => `${formatNumber(d[valueField])}人 (${d.percentage.toFixed(1)}%)`)
      .attr('fill', '#b0b3b8')
      .style('font-size', '16px')
      .style('font-weight', '400')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    const pieGroup = svg.append('g')
      .attr('transform', 'translate(640, 280)');
    
    const radius = 160;
    const pie = d3.pie<any>()
      .value((d: any) => d[valueField])
      .sort(null);
    
    const arc = d3.arc<any>()
      .innerRadius(0)
      .outerRadius(radius);
    
    const highlightArc = d3.arc<any>()
      .innerRadius(0)
      .outerRadius(radius + 8);
    
    const pieData = pie(processedData);
    
    const slices = pieGroup.selectAll('.slice')
      .data(pieData)
      .enter()
      .append('g')
      .attr('class', 'slice');
    
    slices.append('path')
      .attr('d', (d: any) => d.data[valueField] === Math.max(...processedData.map(item => item[valueField])) ? highlightArc(d) : arc(d))
      .attr('fill', (d: any) => d.data[categoryField] === '男' ? 'url(#maleGradient)' : 'url(#femaleGradient)')
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 3)
      .style('filter', 'url(#shadow)');
    
    slices.append('text')
      .attr('transform', (d: any) => `translate(${arc.centroid(d)})`)
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d.data.percentage.toFixed(1)}%`)
      .attr('fill', '#ffffff')
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('text-shadow', '0 2px 4px rgba(0,0,0,0.5)');
    
    const totalCount = d3.sum(processedData, (d: any) => d[valueField]);
    pieGroup.append('text')
      .attr('x', 0)
      .attr('y', radius + 50)
      .attr('text-anchor', 'middle')
      .text(`总计: ${totalCount}人`)
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', '600')
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
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        性别分布统计
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