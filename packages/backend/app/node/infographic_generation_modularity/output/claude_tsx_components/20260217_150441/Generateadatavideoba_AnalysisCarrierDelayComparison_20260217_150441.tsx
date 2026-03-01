import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisCarrierDelayComparison_20260217_150441Component: React.FC = () => {
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
  
  // Data binding configuration
  const data_binding = {
    "x_axis": { "field": "carrier", "label": "航空公司" },
    "y_axis": { "field": "avg_depdelay", "label": "平均出发延误 (分钟)" }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field; // y_axis is a dict, not an array
  
  // Color configuration
  const backgroundColor = '#0f1419'; // MUST use JSON config value
  const containerBackground = '#0f1419'; // MUST use JSON config value
  
  const textColor = '#e8eaed'; // Light grey for readability on dark background
  const barColor = '#f97316';   // Primary color: Orange for 'delays' semantics
  const highlightColor = '#facc15'; // Accent color: Brighter amber for highlighting max delay
  const gridColor = '#374151'; // Subtle darker grey for grid lines
  const axisColor = '#888888'; // Lighter grey for axis labels/lines

  // Format numbers to two decimal places
  const formatValue = d3.format(".2f");
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions and margins
  const svgWidth = 1280;
  const svgHeight = 720;
  const marginTop = 100; // Space for title and top buffer
  const marginRight = 80;
  const marginBottom = 180; // CRITICAL: Space for 2-3 line subtitles
  const marginLeft = 80; // Space for Y-axis label

  const chartWidth = svgWidth - marginLeft - marginRight;
  const chartHeight = svgHeight - marginTop - marginBottom; // Actual drawing area for bars

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Extend domain slightly above max value
      .range([chartHeight, 0]); // Invert range for SVG coordinates

    return { xScale, yScale };
  }, [data, xField, yField, chartWidth, chartHeight, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create linear gradient for the highlighted bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group
    const g = svg.append('g')
      .attr('transform', `translate(${marginLeft}, ${marginTop})`);
    
    const { xScale, yScale } = scales;

    // Horizontal grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,4');
    
    // Y-axis label
    g.append('text')
      .attr('x', -marginLeft / 2 - 10) // Position left of the chart area
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-marginLeft / 2 - 10}, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis tick labels
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => formatValue(d as number)))
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
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
      .attr('rx', 8) // Rounded corners for aesthetics
      .attr('ry', 8)
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position 15px above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => formatValue(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart
    // Positioned safely above the 180px subtitle zone
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 25) // Position below the x-axis
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, maxItem, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight, marginLeft]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center', // This centers the SVG vertically when combined with top padding
      padding: '0 40px' // Left/right padding
    }}>
      {/* Title - positioned at the top, leaving space for subtitles below */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Light white for title
        textAlign: 'center',
        width: '100%',
      }}>
        按航空公司划分的平均出发延误
      </div>
      
      {/* Chart - centered vertically within the available space */}
      <svg 
        ref={svgRef} 
        width={svgWidth} 
        height={svgHeight} 
        style={{ 
          marginTop: '0px', // Managed by absolute positioning of title and overall flex centering
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};