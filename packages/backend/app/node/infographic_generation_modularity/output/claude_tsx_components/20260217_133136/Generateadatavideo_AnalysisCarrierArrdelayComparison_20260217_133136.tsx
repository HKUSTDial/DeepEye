import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

// Define the data structure explicitly for better type checking
interface CarrierDelayData {
  carrier: string;
  avg_arrdelay: number;
  count: number;
}

export const Generateadatavideo_AnalysisCarrierArrdelayComparison_20260217_133136Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);

  // Hardcoded data
  const data: CarrierDelayData[] = [
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

  // Data binding fields
  const xField = "carrier";
  const yField = "avg_arrdelay";
  const yLabel = "平均延误时间 (分钟)";

  // Color configuration (fixed background, semantic accent colors)
  const backgroundColor = '#0f1419'; // CRITICAL: MUST use JSON config value
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f97316';   // Orange for delays, representing an issue
  const highlightColor = '#ef4444'; // Red for emphasis on the highest delay
  const gridColor = '#3a3f44'; // Slightly lighter than background, subtle for grid lines
  const axisColor = '#888888'; // Grey for axis lines

  // Calculate metrics for highlighting
  const maxValue = d3.max(data, d => d[yField]) || 0;
  // const maxItem = data.find(d => d[yField] === maxValue); // Not directly used in D3 render logic, but useful for context

  // D3 dimensions
  const chartWidth = 960; // Inner width of the chart area within the SVG
  const chartHeight = 350; // Inner height of the chart area, leaving space for subtitles

  const scales = useMemo(() => {
    const xScale = d3.scaleBand<string>()
      .domain(data.map(d => d[xField]))
      .range([0, chartWidth - 160]) // Adjusted range to fit within translation and provide right margin
      .padding(0.3); // Padding between bars for visual clarity

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15]) // Extend domain slightly above max value for labels
      .range([chartHeight, 0]); // Range from chartHeight (bottom) to 0 (top)

    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight]);


  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders

    // Apply SVG clarity optimizations
    svg.attr('shape-rendering', 'geometricPrecision')
      .attr('text-rendering', 'geometricPrecision');

    const defs = svg.append('defs');

    // Linear gradient for the highlighted bar
    const gradient = defs.append('linearGradient')
      .attr('id', 'delayGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#ff9f00'); // Lighter orange
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor); // Vibrant red

    // Drop shadow filter for the highlighted bar (CRITICAL: feDropShadow for clarity)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 8) // Vertical offset for shadow
      .attr('stdDeviation', 10) // Softness of the shadow
      .attr('flood-color', '#000') // Shadow color
      .attr('flood-opacity', 0.4); // Shadow opacity

    // Chart group, translated to provide overall padding from SVG edges
    // 80px from left, 100px from top (leaving top 80px clear for title + buffer)
    const g = svg.append('g').attr('transform', 'translate(80, 100)');

    const { xScale, yScale } = scales;

    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .ticks(5) // Approximately 5 ticks
      .tickSizeOuter(0) // No outer ticks
      .tickFormat(d => `${d} min`); // Add 'min' suffix

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .call(axisG => axisG.select('.domain').remove()) // Remove the main axis line
      .call(axisG => axisG.selectAll('.tick line').attr('stroke', gridColor).attr('stroke-dasharray', '4 4')) // Grid lines
      .call(axisG => axisG.selectAll('text')
        .attr('fill', textColor)
        .style('font-size', '14px')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision')
      );

    // Y-axis label (CRITICAL: x position at least -70 to avoid overlap)
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70)
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`)
      .text(yLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', d => xScale(d[xField]) || 0)
      .attr('y', d => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', d => chartHeight - yScale(d[yField]))
      .attr('fill', d => d[yField] === maxValue ? 'url(#delayGradient)' : barColor) // Highlight max value
      .attr('rx', 8) // Rounded corners for bars
      .attr('ry', 8)
      .style('filter', d => d[yField] === maxValue ? 'url(#barShadow)' : 'none'); // Apply shadow only to max bar

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', d => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', d => yScale(d[yField]) - 12) // Position above the bar
      .attr('text-anchor', 'middle')
      .text(d => `${d[yField].toFixed(2)}`) // Format to 2 decimal places
      .attr('fill', d => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis category labels below chart
    // CRITICAL: y-position (relative to 'g') calculated to ensure absolute position leaves 180px for subtitle zone
    // Absolute position: 100 (g translate Y) + chartHeight + 40 = 100 + 350 + 40 = 490.
    // This is well above 720 - 180 = 540 (the cutoff for subtitles).
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', d => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 40) // Positioned below the chart, relative to 'g'
      .attr('text-anchor', 'middle')
      .text(d => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis line (below category labels)
    g.append('line')
      .attr('class', 'x-axis-line')
      .attr('x1', 0)
      .attr('y1', chartHeight + 60) // Position below category labels
      .attr('x2', chartWidth - 160) // Matches the width of the x-scale range
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);

  }, [scales, maxValue, xField, yField, yLabel, barColor, highlightColor, textColor, gridColor, axisColor, chartWidth, chartHeight]);

  // Total SVG height: 100px (top margin for 'g') + chartHeight (350px) + 60px (x-axis labels + line) + ~20px (bottom buffer) = 530px
  // This leaves 720px (total canvas height) - 530px (SVG content height) = 190px clear at the bottom for subtitles (CRITICAL for 180px requirement).
  return (
    <AbsoluteFill style={{
      background: backgroundColor, // CRITICAL: MUST use JSON config value: #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align items to the top to manage vertical spacing
      padding: '0px', // No padding here; spacing is managed by SVG 'g' translation and element positioning
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned 30px from the top, leaving space for potential subtitle overlay
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: textColor,
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision',
      }}>
        不同航空公司平均延误时间
      </div>

      {/* Chart SVG container */}
      <svg
        ref={svgRef}
        width={chartWidth} // Set SVG width to accommodate chart content and margins
        height={530} // Set SVG height based on calculated content height + buffer for subtitle zone
        style={{
          marginTop: '0px', // Vertical positioning handled by flexbox and 'g' translation
        }}
      />
    </AbsoluteFill>
  );
};