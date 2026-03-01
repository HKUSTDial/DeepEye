import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 生成一个数据视频_AnalysisDestcityArrivalDelays_20260215_064204Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "destcity": "Boston",
    "avg_arrdelay": 12.52,
    "count": 385
  },
  {
    "destcity": "Dallas",
    "avg_arrdelay": 15.78,
    "count": 608
  },
  {
    "destcity": "Los Angeles",
    "avg_arrdelay": 5.13,
    "count": 514
  },
  {
    "destcity": "Minneapolis",
    "avg_arrdelay": 19.58,
    "count": 439
  },
  {
    "destcity": "New York",
    "avg_arrdelay": 15.04,
    "count": 769
  },
  {
    "destcity": "San Francisco",
    "avg_arrdelay": 13.05,
    "count": 459
  },
  {
    "destcity": "Washington",
    "avg_arrdelay": 13.95,
    "count": 583
  }
];
  
  // Data binding
  const xField = "destcity";
  const yField = "avg_arrdelay";
  const yLabel = "平均抵达延误（分钟）";

  // Color configuration
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  const textColor = '#e8eaed'; 
  const barColor = '#f97316'; // Orange-red for "delays"
  const highlightColor = '#ef4444'; // Brighter red for max delay
  const gridColor = '#555555'; 
  const axisColor = '#888888'; 
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // D3 scales
  const margin = { top: 100, right: 60, bottom: 180, left: 80 }; // Adjusted for subtitle zone
  const chartWidth = 1280 - margin.left - margin.right;
  const chartHeight = 720 - margin.top - margin.bottom; // Actual drawing area for bars

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Give some room above max bar
      .range([chartHeight, 0]); // In SVG, 0 is top, chartHeight is bottom
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight]);
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create gradient for highlight (max value)
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); 
    gradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8).toString() || highlightColor); 
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Draw chart with proper spacing to avoid label overlap
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    const {xScale, yScale} = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
        .ticks(5))
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '4 4');

    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d: any) => `${d} min`);
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Position left of chart area, adjusted
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${chartHeight / 2})`)
      .text(yLabel)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Draw bars (highlight max value with accent color)
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for bars
      .attr('ry', 8)
      .style('filter', 'url(#shadow)');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Position above bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(2)} min`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart (X-axis labels)
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 20) // Position below bars, above bottom margin
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, maxItem, chartWidth, chartHeight, margin, barColor, highlightColor, textColor, gridColor, axisColor, xField, yField, yLabel]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top, leaving space for subtitle at 80px
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        按目的地城市划分的平均抵达延误
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={1280} 
        height={720} 
        style={{ 
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
      
    </AbsoluteFill>
  );
};