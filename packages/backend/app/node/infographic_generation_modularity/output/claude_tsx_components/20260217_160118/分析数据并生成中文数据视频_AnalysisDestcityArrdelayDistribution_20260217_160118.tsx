import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const 分析数据并生成中文数据视频_AnalysisDestcityArrdelayDistribution_20260217_160118Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "destcity": "Minneapolis",
    "avg_arrdelay": 19.58,
    "count": 439
  },
  {
    "destcity": "Dallas",
    "avg_arrdelay": 15.78,
    "count": 608
  },
  {
    "destcity": "New York",
    "avg_arrdelay": 15.04,
    "count": 769
  },
  {
    "destcity": "Washington",
    "avg_arrdelay": 13.95,
    "count": 583
  },
  {
    "destcity": "San Francisco",
    "avg_arrdelay": 13.05,
    "count": 459
  },
  {
    "destcity": "Boston",
    "avg_arrdelay": 12.52,
    "count": 385
  },
  {
    "destcity": "Los Angeles",
    "avg_arrdelay": 5.13,
    "count": 514
  }
];
  
  // Data binding from prompt
  const data_binding = {
    "x_axis": {
      "field": "destcity",
      "label": "目的地城市"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均到达延误 (分钟)"
    }
  };

  const xField = data_binding.x_axis?.field || 'destcity';
  const yField = data_binding.y_axis?.field || 'avg_arrdelay';
  
  // Sort data by avg_arrdelay in ascending order to highlight Los Angeles at one end
  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => (a as any)[yField] - (b as any)[yField]);
  }, [data, yField]);

  // Color configuration (CRITICAL: Background colors are fixed!)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419'; // Unused, but keep for consistency with prompt
  
  // Scene-specific colors based on "delays" (negative) but highlighting a "punctual" (positive) outlier
  const textColor = '#e8eaed'; 
  const barColor = '#ef4444'; // Red for general delays
  const highlightColor = '#22c55e'; // Green for the lowest delay (Los Angeles)
  const gridColor = '#444444'; 
  const axisColor = '#777777'; 
  
  // Calculate metrics
  const maxValue = d3.max(sortedData, (d: any) => d[yField]) || 0;
  const lowestDelayCity = sortedData[0][xField]; // Los Angeles after sorting
  
  const scales = useMemo(() => {
    const chartWidth = 960;
    const chartHeight = 320; // Max height for the chart drawing area, reserving 180px for subtitles
    const marginLeft = 80;
    const marginRight = 80;

    const xScale = d3.scaleBand()
      .domain(sortedData.map((d: any) => d[xField]))
      .range([0, chartWidth - marginLeft - marginRight])
      .padding(0.2);
      
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Add some padding above max value
      .range([chartHeight, 0]);
      
    return { xScale, yScale, chartWidth, chartHeight, marginLeft, marginRight };
  }, [sortedData, xField, yField, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Define SVG dimensions and margins
    const { xScale, yScale, chartWidth, chartHeight, marginLeft, marginRight } = scales;

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Chart group, positioned to allow for title and bottom subtitle space
    const g = svg.append('g').attr('transform', `translate(${marginLeft + 40}, 100)`); // Shift down to allow title, and right for Y-axis label

    // Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-(xScale.range()[1])) // Extend grid lines across chart width
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d => `${d} min`))
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px');

    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);

    // Y-axis label
    g.append('text')
      .attr('x', -70) // CRITICAL: At least -70 to avoid overlap with tick numbers!
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`) 
      .text(data_binding.y_axis.label)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Draw bars (highlight lowest delay city with accent color)
    g.selectAll('.bar')
      .data(sortedData)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => chartHeight - yScale(d[yField]))
      .attr('fill', (d: any) => d[xField] === lowestDelayCity ? highlightColor : barColor)
      .attr('rx', 6) // Rounded corners for aesthetics
      .style('filter', (d: any) => d[xField] === lowestDelayCity ? 'url(#shadow)' : 'none');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(sortedData)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 10) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2)) // Format to 2 decimal places
      .attr('fill', (d: any) => d[xField] === lowestDelayCity ? highlightColor : textColor)
      .style('font-size', '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart
    // CRITICAL: y must be <= 370 to leave bottom 180px for subtitle overlay
    g.selectAll('.category-label')
      .data(sortedData)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 30) // Position category labels below the bars
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, sortedData, xField, yField, lowestDelayCity, highlightColor, barColor, textColor, gridColor, axisColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to start to control top padding better
      padding: '0px 40px' // Horizontal padding
    }}>
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: 30, // Positioned at top 30px, leaving space
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision',
      }}>
        目的地城市平均到达延误分布
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={1280} // Full width to position the chart group
        height={720} // Full height to control internal elements
        style={{ 
          marginTop: '20px', // Adjusted to fit title and overall layout
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};