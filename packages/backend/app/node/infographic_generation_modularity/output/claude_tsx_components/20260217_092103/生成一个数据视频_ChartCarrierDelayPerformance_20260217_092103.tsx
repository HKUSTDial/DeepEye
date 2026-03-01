import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 生成一个数据视频_ChartCarrierDelayPerformance_20260217_092103Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);

  // Hardcoded data
  const data = [
    {
      "carrier": "AA",
      "metric": "平均出发延误",
      "value": 15.41
    },
    {
      "carrier": "AA",
      "metric": "平均到达延误",
      "value": 9.48
    },
    {
      "carrier": "EV",
      "metric": "平均出发延误",
      "value": 16.53
    },
    {
      "carrier": "EV",
      "metric": "平均到达延误",
      "value": 12.76
    },
    {
      "carrier": "MQ",
      "metric": "平均出发延误",
      "value": 33.98
    },
    {
      "carrier": "MQ",
      "metric": "平均到达延误",
      "value": 38.98
    },
    {
      "carrier": "OO",
      "metric": "平均出发延误",
      "value": 25.3
    },
    {
      "carrier": "OO",
      "metric": "平均到达延误",
      "value": 26.06
    },
    {
      "carrier": "UA",
      "metric": "平均出发延误",
      "value": 25.24
    },
    {
      "carrier": "UA",
      "metric": "平均到达延误",
      "value": 15.6
    }
  ];

  // Data binding fields
  const xField = "carrier";
  const groupField = "metric"; // For grouped bars
  const valueField = "value";

  // Color configuration - CRITICAL: Background colors are fixed!
  const backgroundColor = '#0f1419'; // MUST use JSON config value
  const containerBackground = '#0f1419'; // MUST use JSON config value

  // Scene-specific colors (Delays/Problems theme -> Red/Orange)
  const textColor = '#e8eaed'; // Light grey for dark background
  const barColorDepDelay = '#fb923c'; // Orange-400 for departure delay
  const barColorArrDelay = '#ef4444'; // Red-500 for arrival delay
  const highlightStartColor = '#f87171'; // Red-400 for highlight gradient start
  const highlightEndColor = '#dc2626'; // Red-600 for highlight gradient end
  const highlightTextColor = '#fecaca'; // Red-200 for highlight text
  const gridColor = '#333333'; // Dark grey, very subtle
  const axisColor = '#777777'; // Medium grey, subtle

  // Highlight specific data point (MQ's average arrival delay)
  const highlightCarrier = "MQ";
  const highlightMetric = "平均到达延误";

  // D3 scales and chart dimensions
  const chartWidth = 900; // Adjusted for 1100px SVG width and 100px side margins
  const chartHeight = 360; // Adjusted to leave 180px for subtitles at bottom
  const svgWidth = 1100;
  const svgHeight = 460; // Chart height + padding for x-axis labels

  const scales = useMemo(() => {
    const uniqueCarriers = Array.from(new Set(data.map(d => d[xField])));
    const uniqueMetrics = Array.from(new Set(data.map(d => d[groupField])));

    const xScale = d3.scaleBand()
      .domain(uniqueCarriers as string[])
      .range([0, chartWidth])
      .padding(0.2);

    const xSubgroup = d3.scaleBand()
      .domain(uniqueMetrics as string[])
      .range([0, xScale.bandwidth()])
      .padding(0.05);

    const maxValue = d3.max(data, (d: any) => d[valueField]) || 0;
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.15]) // Add a little extra space above max value for labels
      .range([chartHeight, 0]);

    return { xScale, xSubgroup, yScale, uniqueMetrics };
  }, [data]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear SVG contents

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');

    // Highlight gradient for the specific bar (MQ Arrival Delay)
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', highlightStartColor);
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightEndColor);

    // Shadow filter (using feDropShadow to avoid blur)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    const { xScale, xSubgroup, yScale, uniqueMetrics } = scales;

    // Main chart group, positioned to allow space for title and margins
    const g = svg.append('g').attr('transform', `translate(100, 0)`); // Y-offset handled by SVG margin-top

    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat(d => `${d}分钟`); // Format as "X分钟"

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .call(axisG => axisG.select(".domain").remove()) // Remove axis line
      .call(axisG => axisG.selectAll(".tick line").attr("stroke", gridColor).attr("stroke-dasharray", "4 4")) // Grid lines
      .call(axisG => axisG.selectAll("text").attr("fill", axisColor).style('font-size', '14px')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision')
      );

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // Adjusted to avoid overlap with tick labels
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`)
      .text('平均延误时间 (分钟)')
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Bars
    uniqueCarriers.forEach(carrier => {
      const carrierData = data.filter(d => d[xField] === carrier);

      g.selectAll(`.bar-${carrier}`)
        .data(carrierData)
        .enter()
        .append('rect')
        .attr('class', (d: any) => `bar-${d[groupField].replace(/\s/g, '-')}`) // Clean class name
        .attr('x', (d: any) => xScale(d[xField])! + xSubgroup(d[groupField])!)
        .attr('y', (d: any) => yScale(d[valueField]))
        .attr('width', xSubgroup.bandwidth())
        .attr('height', (d: any) => chartHeight - yScale(d[valueField]))
        .attr('fill', (d: any) =>
          (d[xField] === highlightCarrier && d[groupField] === highlightMetric)
            ? 'url(#highlightGradient)'
            : (d[groupField] === "平均出发延误" ? barColorDepDelay : barColorArrDelay)
        )
        .attr('rx', 4) // Rounded corners for bars
        .style('filter', 'url(#barShadow)'); // Apply shadow

      // Value labels on top of bars
      g.selectAll(`.value-label-${carrier}`)
        .data(carrierData)
        .enter()
        .append('text')
        .attr('class', 'value-label')
        .attr('x', (d: any) => xScale(d[xField])! + xSubgroup(d[groupField])! + xSubgroup.bandwidth() / 2)
        .attr('y', (d: any) => yScale(d[valueField]) - 10)
        .attr('text-anchor', 'middle')
        .text((d: any) => `${d[valueField].toFixed(2)}`)
        .attr('fill', (d: any) =>
          (d[xField] === highlightCarrier && d[groupField] === highlightMetric)
            ? highlightTextColor
            : textColor
        )
        .style('font-size', '16px')
        .style('font-weight', '700')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });

    // X-axis labels (Carrier names)
    // CRITICAL: Y position adjusted to leave 180px for subtitle zone
    g.selectAll('.carrier-label')
      .data(uniqueCarriers)
      .enter()
      .append('text')
      .attr('class', 'carrier-label')
      .attr('x', (d: any) => xScale(d)! + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 35) // Position below bars, within SVG height
      .attr('text-anchor', 'middle')
      .text(d => d)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Legend
    const legend = g.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(${chartWidth - 200}, 20)`); // Position legend top right

    uniqueMetrics.forEach((metric, i) => {
      const legendColor = metric === "平均出发延误" ? barColorDepDelay : barColorArrDelay;
      const legendItem = legend.append('g')
        .attr('transform', `translate(0, ${i * 25})`);

      legendItem.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', 15)
        .attr('height', 15)
        .attr('fill', legendColor)
        .attr('rx', 3);

      legendItem.append('text')
        .attr('x', 25)
        .attr('y', 12)
        .text(metric)
        .attr('fill', textColor)
        .style('font-size', '14px')
        .style('font-weight', '500')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });

  }, [scales, highlightCarrier, highlightMetric, highlightStartColor, highlightEndColor, barColorDepDelay, barColorArrDelay, textColor, highlightTextColor, gridColor, axisColor, chartHeight, chartWidth]);

  return (
    <AbsoluteFill style={{
      background: backgroundColor, // CRITICAL: Use JSON config value
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '0px', // Adjusted to manage spacing with SVG margin-top
    }}>
      {/* Title - positioned at top, respecting 80px clearance */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top, leaves ~50px for top padding
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均出发与到达延误对比
      </div>

      {/* Chart - centered, with space for labels and subtitle overlay */}
      <svg
        ref={svgRef}
        width={svgWidth}
        height={svgHeight}
        style={{
          marginTop: '80px', // Push SVG down to account for title and top space
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision',
          overflow: 'visible' // Allow elements to draw outside SVG boundary if needed (e.g. shadows)
        }}
      />
    </AbsoluteFill>
  );
};