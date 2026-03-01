import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_AnalysisCarrierDelayPerformance_20260217_155626ComponentAnimated: React.FC  = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "delay_type": "平均出发延误",
    "delay_value": 15.41
  },
  {
    "carrier": "AA",
    "delay_type": "平均到达延误",
    "delay_value": 9.48
  },
  {
    "carrier": "EV",
    "delay_type": "平均出发延误",
    "delay_value": 16.53
  },
  {
    "carrier": "EV",
    "delay_type": "平均到达延误",
    "delay_value": 12.76
  },
  {
    "carrier": "MQ",
    "delay_type": "平均出发延误",
    "delay_value": 33.98
  },
  {
    "carrier": "MQ",
    "delay_type": "平均到达延误",
    "delay_value": 38.98
  },
  {
    "carrier": "OO",
    "delay_type": "平均出发延误",
    "delay_value": 25.3
  },
  {
    "carrier": "OO",
    "delay_type": "平均到达延误",
    "delay_value": 26.06
  },
  {
    "carrier": "UA",
    "delay_type": "平均出发延误",
    "delay_value": 25.24
  },
  {
    "carrier": "UA",
    "delay_type": "平均到达延误",
    "delay_value": 15.6
  }
];
  
  // Data Binding configuration
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "delay_value",
      "label": "平均延误时间 (分钟)"
    },
    "color": {
      "field": "delay_type",
      "label": "延误类型",
      "domain": [
        "平均出发延误",
        "平均到达延误"
      ],
      "range": [
        "#5b8ff9", // Blue for departure delay
        "#5ad8a6"  // Green for arrival delay
      ]
    },
    "group": { // This indicates a grouped bar chart
      "field": "delay_type"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  const yAxisLabel = data_binding.y_axis.label;
  const colorField = data_binding.color.field;
  const colorDomain = data_binding.color.domain;
  const colorRange = data_binding.color.range;
  const groupField = data_binding.group.field;
  
  // Color configuration (MUST use #0f1419 for background)
  const backgroundColor = '#0f1419'; 
  // const containerBackground = '#0f1419'; // Not directly used in style but implies container background
  
  const textColor = '#e8eaed'; // Light text for dark background
  // Use the provided colorRange for the bars
  // Highlight color for "problem" / highest value (MQ)
  const highlightColor = '#ef4444'; // Red to signify highest delay/problem
  const gridColor = '#2d3748'; // Subtle grid color
  const axisColor = '#888888'; // Subtle axis color

  // Calculate metrics
  const allDelayValues = data.map((d: any) => d[yField]);
  const maxValue = d3.max(allDelayValues) || 0;
  // Identify the carrier with the highest delay for highlighting
  const highestDelayCarrier = data.find((d: any) => d[yField] === maxValue)?.carrier;

  // D3 scales and chart dimensions
  const width = 1100; // Total SVG width
  const height = 550; // Total SVG height
  // Margins adjusted for title (top 80-100px) and subtitle zone (bottom 180px)
  const margin = { top: 80, right: 60, bottom: 180, left: 90 }; 
  const innerWidth = width - margin.left - margin.right;
  // innerHeight is the actual chart drawing area, leaving space for subtitle
  const innerHeight = height - margin.top - margin.bottom - 40; // 40px additional gap above subtitle
  // innerHeight = 550 - 80 - 180 - 40 = 250px

  const scales = useMemo(() => {
    const carriers = Array.from(new Set(data.map(d => d[xField])));
    const delayTypes = Array.from(new Set(data.map(d => d[groupField])));

    const xScale = d3.scaleBand()
      .domain(carriers as string[])
      .range([0, innerWidth])
      .padding(0.2); // Padding between carrier groups

    const xSubgroup = d3.scaleBand()
      .domain(delayTypes as string[])
      .range([0, xScale.bandwidth()])
      .padding(0.05); // Padding between bars within a group

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Extend domain slightly above max value
      .range([innerHeight, 0]); // Y-axis range from bottom (innerHeight) to top (0)

    const colorScale = d3.scaleOrdinal<string>()
      .domain(colorDomain)
      .range(colorRange);

    return { xScale, xSubgroup, yScale, colorScale, carriers, delayTypes };
  }, [data, xField, groupField, maxValue, innerWidth, innerHeight, colorDomain, colorRange]);
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders
    
    // Define reusable styles for text clarity
    const textStyle = {
      'font-family': 'system-ui, -apple-system, sans-serif',
      '-webkit-font-smoothing': 'antialiased',
      'text-rendering': 'geometricPrecision'
    };

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Shadow filter (using feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    const { xScale, xSubgroup, yScale, colorScale, carriers, delayTypes } = scales;
    
    // Chart group, translated to respect margins
    const g = svg.append('g').attr('transform', `translate(${margin.left}, ${margin.top})`);
    
    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickFormat((d: any) => `${d3.format(".1f")(d)}`); // Format delay values to one decimal place
    
    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .call(g => g.select('.domain').remove()) // Remove the main axis line
      .call(g => g.selectAll('.tick line').attr('stroke', gridColor).attr('stroke-dasharray', '2,2')) // Grid lines
      .call(g => g.selectAll('.tick text')
        .attr('fill', axisColor)
        .style('font-size', '14px')
        .style(textStyle)
      );
    
    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // Positioned further left to prevent overlap with tick numbers
      .attr('y', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${innerHeight / 2})`) // Rotate around its own position
      .text(yAxisLabel)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '500')
      .style(textStyle);

    // Bars: grouped by carrier
    g.selectAll('.carrier-group')
      .data(carriers)
      .enter()
      .append('g')
      .attr('class', 'carrier-group')
      .attr('transform', d => `translate(${xScale(d)}, 0)`) // Translate each carrier group
      .selectAll('.bar')
      .data(carrier => data.filter(d => d[xField] === carrier)) // Bind data for each bar within group
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', d => xSubgroup(d[groupField]) || 0) // Position bar within subgroup
      .attr('y', d => yScale(d[yField]))
      .attr('width', xSubgroup.bandwidth())
      .attr('height', d => innerHeight - yScale(d[yField]))
      .attr('fill', d => colorScale(d[groupField]))
      .attr('rx', 4) // Rounded corners for bars
      .attr('ry', 4)
      .style('filter', d => d[xField] === highestDelayCarrier ? 'url(#shadow)' : 'none') // Apply shadow to highlighted carrier
      .attr('stroke', d => d[xField] === highestDelayCarrier ? highlightColor : 'none') // Red stroke for highlighted carrier
      .attr('stroke-width', d => d[xField] === highestDelayCarrier ? 2 : 0); // Stroke width for highlighted carrier

    // Value labels on top of bars
    g.selectAll('.carrier-group')
      .selectAll('.value-label')
      .data(carrier => data.filter(d => d[xField] === carrier))
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', d => (xSubgroup(d[groupField]) || 0) + xSubgroup.bandwidth() / 2)
      .attr('y', d => yScale(d[yField]) - 8) // Position 8px above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(".1f")(d[yField]))
      .attr('fill', d => d[xField] === highestDelayCarrier ? highlightColor : textColor) // Highlight label color
      .style('font-size', d => d[xField] === highestDelayCarrier ? '16px' : '14px') // Highlight label size
      .style('font-weight', d => d[xField] === highestDelayCarrier ? '700' : '500') // Highlight label weight
      .style(textStyle);

    // X-axis labels (Carrier names)
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${innerHeight})`) // Position X-axis at the bottom of chart area
      .call(d3.axisBottom(xScale).tickSizeOuter(0)) // No outer ticks
      .call(g => g.select('.domain').remove()) // Remove main axis line
      .call(g => g.selectAll('.tick line').remove()) // Remove tick lines
      .call(g => g.selectAll('.tick text')
        .attr('fill', textColor)
        .style('font-size', '15px')
        .style('font-weight', '500')
        .attr('y', 15) // Position labels below the actual axis line, safely above subtitle zone
        .style(textStyle)
      );
    
    // Legend for delay types
    const legend = g.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(${innerWidth - 250}, -40)`); // Position at top right of chart area

    legend.selectAll('.legend-item')
      .data(delayTypes)
      .enter()
      .append('g')
      .attr('class', 'legend-item')
      .attr('transform', (d, i) => `translate(0, ${i * 25})`) // Vertical spacing for legend items
      .each(function(d) {
        d3.select(this).append('rect')
          .attr('x', 0)
          .attr('y', -10)
          .attr('width', 18)
          .attr('height', 18)
          .attr('fill', colorScale(d))
          .attr('rx', 3); // Small rounded corners for legend swatches
        d3.select(this).append('text')
          .attr('x', 24)
          .attr('y', 5)
          .text(d)
          .attr('fill', textColor)
          .style('font-size', '14px')
          .style('font-weight', '400')
          .style(textStyle);
      });

  }, [scales, highestDelayCarrier, margin, innerWidth, innerHeight, textColor, highlightColor, gridColor, axisColor, yAxisLabel, data_binding.x_axis.label]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // MUST use JSON config value: #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0px 40px' // Horizontal padding for overall scene
    }}>
      {/* Title - positioned at the top, reserved top 80-100px */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top, well within 80-100px safe zone
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%', // Ensure title spans full width
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        航空公司平均延误表现对比
      </div>
      
      {/* Chart - centered, with space for labels and subtitle zone */}
      <svg 
        ref={svgRef} 
        width={width} 
        height={height} 
        style={{ 
          marginTop: '20px', // Push chart down slightly from title
          shapeRendering: 'geometricPrecision', // SVG clarity optimization
          textRendering: 'geometricPrecision' // SVG clarity optimization
        }} 
      />
      
      {/* IMPORTANT: No additional info cards or metrics here. 
          Data labels on chart elements are sufficient. 
          Highlight key data IN THE CHART with size/color/stroke. */}
    </AbsoluteFill>
  );
};