import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 生成一个数据视频_ChartCarrierPassengersVsDelay_20260217_092103Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "sum_passengers": 239676,
    "avg_arrdelay": 9.48,
    "count": 1880
  },
  {
    "carrier": "EV",
    "sum_passengers": 9876,
    "avg_arrdelay": 12.76,
    "count": 144
  },
  {
    "carrier": "MQ",
    "sum_passengers": 3344,
    "avg_arrdelay": 38.98,
    "count": 56
  },
  {
    "carrier": "OO",
    "sum_passengers": 29825,
    "avg_arrdelay": 26.06,
    "count": 319
  },
  {
    "carrier": "UA",
    "sum_passengers": 210452,
    "avg_arrdelay": 15.6,
    "count": 1358
  }
];
  
  // Data binding from JSON
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均延误时间 (分钟)"
    }
  };
  
  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;

  // Color configuration (MUST use provided background, others based on scene semantics)
  const backgroundColor = '#0f1419'; // CRITICAL: MUST use this value
  const containerBackground = '#0f1419'; // CRITICAL: MUST use this value
  
  // Scene semantics: "航空公司平均延误时间" (Airline Average Delay Time)
  // Narration highlights highest delay (MQ) and relatively low delay (AA)
  // Emotional tone: Negative (delays) -> Red/Orange color scheme
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f97316'; // Vibrant orange for general delays
  const highlightColor = '#ef4444'; // Brighter red for the highest delay (MQ)
  const gridColor = '#3a4149'; // Subtle dark gray-blue
  const axisColor = '#888888'; // Medium gray for axes

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // Chart dimensions and margins
  const margin = { top: 40, right: 80, bottom: 180, left: 80 }; // Bottom 180px for subtitle
  const chartWidth = 1280 - margin.left - margin.right;
  const chartHeight = 720 - margin.top - margin.bottom; // Effective chart height for bars/axis

  // D3 scales
  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.4);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Give some padding above the max value
      .range([chartHeight, 0]); // Range from chartHeight (bottom) to 0 (top)

    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField, yField]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear SVG contents

    // Add SVG clarity optimizations
    svg.attr('shape-rendering', 'geometricPrecision')
       .attr('text-rendering', 'geometricPrecision');
    
    // Define gradient for highlighting the max value
    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); // Top color (red)
    gradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8) || highlightColor); // Darker red at bottom

    // Add shadow filter (using feDropShadow to avoid blurring the shape)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.4); // Slightly more opaque shadow

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    const { xScale, yScale } = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => '') // No labels for grid lines
        .ticks(5))
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '4 4'); // Dashed grid lines
    
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
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Positioned to the left of the axis
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for bars
      .attr('ry', 8)
      .style('filter', 'url(#barShadow)');

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // 10px above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(2)} min`) // Format delay time
      .attr('fill', (d: any) => d[xField] === maxItem?.[xField] ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Category labels (X-axis labels) below chart
    // CRITICAL: y-positioning to reserve bottom 180px for subtitles
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 30) // Positioned safely below the bars, within the 180px reserved zone
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', (d: any) => d[xField] === maxItem?.[xField] ? 'bold' : 'normal') // Bold for highlighted carrier
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis label (for the entire x-axis)
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 70) // Further down, below category labels
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Clean up axis lines (remove default d3 axis path and lines)
    g.select('.y-axis path').attr('stroke', 'none');
    g.select('.y-axis .tick line').attr('stroke', 'none');

    // Manually add axis line at the bottom of the chart area
    g.append('line')
      .attr('x1', 0)
      .attr('y1', chartHeight)
      .attr('x2', chartWidth)
      .attr('y2', chartHeight)
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);

  }, [scales, maxValue, maxItem, chartWidth, chartHeight, xField, yField, barColor, highlightColor, textColor, gridColor, axisColor, margin.left]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0px 0px' // Padding handled by SVG margins for precise control
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Keep clear for subtitle overlay if subtitle is at top
        fontSize: '36px',
        fontWeight: '700',
        color: textColor,
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision',
      }}>
        {data_binding.y_axis.label}
      </div>
      
      {/* Chart - centered within the available space */}
      <svg 
        ref={svgRef} 
        width={1280} 
        height={720} // Full canvas height, internal D3 margins handle spacing
        style={{ 
          marginTop: '20px', // Adjust to push chart down if needed
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};