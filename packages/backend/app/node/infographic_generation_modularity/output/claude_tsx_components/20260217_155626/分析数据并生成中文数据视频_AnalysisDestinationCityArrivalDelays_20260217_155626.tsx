import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_AnalysisDestinationCityArrivalDelays_20260217_155626Component: React.FC = () => {
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
  const yLabel = "平均到达延误 (分钟)";
  
  // Color configuration
  const backgroundColor = '#0f1419'; // MUST use JSON config value
  const containerBackground = '#0f1419'; // MUST use JSON config value
  
  // Scene-specific colors based on "Delays related" semantics
  const textColor = '#e8eaed';
  const barColor = '#f97316'; // Orange for general delays
  const highlightColor = '#dc2626'; // Red for highest delay (Minneapolis)
  const gridColor = '#333333'; // Darker grid for subtle presence
  const axisColor = '#888888'; // Grey for axis lines and ticks
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions
  const canvasWidth = 1280;
  const canvasHeight = 720;
  
  // Margins for the chart within the SVG container
  const chartMargin = { top: 40, right: 40, bottom: 40, left: 80 };
  const chartWidth = 900; // Inner chart width for bars
  const chartHeight = 300; // Inner chart height for bars (y-axis range)

  // Total SVG dimensions, considering inner chart and margins, plus space for labels
  const svgWidth = chartWidth + chartMargin.left + chartMargin.right; // 900 + 80 + 40 = 1020
  const svgHeight = chartHeight + chartMargin.top + chartMargin.bottom + 80; // 300 + 40 + 40 + 40 (for x-tick labels) + 40 (for x-axis label) = 460
                                                                            // Total height from SVG top: 460.
                                                                            // SVG top position: 100.
                                                                            // SVG bottom position: 100 + 460 = 560.
                                                                            // Canvas bottom: 720. 720 - 560 = 160px remaining.
                                                                            // This is safe, as we need to reserve 180px for subtitles,
                                                                            // and 160px for subtitle line + 20px padding is acceptable.
                                                                            // Let's adjust SVG height slightly to make bottom safe zone 180px.
                                                                            // If SVG top is 100, then SVG must end at y=540 (720-180).
                                                                            // So, SVG height must be 440 (540-100).
  const finalSvgHeight = 440; // Adjusted for 180px subtitle zone
  const svgTop = 100; // Position SVG 100px from top of canvas
  const svgLeft = (canvasWidth - svgWidth) / 2; // Center SVG horizontally

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding slightly for cleaner look
    
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Extend domain slightly above max value
      .range([chartHeight, 0]);
      
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField, yField]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // SVG Clarity Optimization
    svg.attr('shape-rendering', 'geometricPrecision')
       .attr('text-rendering', 'geometricPrecision');
    
    const defs = svg.append('defs');
    
    // Gradient for the highest bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8) || highlightColor);
    
    // Shadow filter (feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'bar-shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-color', 'rgba(0,0,0,0.4)');
    
    // Main chart group
    const g = svg.append('g')
      .attr('transform', `translate(${chartMargin.left}, ${chartMargin.top})`);
    
    const { xScale, yScale } = scales;
    
    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => '')
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.5);

    // Y-axis
    const yAxis = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `${d}min`))
      .attr('font-size', '14px');

    yAxis.selectAll('path').attr('stroke', axisColor);
    yAxis.selectAll('line').attr('stroke', axisColor);
    yAxis.selectAll('text')
      .attr('fill', textColor)
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('x', -chartMargin.left + 15) // Adjust to left of tick marks
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-chartMargin.left + 15}, ${chartHeight / 2})`)
      .text(yLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
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
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 6) // Rounded corners for bars
      .style('filter', 'url(#bar-shadow)');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2))
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '20px' : '18px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? 'bold' : 'normal')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels (X-axis tick labels)
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 25) // Position below bars, within SVG height
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis label (目的地城市)
    g.append('text')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 60) // Position below category labels
      .attr('text-anchor', 'middle')
      .text(xField) // Label "目的地城市"
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, data, maxValue, xField, yField, yLabel, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight, chartMargin]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to place title and then chart
      padding: '0px 0px' // Remove padding from AbsoluteFill to control positioning precisely
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top of canvas, leaving ~70px buffer for subtitle overlay
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
      }}>
        目的地城市平均到达延误分布
      </div>
      
      {/* Chart container */}
      <svg 
        ref={svgRef} 
        width={svgWidth} 
        height={finalSvgHeight} // Use adjusted height
        style={{ 
          position: 'absolute',
          top: svgTop, // 100px from top of canvas
          left: svgLeft, // Horizontally centered
        }} 
      />
    </AbsoluteFill>
  );
};