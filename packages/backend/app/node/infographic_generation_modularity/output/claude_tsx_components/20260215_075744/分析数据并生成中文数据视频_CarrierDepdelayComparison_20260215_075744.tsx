import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_CarrierDepdelayComparison_20260215_075744Component: React.FC = () => {
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

  // Color configuration
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';

  // Scene-specific colors for "Delays related" theme (red/orange)
  const textColor = '#e8eaed';
  const barColor = '#f97316'; // Orange-500 for general bars
  const highlightColor = '#dc2626'; // Red-600 for the highest delay
  const gridColor = '#374151'; // Darker grey for subtle grid
  const axisColor = '#6b7280'; // Medium grey for axis elements

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);

  const scales = useMemo(() => {
    // Chart dimensions
    const chartWidth = 840; // Total SVG width 960 - 80 (left margin) - 40 (right margin)
    const chartHeight = 400; // Usable chart height, leaving space for labels and subtitle

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15]) // Add some padding above the max value
      .range([chartHeight, 0]);

    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, maxValue]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear SVG contents for re-render

    const { xScale, yScale, chartWidth, chartHeight } = scales;

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');

    // Gradient for the highlighted bar (from a lighter orange to a darker red)
    const gradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#fcd34d'); // Lighter shade of orange
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor); // Darker red

    // Shadow filter (using feDropShadow to avoid blur)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 8)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.4);

    // Draw chart group with proper spacing
    // SVG is positioned with `top: 80`, so `g` transform `translate(80, 0)` places it correctly relative to SVG.
    const g = svg.append('g').attr('transform', `translate(80, 0)`);

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .ticks(5)
        .tickSize(-chartWidth)
        .tickFormat(() => '')
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,4');

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -60) // Position to avoid overlap with tick numbers
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -60, ${chartHeight / 2})`)
      .text("平均出发延误 (分钟)")
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis ticks and labels
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d3.format(".1f")))
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
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners
      .style('filter', 'url(#barShadow)');

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 18) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(".1f")(d[yField])) // Format to one decimal place
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '24px' : '18px')
      .style('font-weight', (d: any) => d[yField] === maxValue ? '900' : '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Category labels below chart
    // CRITICAL: y = 420 (relative to 'g') means absolute Y is 80 (SVG top) + 420 = 500.
    // This leaves 720 - 500 = 220px for the subtitle zone (>=180px required).
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 40) // Position below the chart bars
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, maxItem]);

  return (
    <AbsoluteFill style={{
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to give space for title
      padding: '0px 40px' // Horizontal padding
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Top 30px, consistent with 80px buffer
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%', // Ensure title spans full width for centering
        fontFamily: 'system-ui, -apple-system, sans-serif',
        '-webkit-font-smoothing': 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        不同航空公司平均出发延误时间对比
      </div>

      {/* Chart - positioned to respect top 80px and bottom 180px subtitle zone */}
      <svg
        ref={svgRef}
        width={960} // Total SVG width
        height={460} // Total SVG height (720 - 80 top - 180 bottom = 460)
        style={{
          marginTop: '80px', // Pushes SVG down from the top, creating the 80px buffer
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }}
      />
    </AbsoluteFill>
  );
};