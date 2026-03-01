import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const flightdelaystatistic_AnalysisArrdelayDistribution_20260217_135016Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "delay_range": "小于 -20",
    "count": 7
  },
  {
    "delay_range": "[-20, -1]",
    "count": 15
  },
  {
    "delay_range": "[0, 19]",
    "count": 3
  },
  {
    "delay_range": "[20, 39]",
    "count": 0
  },
  {
    "delay_range": "[40, 59]",
    "count": 1
  },
  {
    "delay_range": "[60, 79]",
    "count": 1
  },
  {
    "delay_range": "[80, 99]",
    "count": 1
  },
  {
    "delay_range": "[100, 119]",
    "count": 0
  },
  {
    "delay_range": "[120, 139]",
    "count": 0
  },
  {
    "delay_range": "[140, 159]",
    "count": 0
  },
  {
    "delay_range": "[160, 179]",
    "count": 1
  },
  {
    "delay_range": "[180, 199]",
    "count": 1
  }
];
  
  // Data binding configuration
  const data_binding = {
    "x_axis": {
      "field": "delay_range",
      "label": "延误时长 (分钟)"
    },
    "y_axis": {
      "field": "count",
      "label": "航班数量"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field; // Explicitly cast for single y_axis

  // Color configuration (MUST use JSON config values for background)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Scene-specific colors based on "Arrival Delay Duration Distribution" (delays, distribution, concern)
  const textColor = '#e8eaed'; 
  const barColor = '#fca311'; // Golden-orange for delays, not overly aggressive but distinct
  const highlightColor = '#f77f00'; // More vibrant orange for highlighted elements
  const gridColor = '#3a4149'; // Subtle grid color, slightly lighter than background
  const axisColor = '#6f7e8a'; // Medium grey for axis lines and labels

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions and margins
  const chartWidth = 960 - 80 * 2; // SVG width - left/right margins
  const chartHeight = 300; // Height of the actual bar drawing area (reserving bottom for subtitles)
  const margin = { top: 40, right: 80, bottom: 40, left: 80 }; // For 'g' element transform

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([chartHeight, 0]);
    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField]);
  
  // Static D3 rendering
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
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); 
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor); 
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Draw chart with proper spacing
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    const {xScale, yScale} = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => "")
        .ticks(5)
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-opacity', 0.7);

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5))
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 10) // Positioned to the left of the axis line
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 10}, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Draw bars (highlight max value)
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue && maxItem?.delay_range === d.delay_range ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for bars
      .style('filter', 'url(#shadow)');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField] > 0 ? d[yField] : '') // Only show non-zero counts
      .attr('fill', (d: any) => d[yField] === maxValue && maxItem?.delay_range === d.delay_range ? highlightColor : textColor)
      .style('font-size', '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // X-axis (invisible line, just for ticks and labels)
    const xAxisGroup = g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`)
      .call(d3.axisBottom(xScale).tickSizeOuter(0)); // Hide outer ticks
      
    // X-axis tick labels
    xAxisGroup.selectAll('text')
      .attr('fill', axisColor)
      .attr('y', 15) // Adjust position below the axis line
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis line/path
    xAxisGroup.selectAll('path')
      .attr('stroke', axisColor);
    xAxisGroup.selectAll('line')
      .attr('stroke', gridColor) // Use grid color for x-axis ticks
      .attr('stroke-opacity', 0.3); // Make them subtle

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 45) // Position below x-axis ticks
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, maxItem, chartWidth, chartHeight, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, data_binding]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to control space
      padding: '60px 40px' // Overall padding
    }}>
      {/* Title - Positioned at the top, reserving space for potential subtitles */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top of AbsoluteFill
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        到达延误时长分布
      </div>
      
      {/* Chart - Centered horizontally, positioned vertically to leave space */}
      <svg 
        ref={svgRef} 
        width={960} // Total SVG width (1280 - 2*160 for side margins in AbsoluteFill)
        height={550} // Total SVG height (720 - 60 top padding - 110 bottom for subtitle)
        style={{ 
          marginTop: '80px', // Pushes chart down from top, leaving space for title/subtitle
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision',
          overflow: 'visible' // Ensure shadows/labels are not clipped
        }} 
      />
    </AbsoluteFill>
  );
};