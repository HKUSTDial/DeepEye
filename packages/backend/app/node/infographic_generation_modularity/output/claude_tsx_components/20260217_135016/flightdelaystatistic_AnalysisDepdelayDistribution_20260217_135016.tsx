import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const flightdelaystatistic_AnalysisDepdelayDistribution_20260217_135016Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
    { "delay_range": "<-15分钟", "count": 0 },
    { "delay_range": "-15至-5分钟", "count": 5 },
    { "delay_range": "-5至0分钟", "count": 14 },
    { "delay_range": "0至15分钟", "count": 5 },
    { "delay_range": "15至30分钟", "count": 1 },
    { "delay_range": "30至60分钟", "count": 0 },
    { "delay_range": "60至120分钟", "count": 3 },
    { "delay_range": ">120分钟", "count": 2 }
  ];
  
  const xField = "delay_range";
  const yField = "count";
  
  // Color configuration - CRITICAL: Background colors are fixed per JSON config
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; // Not directly used in AbsoluteFill, but kept for consistency

  // Scene-specific colors based on "Delays/Problems" semantics
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f59e0b'; // Muted orange for general delays
  const highlightColor = '#ef4444'; // Red for significant delays (accent)
  const gridColor = '#333333'; // Subtle grey for grid lines
  const axisColor = '#888888'; // Lighter grey for axis lines and labels
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // D3 scales and chart dimensions
  const chartWidth = 1000; // Inner width of the chart area
  const chartHeight = 280; // Inner height of the chart area, adjusted to leave space for subtitles
                             // (Absolute Y of chart bottom is 120 + 280 = 400. X-axis label is at 440,
                             // which is well above the 540px limit for bottom 180px subtitle zone)

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding for cleaner bar separation

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Add 20% padding above max value for labels
      .range([chartHeight, 0]); // Invert range for SVG coordinates (0 at top)
      
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    // Apply SVG clarity optimizations
    svg.attr('shape-rendering', 'geometricPrecision')
       .attr('text-rendering', 'geometricPrecision');
    
    const defs = svg.append('defs');
    
    // Gradient for highlighted bars (long delays)
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8)?.toString() || '#a00');
    
    // Shadow filter (using feDropShadow to avoid blurring the actual shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group, translated for margins
    // 80px left margin, 40px top margin relative to SVG container
    const g = svg.append('g').attr('transform', `translate(80, 40)`);
    const {xScale, yScale} = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across the chart width
        .tickFormat(() => '') // No labels for grid lines
        .ticks(5)) // 5 ticks for the y-axis
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2'); // Dashed grid lines

    // X-axis (category labels)
    const xAxisGroup = g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`) // Position at the bottom of the chart area
      .call(d3.axisBottom(xScale).tickSizeOuter(0)); // No outer ticks
    
    xAxisGroup.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .attr('y', 15); // Adjust tick label position below the axis line
    
    xAxisGroup.select('.domain').attr('stroke', axisColor); // Color the axis line

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 40) // Positioned below tick labels, within subtitle safe zone
      .attr('text-anchor', 'middle')
      .attr('fill', axisColor)
      .style('font-size', '18px')
      .style('font-weight', '500')
      .text('延误时长 (分钟)')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis (value labels)
    const yAxisGroup = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5)); // 5 ticks for the y-axis
    
    yAxisGroup.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    yAxisGroup.select('.domain').attr('stroke', axisColor); // Color the axis line

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // CRITICAL: At least -70 to avoid overlap with tick numbers
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`)
      .attr('fill', axisColor)
      .style('font-size', '18px')
      .style('font-weight', '500')
      .text('航班数量')
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
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => {
        // Highlight bars representing delays > 60 minutes
        if (d[xField] === "60至120分钟" || d[xField] === ">120分钟") {
          return 'url(#highlightGradient)';
        }
        return barColor;
      })
      .attr('rx', 6) // Rounded corners for a softer look
      .style('filter', 'url(#shadow)'); // Apply shadow effect
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => {
        // Position label above bar if height allows, otherwise slightly below
        return yScale(d[yField]) > 20 ? yScale(d[yField]) - 10 : yScale(d[yField]) + 20;
      })
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField] > 0 ? d[yField].toString() : '') // Only show label for non-zero counts
      .attr('fill', (d: any) => {
        if (d[xField] === "60至120分钟" || d[xField] === ">120分钟") {
          return highlightColor; // Highlighted label color
        }
        return textColor;
      })
      .style('font-size', '16px')
      .style('font-weight', '700') // Bold for emphasis
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to start to manage top/bottom space
      padding: '0px 40px' // Left/right padding
    }}>
      {/* Title - positioned absolutely to reserve top 80px */}
      <div style={{
        position: 'absolute',
        top: 30, // Start title at 30px from top
        left: 0,
        right: 0,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Light color for title on dark background
        textAlign: 'center',
        zIndex: 10, // Ensure title is above SVG content
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        起飞延误时长分布
      </div>
      
      {/* Chart SVG container */}
      <svg 
        ref={svgRef} 
        width={1160} // Total SVG width (chartWidth + 2 * left/right margins)
        height={460} // Total SVG height (adjusted to fit within 720px, leaving 180px for subtitles)
        style={{ 
          marginTop: '80px', // Push chart down to clear the title area (80px from top)
          overflow: 'visible' // Ensure shadows and labels are not clipped by SVG boundary
        }} 
      />
    </AbsoluteFill>
  );
};