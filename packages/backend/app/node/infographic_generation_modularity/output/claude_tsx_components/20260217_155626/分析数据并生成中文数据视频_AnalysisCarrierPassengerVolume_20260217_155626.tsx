import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_AnalysisCarrierPassengerVolume_20260217_155626Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "sum_passengers": 239676,
    "count": 1880
  },
  {
    "carrier": "EV",
    "sum_passengers": 9876,
    "count": 144
  },
  {
    "carrier": "MQ",
    "sum_passengers": 3344,
    "count": 56
  },
  {
    "carrier": "OO",
    "sum_passengers": 29825,
    "count": 319
  },
  {
    "carrier": "UA",
    "sum_passengers": 210452,
    "count": 1358
  }
];
  
  // Data Binding (from prompt)
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "sum_passengers",
      "label": "客运总量"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  
  // Color configuration - MUST use these background colors, others chosen based on scene semantics
  const backgroundColor = '#0f1419'; 
  const containerBackground = '#0f1419'; // Not directly used in this component, but for consistency

  // Scene semantics: Neutral analysis, comparison of passenger volume.
  // Using a harmonious blue/cyan scheme with the dark background.
  const textColor = '#e8eaed'; // Off-white for readability on dark background
  const barColor = '#3b82f6'; // A vibrant blue for general bars
  const highlightColor = '#82d0fe'; // A brighter sky blue to highlight the max value
  const gridColor = '#2a3440'; // Subtle dark gray-blue for grid lines
  const axisColor = '#888888'; // Medium gray for axis labels and ticks

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue); // Needed for conditional styling

  // D3 dimensions
  const svgWidth = 960; // Chart-Dominant layout, 80% of 1280px is 1024, using 960 for good margins
  const svgHeight = 550; // Total SVG element height. Actual chart drawing area within this.

  // Margins for the chart group within the SVG
  const margin = { top: 40, right: 60, bottom: 0, left: 80 }; // Bottom margin handled by overall SVG height and positioning
  
  // Inner chart dimensions (where the bars will be drawn, relative to 'g' transform)
  // This value is critical for `yScale` range and bar heights.
  // It ensures bars and their value labels fit above the reserved bottom 180px for subtitles.
  const innerChartHeight = 320; // Consistent with example range([320, 0])
  const innerChartWidth = svgWidth - margin.left - margin.right; // 960 - 80 - 60 = 820

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, innerChartWidth])
      .padding(0.3); // Space between bars

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Y-axis starts at 0, ends slightly above max value
      .range([innerChartHeight, 0]); // Maps data values to pixel range (bottom to top)

    return { xScale, yScale };
  }, [data, xField, yField, maxValue, innerChartWidth, innerChartHeight]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add SVG clarity optimizations
    svg.attr('shapeRendering', 'geometricPrecision')
       .attr('textRendering', 'geometricPrecision');

    const defs = svg.append('defs');
    
    // Gradient for the highlighted bar (AA)
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColor)!.brighter(0.5).toString());
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);

    // Shadow filter for the highlighted bar
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 8) // Vertical offset for shadow
      .attr('stdDeviation', 10) // Blur radius
      .attr('flood-color', highlightColor) // Shadow color matches highlight
      .attr('flood-opacity', 0.4); // Semi-transparent shadow

    // Main chart group, translated by margins
    // This 'g' element's origin is at (margin.left, margin.top) relative to the SVG.
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    const { xScale, yScale } = scales;

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .attr('opacity', 0.4)
      .call(d3.axisLeft(yScale)
        .tickSize(-innerChartWidth) // Extend grid lines across chart width
        .tickFormat(() => "") // No labels for grid lines
      )
      .select('.domain').remove(); // Remove the axis line itself

    // Y-axis labels (numbers)
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).tickSize(0).tickPadding(10).tickFormat(d3.format(".2s"))) // Format for thousands/millions/etc.
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    g.select('.y-axis').select('.domain').remove(); // Remove Y-axis domain line

    // Bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField])!)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => innerChartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for aesthetics
      .style('filter', (d: any) => d[yField] === maxValue ? 'url(#shadow)' : 'none');

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => xScale(d[xField])! + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Positioned slightly above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(",")(d[yField])) // Format with commas for large numbers
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Category labels (X-axis labels)
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => xScale(d[xField])! + xScale.bandwidth() / 2)
      .attr('y', innerChartHeight + 25) // Positioned below the bars, within safe zone for subtitles
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -margin.left + 20) // Positioned to the left of the y-axis ticks
      .attr('y', innerChartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-margin.left + 20}, ${innerChartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
  }, [scales, data, xField, yField, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, innerChartHeight, innerChartWidth, margin.left]);

  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: Use the determined background color
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to ensure title space
      padding: '0px 40px' // Horizontal padding
    }}>
      {/* Title - positioned at the top, outside of the SVG chart area */}
      <div style={{
        position: 'absolute',
        top: 30, // Top 30px from the absolute fill top
        fontSize: '36px',
        fontWeight: '700',
        color: textColor, // Use consistent text color
        textAlign: 'center',
        width: '100%', // Ensure title spans full width
      }}>
        {/* Dynamic title using data binding labels */}
        {data_binding.x_axis.label} {data_binding.y_axis.label}对比
      </div>
      
      {/* Chart SVG container */}
      <svg 
        ref={svgRef} 
        width={svgWidth} 
        height={svgHeight} 
        style={{ 
          marginTop: '100px', // Pushes the SVG down to account for title and top buffer
          // The bottom 180px for subtitles are reserved by ensuring chart elements
          // (bars, x-axis labels) do not extend below `innerChartHeight + margin.top + X-axis_label_offset`
          // which in this case calculates to 40 (svg.top) + 320 (chartHeight) + 25 (x_label_offset) = 385px
          // from the SVG's top. The SVG itself is pushed down 100px, so absolute y=485px.
          // Canvas height is 720px. 720 - 485 = 235px remaining, which is > 180px for subtitles.
          overflow: 'visible' // Allow elements like shadows to render outside svg bounds
        }} 
      />
    </AbsoluteFill>
  );
};