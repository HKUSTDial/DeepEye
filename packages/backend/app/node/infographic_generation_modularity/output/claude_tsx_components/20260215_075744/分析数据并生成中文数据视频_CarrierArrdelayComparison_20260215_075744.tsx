import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_CarrierArrdelayComparison_20260215_075744Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "avg_arrdelay": 9.48,
    "count": 1880
  },
  {
    "carrier": "EV",
    "avg_arrdelay": 12.76,
    "count": 144
  },
  {
    "carrier": "MQ",
    "avg_arrdelay": 38.98,
    "count": 56
  },
  {
    "carrier": "OO",
    "avg_arrdelay": 26.06,
    "count": 319
  },
  {
    "carrier": "UA",
    "avg_arrdelay": 15.6,
    "count": 1358
  }
];
  
  // Data binding configuration
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均抵达延误时间 (分钟)"
    }
  };

  const xField = data_binding.x_axis?.field || 'carrier';
  const yField = (data_binding.y_axis as {field: string}).field || 'avg_arrdelay';
  const yLabel = (data_binding.y_axis as {label: string}).label || 'Value';
  
  // Color configuration (CRITICAL: Background colors are fixed!)
  const backgroundColor = '#0f1419'; // MUST use this exact value
  const containerBackground = '#0f1419'; // MUST use this exact value
  
  // Scene-specific theme colors for 'delays'
  const textColor = '#e8eaed'; 
  const barColor = '#f97316'; // Vibrant orange for delays
  const highlightColor = '#dc2626'; // More intense red for longest delay
  const gridColor = '#3a3a3a'; // Subtle grey for grid lines
  const axisColor = '#888888'; // Subtle grey for axis lines
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions and margins
  const width = 1000;
  const height = 400; // Chart drawing area height (max y-axis value to x-axis)
  const margin = { top: 100, right: 60, bottom: 180, left: 80 }; // Bottom 180px for subtitles
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15]) // Extend domain slightly above max for label space
      .range([innerHeight, 0]); // Invert range for SVG coordinates
      
    return { xScale, yScale };
  }, [data, xField, maxValue, innerWidth, innerHeight]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear SVG contents

    // Add SVG clarity optimizations
    svg.attr('shape-rendering', 'geometricPrecision')
       .attr('text-rendering', 'geometricPrecision');
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Gradient for the highlight bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); 
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor); 
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.4);
    
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    const { xScale, yScale } = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => "")
        .ticks(5)
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `${d} min`))
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 10) // Positioned to the left of the axis
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 10}, ${innerHeight / 2})`)
      .text(yLabel)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Draw bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => innerHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 6) // Rounded corners for aesthetics
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#barShadow)' : 'none');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Position slightly above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(2)}`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart (X-axis labels)
    // CRITICAL: y position must be <= 370 for 720px canvas, leaving 180px for subtitle zone.
    // innerHeight + 40 ensures it's below the bars but within the safe zone.
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', innerHeight + 40) // Position below the chart area (innerHeight is the bottom of the chart)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[xField] === maxItem?.[xField] ? 'bold' : 'normal')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, data, xField, yField, maxValue, maxItem, barColor, highlightColor, textColor, gridColor, axisColor, innerWidth, innerHeight, margin.left, margin.top]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to control padding more precisely
      paddingTop: '60px', // Reserve space for title + top padding
      paddingBottom: '180px' // CRITICAL: Reserve bottom 180px for subtitles
    }}>
      {/* Title - positioned at the top, allowing for subtitle overlay */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top edge
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        zIndex: 10,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均抵达延误时间对比
      </div>
      
      {/* Chart - positioned below the title, within the safe zone */}
      <svg 
        ref={svgRef} 
        width={width} 
        height={height} 
        style={{ 
          marginTop: '20px', // Space between title and chart
          overflow: 'visible' // Allow elements like shadows to extend beyond svg boundaries
        }} 
      />
      
    </AbsoluteFill>
  );
};