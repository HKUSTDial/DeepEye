import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const flightdelaystatistic_AnalysisCarrierArrdelayComparison_20260217_135016Component: React.FC = () => {
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

  // Data binding from prompt
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均抵达延误 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field; // Single y_axis field

  // Color configuration - MUST use these background colors
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';

  // Scene-specific colors based on "Delays/Problems" semantics (red/orange scheme)
  const textColor = '#e8eaed';
  const barColor = '#f97316'; // Orange for general bars
  const highlightColor = '#ef4444'; // Red for the highest delay
  const gridColor = '#374151'; // Darker gray for subtle grid
  const axisColor = '#6b7280'; // Medium gray for axis lines

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const minItem = data.find((d: any) => d[yField] === minValue);

  // D3 scales
  const scales = useMemo(() => {
    const chartWidth = 960 - 80 - 80; // SVG width - left_margin - right_margin
    const chartHeight = 320; // Max chart drawing height to leave space for subtitles

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding for cleaner look

    // Ensure y-axis starts from 0 and goes slightly above max value
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Add some buffer above the max value
      .range([chartHeight, 0]);

    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, xField, yField, maxValue]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Define main chart group
    const { xScale, yScale, chartWidth, chartHeight } = scales;
    const g = svg.append('g').attr('transform', 'translate(80, 40)'); // Adjust for margins

    // Add gradients and shadow filters in <defs>
    const defs = svg.append('defs');

    // Gradient for the highlighted bar (highest delay)
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(1.5).toString() || highlightColor);

    // Standard bar gradient (optional, or just use solid color)
    const barGradient = defs.append('linearGradient')
      .attr('id', 'barGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    barGradient.append('stop').attr('offset', '0%').attr('stop-color', barColor);
    barGradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(barColor)?.darker(1.0).toString() || barColor);

    // Shadow filter (feDropShadow to avoid blurring the shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    // Draw Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth)
        .tickFormat(() => '') // No labels for grid lines
        .ticks(5))
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,4');

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
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#highlightGradient)' : 'url(#barGradient)')
      .attr('rx', 8) // Rounded corners for aesthetics
      .style('filter', 'url(#shadow)');

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) // Format to 2 decimal places
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis (category labels)
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`)
      .call(d3.axisBottom(xScale).tickSizeOuter(0))
      .selectAll('text')
      .attr('y', 15) // Position tick labels slightly below axis line
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 50) // Position below tick labels (y=320+50 = 370 in g-coords)
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5)) // 5 ticks for cleaner look
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // Position far left to avoid overlap with tick numbers
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Style axis lines
    g.selectAll('.x-axis path, .y-axis path')
      .attr('stroke', axisColor);
    g.selectAll('.x-axis line, .y-axis line')
      .attr('stroke', axisColor);

  }, [scales, data, xField, yField, maxValue, textColor, barColor, highlightColor, gridColor, axisColor, data_binding]);

  return (
    <AbsoluteFill style={{
      background: backgroundColor, // CRITICAL: MUST use JSON config value: #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to better manage spacing
      padding: '60px 40px'
    }}>
      {/* Title - positioned at the top, allowing space for subtitles below */}
      <div style={{
        position: 'absolute',
        top: 30, // Keep clear for 80px subtitle overlay
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均抵达延误时间
      </div>

      {/* Chart - centered, with space for labels */}
      <svg
        ref={svgRef}
        width={960}
        height={550} // Adjusted height to fit within safe zones
        style={{
          marginTop: '80px', // Push chart down to clear top 80px for title/subtitle overlay
          marginBottom: '180px', // Ensure bottom 180px is clear for subtitles
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }}
      />
    </AbsoluteFill>
  );
};