import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisCarrierDepdelayComparison_20260217_143314Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data for the scene
  const data = [
    {"carrier": "AA", "avg_depdelay": 15.41, "count": 1880},
    {"carrier": "EV", "avg_depdelay": 16.53, "count": 144},
    {"carrier": "MQ", "avg_depdelay": 33.98, "count": 56},
    {"carrier": "OO", "avg_depdelay": 25.3, "count": 319},
    {"carrier": "UA", "avg_depdelay": 25.24, "count": 1358}
  ];
  
  // Data binding fields
  const xField = "carrier";
  const yField = "avg_depdelay";
  const xLabel = "航空公司";
  const yLabel = "平均延误时间 (分钟)";

  // CRITICAL: Background colors are ALREADY determined by JSON config. DO NOT CHANGE!
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; // This is also #0f1419, consistent.
  
  // Other colors chosen based on scene semantics (Delays -> Orange/Red scheme)
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f97316'; // Primary orange for bars, signifies "problem" (delay)
  const highlightColor = '#ea580c'; // Deeper orange for the highest bar/highlight
  const gridColor = '#374151'; // Subtle gray for grid lines
  const axisColor = '#555555'; // Slightly darker gray for axis lines
  
  // Calculate max value for Y-axis domain and to identify the highest bar
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;

  // SVG dimensions (canvas size)
  const svgWidth = 1280;
  const svgHeight = 720;

  // Chart area dimensions within the SVG
  const chartWidth = 960; // Represents the width available for the bars/plot area
  const chartHeight = 340; // Represents the height available for the bars/plot area

  // Translation for the main chart group (g element) to position it within the SVG
  // g_translateX centers the chart horizontally: (1280 - 960) / 2 = 160
  const g_translateX = (svgWidth - chartWidth) / 2; 
  // g_translateY provides space from the top for the title and a small gap.
  // Title is at top 30px, approx 40px height. So title ends at ~70px.
  // g_translateY = 120 means chart content starts 50px below title.
  const g_translateY = 120; 

  // D3 Scales memoization
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Padding between bars

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% buffer above max value
      .range([chartHeight, 0]); // Range is [max_height, 0] because SVG y-coords are top-down
      
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField]);
  
  // D3 rendering logic in useEffect
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders

    // Define SVG filters and gradients
    const defs = svg.append('defs');
    
    // Linear gradient for the highlighted bar (from highlightColor to barColor)
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    // Drop shadow filter for visual depth (uses feDropShadow to avoid blurring the shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group, translated to its position within the SVG canvas
    const g = svg.append('g').attr('transform', `translate(${g_translateX}, ${g_translateY})`);
    const {xScale, yScale} = scales;

    // Y-axis grid lines (behind the bars)
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across the chart width
        .tickFormat(() => "") // No labels for grid lines
        .ticks(5) // Approximately 5 grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2'); // Dashed lines for subtlety
    
    // Y-axis (ticks and labels)
    const yAxisGroup = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5));
      
    // Style Y-axis tick labels
    yAxisGroup.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Style Y-axis line and ticks
    yAxisGroup.selectAll('path, line').attr('stroke', axisColor);

    // Y-axis label (rotated)
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -g_translateX + 40) // Positioned relative to g's origin, adjusted to be left of Y-axis
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      // Rotation transform must match the x,y coordinates
      .attr('transform', `rotate(-90, ${-g_translateX + 40}, ${chartHeight / 2})`)
      .text(yLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Draw bars for each data point
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      // Highlight the bar with the maximum value using the gradient
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners
      .style('filter', 'url(#shadow)'); // Apply shadow filter
    
    // Value labels on top of each bar
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position slightly above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) // Format to 2 decimal places
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? 'bold' : 'normal')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels (X-axis tick labels) below the bars
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 35) // Positioned 35px below the chart baseline (chartHeight)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? 'bold' : 'normal') // Highlight category too
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis label (overall label for the categories)
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 70) // Positioned 70px below the chart baseline (below category labels)
      .attr('text-anchor', 'middle')
      .text(xLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, chartWidth, chartHeight, g_translateX, g_translateY, barColor, highlightColor, textColor, gridColor, axisColor, xField, yField, xLabel, yLabel]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // Uses the unified background color
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align content to the top
    }}>
      {/* Scene Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned 30px from the top of the canvas
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Light text for title
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均起飞延误时间
      </div>
      
      {/* D3 Chart SVG Container */}
      <svg 
        ref={svgRef} 
        width={svgWidth} // Full canvas width
        height={svgHeight} // Full canvas height
        style={{ 
          // SVG element itself takes full canvas, its content is translated by the 'g' element
          shapeRendering: 'geometricPrecision', // Ensures sharp lines and shapes
          textRendering: 'geometricPrecision' // Ensures sharp text rendering
        }} 
      />
    </AbsoluteFill>
  );
};