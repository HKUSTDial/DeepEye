import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_AnalysisCarrierDepdelayComparison_20260217_160118Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
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
  
  // Extract field names from data_binding
  const xField = "carrier";
  const yField = "avg_depdelay";
  const yAxisLabel = "平均出发延误时间 (分钟)";
  
  // Color configuration - CRITICAL: Background colors are fixed!
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; 
  
  // Other colors chosen based on scene semantics (delays/problems -> red/orange)
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f97316'; // Warm orange for general bars
  const highlightColor = '#ef4444'; // Intense red for the highest delay
  const gridColor = '#2d333b'; // Subtle dark gray for grid lines
  const axisColor = '#5a626a'; // Slightly brighter gray for axis lines and ticks
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // D3 scales
  // SVG size is 960x550 from template.
  // We apply a 'g' transform of translate(80, 40) for chart margins.
  // This leaves 960 - 80 (left margin) - 80 (right margin/padding) = 800px for the chartWidth.
  // For chartHeight: 550 (SVG height) - 40 (top margin) - 180 (bottom subtitle safe zone) - 0 (padding) = 330px.
  const chartWidth = 800; 
  const chartHeight = 330; 
  
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2); // Padding between bars
      
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% padding above max value for labels
      .range([chartHeight, 0]); // Invert Y-axis for SVG (0 at top)
      
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField]);
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous drawings
    
    // Add definitions for gradients and shadows
    const defs = svg.append('defs');
    
    // Create linear gradient for the highlighted bar (red/orange theme)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', barColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    // Drop shadow filter for clarity (CRITICAL: use feDropShadow, not feGaussianBlur+feOffset!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Chart group with margins applied via transform
    const g = svg.append('g').attr('transform', 'translate(80, 40)');
    const {xScale, yScale} = scales;
    
    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .ticks(5) // Approximately 5 ticks
        .tickSize(-chartWidth) // Extend grid lines across the chart width
        .tickFormat(() => "") // No labels for grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2'); // Dashed grid lines for subtlety
      
    // Y-axis (only path and text, no line for the axis itself)
    const yAxis = g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat((d: any) => `${d.toFixed(0)} 分钟`)); // Format ticks to whole numbers
      
    yAxis.selectAll('path').remove(); // Remove the main Y-axis line
    yAxis.selectAll('line') // Keep only the tick lines and color them
      .attr('stroke', axisColor);
    yAxis.selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('x', -70) // CRITICAL: Position at least -70px to the left of the axis to avoid overlap with tick numbers!
      .attr('y', chartHeight / 2) // Center vertically relative to chart height
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`) // Rotate around its own position
      .text(yAxisLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
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
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for a softer look
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none'); // Apply shadow only to the highlighted bar
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) // Format to two decimal places
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart (X-axis labels)
    // CRITICAL: Position at chartHeight + 30px (relative to 'g')
    // This translates to 40 (g-y) + 330 (chartHeight) + 30 = 400px absolute Y.
    // This leaves 720 - 400 = 320px for the subtitle zone, which is more than the required 180px.
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 30) 
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight, xField, yField, yAxisLabel, data]); 
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px' // Overall padding for the scene
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned 30px from top, leaving space for subtitle overlay
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Bright text color for visibility on dark background
        textAlign: 'center',
        width: '100%', // Ensure title text can span full width for centering
      }}>
        各航空公司平均出发延误时间
      </div>
      
      {/* Chart SVG container */}
      <svg 
        ref={svgRef} 
        width={960} // Template width
        height={550} // Template height
        style={{ 
          marginTop: '20px', // Push chart down slightly from the title
          shapeRendering: 'geometricPrecision', // CRITICAL: For sharper SVG rendering
          textRendering: 'geometricPrecision' // CRITICAL: For sharper text rendering
        }} 
      />
      
      {/* CRITICAL: NO Redundant Information Cards! */}
      {/* Data labels on chart elements are sufficient. Highlight key data IN THE CHART ITSELF. */}
    </AbsoluteFill>
  );
};