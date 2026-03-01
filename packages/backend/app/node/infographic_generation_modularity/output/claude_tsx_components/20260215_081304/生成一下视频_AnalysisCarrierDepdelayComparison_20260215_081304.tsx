import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 生成一下视频_AnalysisCarrierDepdelayComparison_20260215_081304Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  const data = [
    {
      "carrier": "AA",
      "avg_depdelay": 15.41,
      "count": 1880
    },
    {
      "carrier": "EV",
      "avg_depdelay": 16.53,
      "count": 144
    },
    {
      "carrier": "MQ",
      "avg_depdelay": 33.98,
      "count": 56
    },
    {
      "carrier": "OO",
      "avg_depdelay": 25.3,
      "count": 319
    },
    {
      "carrier": "UA",
      "avg_depdelay": 25.24,
      "count": 1358
    }
  ];
  
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "avg_depdelay",
      "label": "平均出发延误 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  
  // Color configuration (CRITICAL: MUST use fixed background colors!)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Scene-specific colors for "延误时间" (delay time) - problem/warning theme
  const textColor = '#e8eaed';
  const barColor = '#f97316'; // Orange for general delays
  const highlightColor = '#ea580c'; // Deeper orange for the highest delay
  const gridColor = '#4a5568';
  const axisColor = '#6b7280';
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  const scales = useMemo(() => {
    const chartWidth = 800; // Inner chart width
    const innerHeight = 400; // Inner chart height (leaving space for titles/subtitles)

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.4); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Add some buffer above max value
      .range([innerHeight, 0]);

    return { xScale, yScale, chartWidth, innerHeight };
  }, [data, xField, yField, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Define chart dimensions
    const margin = { top: 100, right: 80, bottom: 180, left: 80 }; // Adjusted margins for subtitle space
    const { xScale, yScale, chartWidth, innerHeight } = scales;
    
    const defs = svg.append('defs');
    
    // Shadow filter (using feDropShadow to avoid blurring the shape itself)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5))
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Remove y-axis line
    g.select('.y-axis').selectAll('path').attr('stroke', 'none');
    g.select('.y-axis').selectAll('line').attr('stroke', axisColor);

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Positioned further left from the ticks
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${innerHeight / 2})`)
      .text(data_binding.y_axis.label)
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
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => innerHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? highlightColor : barColor)
      .attr('rx', 8)
      .attr('ry', 8)
      .style('filter', 'url(#shadow)');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) // Format to 2 decimal places
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? highlightColor : textColor)
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
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', innerHeight + 20) // Positioned 20px below the chart base
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // X-axis line (optional, but can provide clear separation)
    g.append('line')
      .attr('x1', 0)
      .attr('y1', innerHeight)
      .attr('x2', chartWidth)
      .attr('y2', innerHeight)
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);

  }, [scales, data, xField, yField, maxValue, maxItem, barColor, highlightColor, textColor, gridColor, axisColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to start to manage top space
      padding: '0 40px' // Horizontal padding
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top edge
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均出发延误时间对比
      </div>
      
      {/* Chart container */}
      <svg 
        ref={svgRef} 
        width={1280} // Full canvas width
        height={720} // Full canvas height
        style={{ 
          marginTop: '0px', // Handled by g transform
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};