import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideo_AnalysisDestcityArrdelayDistribution_20260217_133136Component: React.FC = () => {
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
  
  // Data binding configuration
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

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field; // Single y_axis field

  // Color configuration (CRITICAL: MUST use these background colors from JSON config)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Scene-specific colors (chosen based on "delays" semantic)
  const textColor = '#e8eaed'; 
  const barColor = '#ef4444';   // Red for delays
  const highlightColor = '#dc2626'; // Darker red for emphasis
  const gridColor = '#4a4e53';  // Subtle dark grey
  const axisColor = '#888888';  // Medium grey

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  const minItem = data.find((d: any) => d[yField] === minValue);
  
  // D3 scales
  const scales = useMemo(() => {
    const chartWidth = 900; // Adjusted for 960 total width with 30px padding
    const chartHeight = 320; // Max height for bars, leaving room for labels and subtitle zone
    
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.2]) // Give some extra room above max value
      .range([chartHeight, 0]);

    return { xScale, yScale, chartWidth, chartHeight };
  }, [data, xField, yField, maxValue]);
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const { xScale, yScale, chartWidth, chartHeight } = scales;

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');
    
    // Gradient for the highlighted bar (max delay)
    const gradient = defs.append('linearGradient')
      .attr('id', 'delayGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', barColor);
    
    // Shadow filter (using feDropShadow to avoid blur)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 6)
      .attr('stdDeviation', 8)
      .attr('flood-opacity', 0.4);
    
    // Draw chart group, positioned to allow space for title and subtitle
    const g = svg.append('g').attr('transform', 'translate(30, 80)'); // Shift chart down to leave space for title

    // Y-axis
    const yAxis = d3.axisLeft(yScale)
      .tickSizeOuter(0)
      .tickFormat((d) => `${d} min`); // Add 'min' suffix

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .call(g => g.select('.domain').remove()) // Remove the axis line
      .selectAll('text')
      .style('font-size', '14px')
      .style('fill', axisColor)
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.selectAll('.y-axis .tick line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2'); // Dashed grid lines

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -70) // CRITICAL: Position far left to avoid overlap
      .attr('y', chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -70, ${chartHeight / 2})`)
      .text(data_binding.y_axis.label)
      .style('font-size', '16px')
      .style('fill', textColor)
      .style('font-weight', '500')
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
      .attr('fill', (d: any) => {
        if (d[yField] === maxValue) return 'url(#delayGradient)';
        if (d[yField] === minValue) return '#20c997'; // A contrasting green for "best performer" (lowest delay)
        return barColor;
      })
      .attr('rx', 8) // Rounded corners
      .style('filter', (d: any) => (d[yField] === maxValue || d[yField] === minValue) ? 'url(#barShadow)' : 'none');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 12) // Position above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField].toFixed(1)) // Format to one decimal place
      .attr('fill', (d: any) => {
        if (d[yField] === maxValue) return highlightColor;
        if (d[yField] === minValue) return '#20c997';
        return textColor;
      })
      .style('font-size', '16px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below chart
    // CRITICAL: y position <= 370 to reserve bottom 180px for subtitle
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeight + 40) // Positioned relative to chartHeight, within the safe zone
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [scales, barColor, highlightColor, textColor, gridColor, axisColor, xField, yField, maxValue, minValue, maxItem, minItem]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to control spacing
      padding: '0 40px' // Horizontal padding
    }}>
      {/* Title (reserved top 30-80px) */}
      <div style={{
        position: 'absolute',
        top: 30, // Top 30px
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Consistent bright text for titles
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各目的地城市平均到达延误
      </div>
      
      {/* Chart - centered, with space for labels */}
      <svg 
        ref={svgRef} 
        width={960} // Total SVG width
        height={550} // Total SVG height, positioned below title, leaving bottom space
        style={{ 
          marginTop: '0px', // Managed by absolute positioning of title and overall flexbox for main content
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }} 
      />
    </AbsoluteFill>
  );
};