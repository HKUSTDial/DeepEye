import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisDestcityArrivalDelays_20260217_150441Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "destcity": "Boston",
    "avg_arrdelay": 12.52,
    "count": 385
  },
  {
    "destcity": "Dallas",
    "avg_arrdelay": 15.78,
    "count": 608
  },
  {
    "destcity": "Los Angeles",
    "avg_arrdelay": 5.13,
    "count": 514
  },
  {
    "destcity": "Minneapolis",
    "avg_arrdelay": 19.58,
    "count": 439
  },
  {
    "destcity": "New York",
    "avg_arrdelay": 15.04,
    "count": 769
  },
  {
    "destcity": "San Francisco",
    "avg_arrdelay": 13.05,
    "count": 459
  },
  {
    "destcity": "Washington",
    "avg_arrdelay": 13.95,
    "count": 583
  }
];
  
  // Data binding
  const data_binding = {
    "x_axis": {
      "field": "destcity",
      "label": "目的地城市"
    },
    "y_axis": {
      "field": "avg_arrdelay",
      "label": "平均延误时间 (分钟)"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string, label: string }).field; // y_axis is a DICT, so single field

  // Color configuration (CRITICAL: background colors are fixed from JSON config!)
  const backgroundColor = '#0f1419'; 
  const containerBackground = '#0f1419'; 
  
  // Scene-specific colors based on "delay" semantics (orange/red for problems/delays)
  const textColor = '#e8eaed'; 
  const barColor = '#f59e0b'; // Amber-orange for general delays
  const highlightColor = '#ef4444'; // Red for the longest delay (explicitly mentioned in narration)
  const gridColor = '#374151'; // Subtle dark gray for grids
  const axisColor = '#6b7280'; // Medium gray for axes and labels
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  // const maxItem = data.find((d: any) => d[yField] === maxValue); // Not directly used in rendering logic
  // const minValue = d3.min(data, (d: any) => d[yField]) || 0; // Not directly used in rendering logic

  // D3 scales
  const scales = useMemo(() => {
    const chartWidth = 800; // SVG width (960) - left margin (80) - right margin (80)
    const chartHeight = 400; // Max available height for bars, leaves space for labels and subtitle zone

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.2);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Give some room above the max bar for labels
      .range([chartHeight, 0]); // Invert Y-axis for SVG coordinates (0 at top, chartHeight at bottom)

    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, xField, yField, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Create gradient for the highlighted bar (from highlightColor to barColor)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor); 
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor); 
    
    // Shadow filter (CRITICAL: use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Draw chart with proper spacing
    // Translate 'g' to leave space for title (top 80-100px) and left/right margins
    const { xScale, yScale, chartWidth, chartHeight } = scales;
    const g = svg.append('g').attr('transform', 'translate(80, 80)'); 
    
    // Add Y-axis grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across the chart
        .tickFormat(() => "") // No labels for grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Add Y-axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5)) // 5 ticks for readability
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // CRITICAL: At least -70 to avoid overlap with tick numbers
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`) // Rotate around its new x,y
      .text(data_binding.y_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

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
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 6) // Rounded corners for aesthetics
      .style('filter', 'url(#shadow)');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12) // Position slightly above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(2) + '分钟') // Format to 2 decimal places and add unit
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', (d: any) => d[yField] === maxValue ? '20px' : '16px') // Larger for max value
      .style('font-weight', (d: any) => d[yField] === maxValue ? '800' : '500') // Bolder for max value
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels (X-axis tick labels) below chart
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`) // Position X-axis at the bottom of the chart drawing area
      .call(d3.axisBottom(xScale))
      .selectAll('text')
      .attr('fill', axisColor)
      .attr('y', 15) // Adjust position relative to axis line, ensures visibility
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // X-axis label
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', chartWidth / 2)
      .attr('y', chartHeight + 40) // Position X-axis label below tick labels.
                                   // This translates to 80 (g.translateY) + 400 (chartHeight) + 40 = 520px from SVG top.
                                   // With SVG marginTop 20px, it's 540px from AbsoluteFill top, leaving 180px for subtitles.
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', axisColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Select existing axis paths and lines and apply color (CRITICAL: correct selection method)
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);
    g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor);

  }, [scales, data, xField, yField, maxValue, barColor, highlightColor, textColor, gridColor, axisColor, data_binding]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0 40px' // Horizontal padding, vertical space managed by SVG/g transforms
    }}>
      {/* Title (positioned at top 30px, leaving ample space for subtitle overlay) */}
      <div style={{
        position: 'absolute',
        top: 30, 
        fontSize: '36px',
        fontWeight: '700',
        color: textColor, 
        textAlign: 'center',
        width: '100%', 
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各城市平均抵达延误时间
      </div>
      
      {/* Chart - centered, with space for labels and subtitle area */}
      <svg 
        ref={svgRef} 
        width={960} 
        height={550} // SVG height, positioned relative to AbsoluteFill
        style={{ 
          marginTop: '20px', // Pushes the SVG down, ensuring top 80-100px clear
          shapeRendering: 'geometricPrecision', // CRITICAL for SVG clarity
          textRendering: 'geometricPrecision' // CRITICAL for SVG clarity
        }} 
      />
    </AbsoluteFill>
  );
};