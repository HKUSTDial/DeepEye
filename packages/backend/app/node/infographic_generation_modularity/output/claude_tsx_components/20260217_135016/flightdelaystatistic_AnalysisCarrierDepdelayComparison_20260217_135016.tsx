import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const flightdelaystatistic_AnalysisCarrierDepdelayComparison_20260217_135016Component: React.FC = () => {
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
  
  // Data binding from prompt
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
  
  // Color configuration
  // CRITICAL: MUST use these background colors from JSON config (DO NOT change them!)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Other colors: Chosen based on scene semantics ("delays" -> red/orange scheme)
  const textColor = '#e8eaed'; // Light grey for dark background for readability
  const barColor = '#f97316'; // Orange for the 'delays' theme (Tailwind orange-500)
  const highlightColor = '#ea580c'; // Deeper orange for emphasis (Tailwind orange-600)
  const gridColor = '#555555'; // Subtle grey for grid lines
  const axisColor = '#888888'; // Subtle grey for axis labels and lines

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // D3 scales
  const scales = useMemo(() => {
    // Chart dimensions within the SVG
    // SVG width is 1200 (1280 - 40*2 padding from AbsoluteFill)
    // SVG height is 600 (720 - 60*2 padding from AbsoluteFill)
    const margin = {top: 40, right: 80, bottom: 180, left: 80}; // Bottom for subtitle, top for title buffer
    const innerWidth = (1280 - 40 * 2) - margin.left - margin.right; // 1200 - 80 - 80 = 1040
    const innerHeight = (720 - 60 * 2) - margin.top - margin.bottom; // 600 - 40 - 180 = 380
    
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerWidth])
      .padding(0.2);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% padding for top
      .range([innerHeight, 0]); // Invert range for SVG coordinates

    return { xScale, yScale, innerWidth, innerHeight, margin };
  }, [data, xField, yField, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create linear gradient for the highlighted bar (from lighter to darker orange)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', barColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    // Shadow filter (using feDropShadow to avoid blurring the actual shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Chart group with margins
    const {xScale, yScale, innerWidth, innerHeight, margin} = scales;
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-innerWidth) // Extend grid lines across the chart
        .tickFormat(() => "") // No labels for grid lines
        .ticks(5) // Approximately 5 grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-opacity', 0.3);

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
    
    // Y-axis label
    g.append('text')
      .attr('x', -margin.left + 15) // Position to the left of tick labels
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 15}, ${innerHeight / 2})`)
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
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for a softer look
      .style('filter', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#shadow)' : 'none');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2) + ' min') // Format as "XX.XX min"
      .attr('fill', textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart
    // CRITICAL: Position above the 180px subtitle zone.
    // innerHeight is 380. Adding a buffer of 30px makes it 410.
    // g is translated by margin.top (40px). So, actual y from SVG top is 410 + 40 = 450px.
    // This leaves (720 - 450) = 270px from the bottom of the video frame, which is > 180px required.
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', innerHeight + 30) // Position below the bars
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[xField] === maxItem?.[xField] ? 'bold' : 'normal') // Bold the max item label
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, maxItem]); 
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px' // Padding for the AbsoluteFill container
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned at the top, leaving space for the subtitle overlay below
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        '-webkit-font-smoothing': 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        不同航空公司平均出发延误比较
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={1280 - 40 * 2} // Total video width minus AbsoluteFill horizontal padding
        height={720 - 60 * 2} // Total video height minus AbsoluteFill vertical padding
        style={{ 
          marginTop: '20px', // Push chart down from the title for better separation
          shapeRendering: 'geometricPrecision', // SVG clarity optimization
          textRendering: 'geometricPrecision' // SVG clarity optimization
        }} 
      />
    </AbsoluteFill>
  );
};