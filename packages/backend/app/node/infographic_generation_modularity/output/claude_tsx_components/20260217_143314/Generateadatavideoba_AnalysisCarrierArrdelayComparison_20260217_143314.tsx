import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisCarrierArrdelayComparison_20260217_143314Component: React.FC = () => {
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
  
  // Data Binding
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均到达延误 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string; label: string }).field;
  const yLabel = (data_binding.y_axis as { field: string; label: string }).label;

  // Color configuration (CRITICAL: background colors are unified from JSON config)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; // Unused in this component, but kept for consistency
  
  // Scene-specific colors based on "Delays" semantic
  const textColor = '#e8eaed';
  const barColor = '#ef4444'; // Red for delays
  const highlightColor = '#dc2626'; // Darker red for emphasis
  const gridColor = '#3a4047'; // Subtle grey for grids
  const axisColor = '#888888'; // Subtle grey for axes
  
  // Calculate metrics for highlighting
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  const minItem = data.find((d: any) => d[yField] === minValue);

  // D3 dimensions, ensuring space for title and subtitle
  const svgWidth = 1100; // Increased width for better bar spacing
  const svgHeight = 500; // Total SVG height
  const margin = { top: 80, right: 100, bottom: 180, left: 100 }; // Critical: bottom 180px for subtitles
  
  const chartWidth = svgWidth - margin.left - margin.right;
  const chartHeight = svgHeight - margin.top - (margin.bottom - 60); // Adjust chart height to fit axis labels within SVG total height, considering 180px bottom reserve
                                                                    // The 60px here is roughly for the x-axis labels and its title
                                                                    // chartHeight is the actual range for y-scale
  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Extend domain slightly above max for label space
      .range([chartHeight, 0]);
    return { xScale, yScale };
  }, [data, maxValue, xField, chartWidth, chartHeight]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create gradient for highlighted bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', barColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);
    
    // Shadow filter (feDropShadow to avoid blur)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group, shifted to leave space for title and margins
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    const {xScale, yScale} = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => '')
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
    
    g.select('.y-axis path').attr('stroke', axisColor);
    g.select('.y-axis .tick line').attr('stroke', axisColor);

    // X-axis (invisible line, labels handled separately)
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`)
      .call(d3.axisBottom(xScale).tickSize(0).tickFormat(() => ''))
      .select('path') // Select the axis line and make it visible
      .attr('stroke', axisColor);
    
    // Draw bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for bars
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(1)} min`)
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', (d: any) => d[xField] === maxItem?.[xField] || d[xField] === minItem?.[xField] ? '700' : '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart (x-axis tick labels)
    // Positioned relative to the 'g' group, ensuring it's above the overall bottom 180px subtitle zone
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 30) // Position below the x-axis line, at y-coord in 'g' coordinates
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[xField] === maxItem?.[xField] || d[xField] === minItem?.[xField] ? '700' : '400')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('x', -margin.left + 20) // Position to the left of the y-axis
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${chartHeight / 2})`)
      .text(yLabel)
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, maxItem, minItem, chartWidth, chartHeight, yLabel, margin.left, margin.top, margin.bottom]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0px 40px'
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Consistent top margin for title
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均到达延误时间
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={svgWidth} 
        height={svgHeight} 
        style={{ 
          marginTop: '20px', // Push chart down slightly from title
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};