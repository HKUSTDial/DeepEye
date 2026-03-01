import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const flightdelaystatistic_AnalysisDestcityArrdelayDistribution_20260217_135016Component: React.FC = () => {
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
  
  // Extract field names from data_binding
  const xField = "destcity";
  const yField = "avg_arrdelay";
  
  // Color configuration (background colors are CRITICAL and fixed as per JSON config)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; 
  
  // Scene-specific colors based on "flight delay statistics" and "comparison" semantics
  const textColor = '#e8eaed'; // Light grey for readability on dark background
  const barColor = '#3b82f6';   // A vibrant blue for general bars (analytical/data point tone)
  const highlightColorMax = '#ef4444'; // Red for highest delay (problem/warning tone)
  const highlightColorMin = '#10b981'; // Green for lowest delay (positive/best performance tone)
  const gridColor = '#4a5568';  // Subtle grey-blue for grid lines
  const axisColor = '#6b7280';  // Slightly darker grey-blue for axis elements
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  const minItem = data.find((d: any) => d[yField] === minValue);

  // Chart dimensions (Canvas: 1280x720px)
  const chartWidth = 960; // Overall SVG width
  const chartHeight = 550; // Overall SVG height
  // Margins adjusted for title (top: 80px) and subtitle zone (bottom: 180px)
  const margin = { top: 80, right: 60, bottom: 180, left: 100 }; 
  const innerWidth = chartWidth - margin.left - margin.right; // Actual chart drawing area width
  const innerHeight = chartHeight - margin.top - margin.bottom; // Actual chart drawing area height

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerWidth])
      .padding(0.2);
    
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Extend domain slightly above max for label space
      .range([innerHeight, 0]); // In SVG, 0 is top, innerHeight is bottom
      
    return { xScale, yScale };
  }, [data, innerWidth, innerHeight, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear SVG contents on re-render
    
    const { xScale, yScale } = scales;

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Shadow filter (use feDropShadow to avoid blur on shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
      
    // Linear gradient for the highest delay bar
    const maxGradient = defs.append('linearGradient')
      .attr('id', 'maxGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    maxGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColorMax)?.brighter(0.5)?.toString() || highlightColorMax);
    maxGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorMax);

    // Linear gradient for the lowest delay bar
    const minGradient = defs.append('linearGradient')
      .attr('id', 'minGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    minGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColorMin)?.brighter(0.5)?.toString() || highlightColorMin);
    minGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorMin);

    // Chart group - translated to apply margins
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    // Y-axis grid lines (before bars for background effect)
    g.append('g')
      .attr('class', 'grid-y')
      .attr('color', gridColor)
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth)
        .tickFormat(() => '')
      )
      .select('.domain').remove(); // Remove the axis line from grid

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
      .attr('fill', (d: any) => {
        if (d[xField] === maxItem?.destcity) return 'url(#maxGradient)';
        if (d[xField] === minItem?.destcity) return 'url(#minGradient)';
        return barColor;
      })
      .attr('rx', 8) // Rounded corners for aesthetics
      .style('filter', 'url(#shadow)'); // Apply shadow effect
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(2)}`) // Format to 2 decimal places
      .attr('fill', (d: any) => {
        if (d[xField] === maxItem?.destcity) return highlightColorMax;
        if (d[xField] === minItem?.destcity) return highlightColorMin;
        return textColor;
      })
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // X-axis category labels
    // CRITICAL: Position `y` relative to `g` must ensure total Y from SVG top <= (720 - 180) = 540px.
    // innerHeight + 30 = 290 + 30 = 320. Total from SVG top = margin.top + 320 = 80 + 320 = 400px. This is safe.
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', innerHeight + 30) 
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d) => `${d} min`);
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.select('.y-axis').selectAll('line').attr('stroke', axisColor); // Set tick line color
    g.select('.y-axis').select('.domain').remove(); // Remove the axis line from y-axis

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Position it further left from the chart area
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${innerHeight / 2})`)
      .text("平均到达延误 (分钟)")
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, data, xField, yField, maxValue, minValue, maxItem, minItem, barColor, highlightColorMax, highlightColorMin, textColor, gridColor, axisColor, innerWidth, innerHeight, margin.left, margin.top, margin.bottom, chartWidth, chartHeight]); 

  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to start to control vertical positioning
      padding: '0px 0px' 
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Position 30px from top, reserving top 80px for subtitle overlay
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各目的城市平均延误情况
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={chartWidth} 
        height={chartHeight} 
        style={{ 
          marginTop: '60px', // Push the SVG down to make room for the title above
          shapeRendering: 'geometricPrecision', // Critical for SVG clarity
          textRendering: 'geometricPrecision' // Critical for SVG text clarity
        }} 
      />
    </AbsoluteFill>
  );
};