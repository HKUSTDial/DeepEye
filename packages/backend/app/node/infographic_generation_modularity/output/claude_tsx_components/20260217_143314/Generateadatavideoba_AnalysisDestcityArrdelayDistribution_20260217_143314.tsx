import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisDestcityArrdelayDistribution_20260217_143314Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "destcity": "明尼阿波利斯",
    "avg_arrdelay": 120.33
  },
  {
    "destcity": "波士顿",
    "avg_arrdelay": -4.38
  },
  {
    "destcity": "华盛顿",
    "avg_arrdelay": -9.0
  },
  {
    "destcity": "纽约",
    "avg_arrdelay": -9.2
  },
  {
    "destcity": "洛杉矶",
    "avg_arrdelay": -12.17
  },
  {
    "destcity": "旧金山",
    "avg_arrdelay": -22.0
  }
];
  
  // Extract field names from data_binding
  const xField = "destcity";
  const yField = "avg_arrdelay";
  
  // Color configuration (MUST use fixed background, other colors chosen based on scene semantics)
  const backgroundColor = '#0f1419'; // CRITICAL: DO NOT CHANGE - from JSON config
  const containerBackground = '#0f1419'; // CRITICAL: DO NOT CHANGE - from JSON config
  
  const textColor = '#e8eaed'; // Light text for dark background
  const delayColor = '#f97316'; // Vibrant orange for delays
  const earlyColor = '#38bdf8'; // Sky blue for early arrivals
  const highlightDelayColor = '#fbbf24'; // Amber for the highest delay (Minneapolis)
  const gridColor = '#333333'; // Subtle grid lines
  const axisColor = '#666666'; // Subtle axis lines

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // D3 scales
  const scales = useMemo(() => {
    // Chart dimensions within the SVG
    // SVG total height is 460 (720 - 80px top reserve - 180px bottom reserve)
    // g transform translate(80, 20) means 20px top padding inside SVG, 80px left padding
    const chartWidth = 960 - 80 * 2; // 800px
    const chartHeight = 460 - 20 - 20; // 420px (leaving space for x-axis labels at bottom)
    
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2); // Padding between bars
    
    const yScale = d3.scaleLinear()
      .domain([minValue * 1.1, maxValue * 1.1]) // Add padding to min/max values
      .range([chartHeight, 0]); // Invert range for SVG coordinates (y=0 is top)
      
    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, maxValue, minValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders
    
    const { xScale, yScale, chartWidth, chartHeight } = scales;

    // Define SVG filters for shadow
    const defs = svg.append('defs');
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    // Main chart group, translated to leave margins
    // CRITICAL: svg top: 80, g transform translate(80, 20)
    // Lowest content y (relative to g) should be <= 440 (20 + 420 (chartHeight) + 20 (x-axis labels))
    const g = svg.append('g').attr('transform', 'translate(80, 20)');

    // Add X-axis (line at y=0) - no actual axis line, just the category labels
    // We'll draw a horizontal line at yScale(0) to represent the zero-delay line
    g.append('line')
      .attr('x1', 0)
      .attr('y1', yScale(0))
      .attr('x2', chartWidth)
      .attr('y2', yScale(0))
      .attr('stroke', axisColor)
      .attr('stroke-width', 1);

    // Add Y-axis grid lines and labels
    const yAxis = d3.axisLeft(yScale)
      .ticks(5)
      .tickSizeInner(-chartWidth)
      .tickSizeOuter(0)
      .tickFormat((d: any) => `${d} min`);

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .call(g => g.select('.domain').remove()) // Remove the axis line
      .call(g => g.selectAll('.tick line').attr('stroke-opacity', 0.2).attr('stroke', gridColor))
      .call(g => g.selectAll('.tick text')
        .attr('fill', axisColor)
        .style('font-size', '14px')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision')
      );

    // Draw bars for positive and negative values
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => d[yField] >= 0 ? yScale(d[yField]) : yScale(0)) // Start from top for positive, from zero for negative
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => Math.abs(yScale(d[yField]) - yScale(0)))
      .attr('fill', (d: any) => {
        if (d === maxItem) return highlightDelayColor; // Highest delay
        return d[yField] > 0 ? delayColor : earlyColor; // Other delays vs. early arrivals
      })
      .attr('rx', 8) // Rounded corners
      .style('filter', (d: any) => d === maxItem ? 'url(#shadow)' : 'none'); // Shadow only for the highlighted bar

    // Value labels on top/bottom of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => d[yField] >= 0 ? yScale(d[yField]) - 10 : yScale(d[yField]) + 20) // Above for positive, below for negative
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(1))
      .attr('fill', (d: any) => d === maxItem ? highlightDelayColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Category labels (X-axis labels)
    // CRITICAL: Position at y <= 440 (relative to g) to reserve bottom 180px for subtitles
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 20) // Position below the chart area
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, maxValue, minValue, maxItem, textColor, delayColor, earlyColor, highlightDelayColor, gridColor, axisColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value: #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align items to the start to precisely control SVG position
      padding: '0 40px' // Horizontal padding
    }}>
      {/* Title - positioned at the top, within the 80px subtitle-safe zone */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from the absolute top
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        width: '100%',
      }}>
        按目的地城市平均到达延误
      </div>
      
      {/* Chart - positioned absolutely to fit within the 80px to 540px vertical range */}
      <svg 
        ref={svgRef} 
        width={960} // Total width of the SVG
        height={460} // CRITICAL: SVG height (720 - 80px top - 180px bottom = 460px)
        style={{ 
          position: 'absolute',
          top: 80, // CRITICAL: positioned at 80px from absolute top
          left: '50%',
          transform: 'translateX(-50%)', // Center horizontally
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};