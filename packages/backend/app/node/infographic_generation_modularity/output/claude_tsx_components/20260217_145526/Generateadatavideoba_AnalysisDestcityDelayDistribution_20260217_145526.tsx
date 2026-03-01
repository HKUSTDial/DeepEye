import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisDestcityDelayDistribution_20260217_145526Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);

  // Hardcoded data
  const data = [
    { "destcity": "Boston", "avg_arrdelay": 12.52, "count": 385 },
    { "destcity": "Dallas", "avg_arrdelay": 15.78, "count": 608 },
    { "destcity": "Los Angeles", "avg_arrdelay": 5.13, "count": 514 },
    { "destcity": "Minneapolis", "avg_arrdelay": 19.58, "count": 439 },
    { "destcity": "New York", "avg_arrdelay": 15.04, "count": 769 },
    { "destcity": "San Francisco", "avg_arrdelay": 13.05, "count": 459 },
    { "destcity": "Washington", "avg_arrdelay": 13.95, "count": 583 }
  ];

  // Data binding configuration
  const xField = "destcity";
  const yField = "avg_arrdelay";
  const yAxisLabel = "平均延误时间 (分钟)";

  // Color configuration (CRITICAL: background colors from JSON config - DO NOT CHANGE!)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';

  // Scene-specific colors based on "delays" semantics
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#f97316'; // Orange for general delays
  const highlightColorWorst = '#dc2626'; // Red for highest delay (Minneapolis)
  const highlightColorBest = '#10b981'; // Green for lowest delay (Los Angeles)
  const gridColor = '#374151'; // Subtle dark grey for grid lines
  const axisColor = '#6b7280'; // Medium grey for axis lines and ticks

  // Calculate key metrics for highlighting
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  const minItem = data.find((d: any) => d[yField] === minValue);

  // Chart dimensions for D3 calculations
  const svgWidth = 1000; // Total SVG width
  const svgHeight = 550; // Total SVG height
  const chartMargin = { top: 80, right: 20, bottom: 60, left: 80 }; // Internal margins for chart group
  const chartWidth = svgWidth - chartMargin.left - chartMargin.right;
  const chartHeight = 320; // D3 drawing area height (adjusted to leave space for subtitles)

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% buffer for visual appeal
      .range([chartHeight, 0]);

    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight, xField]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const defs = svg.append('defs');

    // Gradient for the highest delay bar (red)
    const worstGradient = defs.append('linearGradient')
      .attr('id', 'worstGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    worstGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColorWorst)?.brighter(0.5).toString() || highlightColorWorst);
    worstGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorWorst);

    // Gradient for the lowest delay bar (green)
    const bestGradient = defs.append('linearGradient')
      .attr('id', 'bestGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    bestGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(highlightColorBest)?.brighter(0.5).toString() || highlightColorBest);
    bestGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorBest);

    // Gradient for general bars (orange)
    const generalGradient = defs.append('linearGradient')
      .attr('id', 'generalGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    generalGradient.append('stop').attr('offset', '0%').attr('stop-color', d3.color(barColor)?.brighter(0.5).toString() || barColor);
    generalGradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);

    // Shadow filter (using feDropShadow to avoid blurring the shape itself)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    // Main chart group, centered within the SVG
    const g = svg.append('g').attr('transform', `translate(${chartMargin.left}, ${chartMargin.top})`);

    const { xScale, yScale } = scales;

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `${d}min`))
      .selectAll('text')
      .style('font-size', '14px')
      .attr('fill', axisColor)
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -chartMargin.left + 20) // Positioned further left to avoid overlap
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, ${-chartMargin.left + 20}, ${chartHeight / 2})`)
      .text(yAxisLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Horizontal grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across chart width
        .tickFormat(() => '') // No labels for grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');
    g.select('.grid-y').select('path').remove(); // Remove the domain line of the grid

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
      .attr('fill', (d: any) => {
        if (d[xField] === maxItem?.[xField]) return 'url(#worstGradient)';
        if (d[xField] === minItem?.[xField]) return 'url(#bestGradient)';
        return 'url(#generalGradient)';
      })
      .attr('rx', 8) // Rounded corners for bars
      .attr('ry', 8)
      .style('filter', 'url(#shadow)'); // Apply shadow

    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => `${d[yField].toFixed(1)}min`)
      .attr('fill', (d: any) => {
        if (d[xField] === maxItem?.[xField]) return highlightColorWorst;
        if (d[xField] === minItem?.[xField]) return highlightColorBest;
        return textColor;
      })
      .style('font-size', '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Category labels (X-axis) below chart
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 35) // Position below bars, safely above the subtitle zone
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, minValue, maxItem, minItem, chartWidth, chartHeight, barColor, highlightColorWorst, highlightColorBest, textColor, gridColor, axisColor, xField, yField, yAxisLabel, chartMargin.left, chartMargin.top]);

  return (
    <AbsoluteFill style={{
      background: backgroundColor, // CRITICAL: Uses JSON config value #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to start to explicitly manage vertical space
      padding: '0 40px' // Horizontal padding for AbsoluteFill
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top for title
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%', // Ensure title spans full width for centering
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision',
        zIndex: 10, // Ensure title is above chart if any overlap
      }}>
        不同目的地城市的平均抵达延误
      </div>

      {/* Chart SVG container */}
      <svg
        ref={svgRef}
        width={svgWidth}
        height={svgHeight}
        style={{
          marginTop: '80px', // Push chart down to leave space for title and top margin
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }}
      />
    </AbsoluteFill>
  );
};