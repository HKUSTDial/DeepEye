import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_AnalysisCarrierArrdelayComparison_20260217_160118ComponentAnimated: React.FC  = () => {
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
  
  // Extract field names from data_binding
  const xField = "carrier";
  const yField = "avg_arrdelay";
  
  // Color configuration
  const backgroundColor = '#0f1419'; // MUST use JSON config value
  
  // Chosen based on scene semantics: "delays" (negative metric), but highlighting a "good performer" (lowest delay)
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#fb923c';   // Base color for delays (orange)
  const highlightColor = '#34d399'; // Highlight color for the best performer (AA, emerald green)
  const gridColor = '#4a5568';  // Subtle dark blue-grey for grid
  const axisColor = '#718096';  // Medium blue-grey for axes
  
  // Calculate metrics
  const minDelayValue = d3.min(data, (d: any) => d[yField]) || 0; // AA has the min delay
  const minDelayCarrier = data.find((d: any) => d[yField] === minDelayValue); // This is AA

  // D3 scales
  const scales = useMemo(() => {
    const chartWidth = 960; // Inner chart width
    const chartHeight = 300; // Inner chart height (Adjusted for subtitle space at bottom)

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding for wider bars, better readability

    const yScale = d3.scaleLinear()
      .domain([0, d3.max(data, (d: any) => d[yField]) * 1.1]) // Max value + 10% buffer
      .range([chartHeight, 0]); // In SVG, 0 is top, height is bottom

    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, xField, yField]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Define chart margins and dimensions for the D3 group
    const margin = { top: 40, right: 80, bottom: 40, left: 80 }; // D3 group transform margins
    const { xScale, yScale, chartWidth, chartHeight } = scales;
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Gradient for the highlighted bar (AA - lowest delay)
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColor)?.brighter(0.5).toString() || highlightColor);
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    // Gradient for regular bars
    const regularGradient = defs.append('linearGradient')
      .attr('id', 'regularGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    regularGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(barColor)?.brighter(0.5).toString() || barColor);
    regularGradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Draw chart group, positioned to respect margins within the SVG
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    // Y-axis grid lines (subtle)
    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');
    
    // Y-axis ticks and labels for reference
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5)) // Show 5 ticks for reference
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);

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
      .attr('fill', (d: any) => d[xField] === minDelayCarrier?.[xField] ? 'url(#highlightGradient)' : 'url(#regularGradient)')
      .attr('rx', 8) // Rounded corners
      .attr('ry', 8)
      .style('filter', 'url(#shadow)'); // Apply shadow
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2) + ' min') // Format to 2 decimal places + ' min'
      .attr('fill', (d: any) => d[xField] === minDelayCarrier?.[xField] ? highlightColor : textColor)
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
      .attr('y', chartHeight + 30) // Position below the chart area
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // X-axis label (for the entire axis)
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 60) // Further down, within the safe zone
      .attr('text-anchor', 'middle')
      .text('航空公司')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label (for the entire axis)
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Positioned to the left of the y-axis ticks
      .attr('y', chartHeight / 2)
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${chartHeight / 2})`) // Rotate around its own point
      .attr('text-anchor', 'middle')
      .text('平均抵达延误 (分钟)')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');


  }, [scales, minDelayCarrier, minDelayValue, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // Use the configured background color
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '60px 40px' // Padding for the overall AbsoluteFill container
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Keep clear for subtitle overlay (top 80-100px)
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Bright text for title
        textAlign: 'center',
        width: '100%', // Ensure title spans full width
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均抵达延误时间对比
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={1120} // Total SVG width (chartWidth + left_margin + right_margin)
        height={480} // Total SVG height (chartHeight + top_margin + bottom_margin), ensures it ends at 540px canvas y
        style={{ 
          marginTop: '60px', // Adjusted to place SVG start at y=60 on canvas
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
      
    </AbsoluteFill>
  );
};