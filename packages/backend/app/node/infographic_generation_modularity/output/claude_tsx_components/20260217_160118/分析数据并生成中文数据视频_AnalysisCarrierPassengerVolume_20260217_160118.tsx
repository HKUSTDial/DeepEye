import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_AnalysisCarrierPassengerVolume_20260217_160118Component: React.FC = () => {
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

  // Data binding fields
  const xField = "carrier";
  const yField = "sum_passengers";

  // Color configuration - CRITICAL: background_color and container_background are fixed!
  const backgroundColor = '#0f1419'; // MUST use this exact value from JSON config
  const containerBackground = '#0f1419'; // MUST use this exact value from JSON config

  // Scene-specific colors based on "Comparison of Total Passengers by Airline" and "AA and UA huge volumes affecting efficiency"
  // Neutral/Analytical with a hint of scale/potential issue. Using a blue-purple base with a vibrant cyan highlight.
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#4f46e5'; // Indigo for general bars (blue-purple for comparison/analysis)
  const highlightColorStart = '#22d3ee'; // Vibrant Cyan for highlighted bars (AA, UA)
  const highlightColorEnd = '#0ea5e9'; // Sky Blue for gradient end, creating a distinct pop
  const gridColor = '#333333'; // Subtle dark grey for grid lines
  const axisColor = '#888888'; // Lighter grey for axes

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItems = data.filter((d: any) => d[yField] === maxValue);
  const carriersToHighlight = ['AA', 'UA']; // As per narration keywords

  // D3 scales
  const chartWidth = 960; // Total SVG width is 960
  const chartHeight = 320; // Drawing area height, leaving space for title and critical subtitle zone (180px at bottom)

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth * 0.8]) // Use 80% of the SVG width for bars, centered
      .padding(0.4); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // 10% extra for top padding
      .range([chartHeight, 0]); // Inverted for SVG coordinates

    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight]);

  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');

    // Gradient for highlighted bars
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColorStart);
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorEnd);

    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    // Calculate margins for chart group to center it horizontally within the SVG
    const chartAreaWidth = scales.xScale.range()[1];
    const horizontalMargin = (chartWidth - chartAreaWidth) / 2;

    const g = svg.append('g').attr('transform', `translate(${horizontalMargin}, 40)`); // Y-offset 40px from SVG top to leave space for title

    // Y-axis grid lines
    const yAxisGrid = d3.axisLeft(scales.yScale)
      .tickSize(-chartAreaWidth)
      .tickFormat(() => "")
      .ticks(5);

    g.append('g')
      .attr('class', 'grid-y')
      .call(yAxisGrid)
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '4 4'); // Dashed grid lines for subtlety

    // Y-axis
    const yAxis = d3.axisLeft(scales.yScale)
      .ticks(5)
      .tickFormat((d: any) => `${d3.format(".2s")(d)}`); // Format numbers (e.g., 240K)

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    g.select('.y-axis').selectAll('path, line')
      .attr('stroke', axisColor);


    // Draw bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => scales.xScale(d[xField]) || 0)
      .attr('y', (d: any) => scales.yScale(d[yField]))
      .attr('width', scales.xScale.bandwidth())
      .attr('height', (d: any) => chartHeight - scales.yScale(d[yField]))
      .attr('fill', (d: any) => carriersToHighlight.includes(d[xField]) ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for aesthetics
      .attr('ry', 8)
      .style('filter', 'url(#barShadow)');

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (scales.xScale(d[xField]) || 0) + scales.xScale.bandwidth() / 2)
      .attr('y', (d: any) => scales.yScale(d[yField]) - 15) // Position above bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(".2s")(d[yField])) // Format numbers (e.g., 240K)
      .attr('fill', (d: any) => carriersToHighlight.includes(d[xField]) ? highlightColorStart : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Category labels below chart
    // CRITICAL: y-position <= 370px to reserve bottom 180px for subtitles
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (scales.xScale(d[xField]) || 0) + scales.xScale.bandwidth() / 2)
      .attr('y', chartHeight + 40) // Positioned 40px below the chart bars (chartHeight is 320)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, data, maxValue, xField, yField, textColor, barColor, highlightColorStart, highlightColorEnd, gridColor, axisColor, carriersToHighlight, chartHeight]);

  return (
    <AbsoluteFill style={{
      background: backgroundColor, // CRITICAL: MUST use JSON config value: #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to control spacing
      padding: '0px 40px' // Horizontal padding
    }}>
      {/* Title - Reserve top space */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top, leaving space for potential top subtitle line
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司乘客总数比较
      </div>

      {/* Chart - positioned below the title, with ample space for bottom subtitles */}
      <svg
        ref={svgRef}
        width={chartWidth}
        height={chartHeight + 110} // chartHeight (320) + title_offset(40) + label_offset(40) + safe_gap (30) = 430. Add 110 to 320 to accommodate axis and labels in the main svg
        style={{
          marginTop: '100px', // Pushes chart down, leaving top 80-100px for title/subtitle
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }}
      />

      {/* CRITICAL: BOTTOM 180px is reserved for subtitle overlay */}
      {/* DO NOT place any critical visual elements below y=540 (720-180=540) */}
      {/* Our chart elements end around y=320 (bars) + 40 (labels) = 360 within the SVG's G group. */}
      {/* SVG's top margin is 100px. So, 100 + 360 = 460px from canvas top. This is safe! */}
    </AbsoluteFill>
  );
};