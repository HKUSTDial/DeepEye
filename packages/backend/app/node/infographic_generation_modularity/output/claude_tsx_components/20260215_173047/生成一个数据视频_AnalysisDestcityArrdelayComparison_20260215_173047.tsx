import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 生成一个数据视频_AnalysisDestcityArrdelayComparison_20260215_173047Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
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
  
  const data_binding = {
    "x_axis": {
      "field": "destcity",
      "label": "目的地城市"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均抵达延误 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  
  // CRITICAL: Background colors from JSON config - DO NOT change them!
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Scene-specific colors based on "Delays" semantic
  const textColor = '#e8eaed';
  const barColor = '#f97316'; // Orange-500 for general bars (delays)
  const highlightColor = '#dc2626'; // Red-600 for max delay
  const gridColor = '#374151'; // Darker gray for subtle grid
  const axisColor = '#6b7280'; // Medium gray for axes

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions and margins
  const width = 1100; // Total SVG width
  const height = 580; // Total SVG height (actual chart content fits in a smaller area)
  const margin = { top: 100, right: 60, bottom: 200, left: 100 }; // Adjusted for subtitle safety
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom; // Actual drawing height for bars

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerWidth])
      .padding(0.3); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([innerHeight, 0]); // Inverted for SVG coordinates

    return { xScale, yScale };
  }, [data, xField, maxValue, innerWidth, innerHeight]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Define gradients and shadow
    const defs = svg.append('defs');
    
    // Gradient for highlighted bar
    const gradientId = 'highlightGradient';
    const gradient = defs.append('linearGradient')
      .attr('id', gradientId)
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8).formatHex());
    
    // Drop shadow filter (CRITICAL: use feDropShadow to avoid blurring the element itself)
    const shadowId = 'barShadow';
    const shadow = defs.append('filter').attr('id', shadowId);
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 5)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.4);
    
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    const { xScale, yScale } = scales;
    
    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,4');

    // Bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => innerHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? `url(#${gradientId})` : barColor)
      .attr('rx', 6) // Rounded corners
      .attr('ry', 6)
      .style('filter', (d: any) => d[yField] === maxValue ? `url(#${shadowId})` : 'none');

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2) + ' min')
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? '700' : 'normal')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis (category labels)
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${innerHeight})`)
      .call(d3.axisBottom(xScale).tickSizeOuter(0))
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .attr('y', 10); // Adjust position slightly below the axis line

    // X-axis line (remove default d3 line if present, replace with subtle one)
    g.select('.x-axis').select('.domain').attr('stroke', axisColor).attr('stroke-width', 0.5);
    g.select('.x-axis').selectAll('.tick line').remove(); // Remove default tick lines

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `${d} min`))
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis line (remove default d3 line if present, replace with subtle one)
    g.select('.y-axis').select('.domain').attr('stroke', axisColor).attr('stroke-width', 0.5);
    g.select('.y-axis').selectAll('.tick line').attr('stroke', axisColor).attr('stroke-width', 0.5);

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', innerWidth / 2)
      .attr('y', innerHeight + 60) // Position below x-axis ticks, well above subtitle zone
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // CRITICAL: Position far left to avoid overlap with tick numbers
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${innerHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, data, xField, yField, maxValue, innerWidth, innerHeight, barColor, highlightColor, textColor, gridColor, axisColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
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
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision',
      }}>
        按目的地城市划分的平均抵达延误
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={width} 
        height={height} 
        style={{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};