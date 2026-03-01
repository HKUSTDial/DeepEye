import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisPassengersByCarrier_20260217_145526Component: React.FC = () => {
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
  
  // Data Binding
  const data_binding = {
    "x_axis": {
      "field": "carrier",
      "label": "航空公司"
    },
    "y_axis": {
      "field": "sum_passengers",
      "label": "旅客总数"
    }
  };

  const xField = data_binding.x_axis.field;
  const yField = data_binding.y_axis.field;
  
  // Color configuration (MUST use JSON config values for background)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Scene semantics: "各航空公司旅客总数对比" (Comparison of total passengers for each airline)
  // Narration hints at "延误影响更为显著" (delay impact more significant) for larger carriers.
  // Choosing a blue/purple scheme for data analysis and magnitude, with purple highlight for impact/prominence.
  const textColor = '#e8eaed'; // Light grey for dark background
  const barColor = '#3b82f6'; // Blue for general data visualization
  const highlightColor = '#8b5cf6'; // Purple for highlighting the maximum value
  
  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // D3 scales
  const scales = useMemo(() => {
    // Chart drawing area dimensions within the SVG
    const chartWidth = 960 - 80 * 2; // SVG width (960) - left/right g margin (80*2) = 800
    // Max height for bars, ensuring category labels clear the bottom 180px subtitle zone
    const chartHeightForBars = 320; 

    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth])
      .padding(0.3); // Padding between bars

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Add 10% padding above max value for labels
      .range([chartHeightForBars, 0]); // Invert range for SVG (y=0 is top)
      
    return { xScale, yScale, chartWidth, chartHeightForBars };
  }, [data, xField, yField, maxValue]);
  
  // Static D3 rendering
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    const { xScale, yScale, chartHeightForBars } = scales;

    // Define gradients and shadow filters
    const defs = svg.append('defs');
    
    // Linear gradient for the highlighted bar (from highlightColor to a darker shade)
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColor);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', d3.color(highlightColor)?.darker(0.8).toString());
    
    // Drop shadow filter for bars (feDropShadow ensures original shape isn't blurred)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Main chart group, translated to provide margins
    const g = svg.append('g').attr('transform', 'translate(80, 40)'); // 80px left, 40px top margin

    // Draw bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => chartHeightForBars - yScale(d[yField]))
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8) // Rounded corners
      .attr('ry', 8)
      .style('filter', 'url(#shadow)'); // Apply shadow filter
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15) // Position 15px above the bar
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(',')(d[yField])) // Format numbers with commas
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Category labels below the chart (e.g., airline codes)
    // CRITICAL: Position `y` relative to `g` to ensure absolute position clears the bottom 180px subtitle zone.
    // Absolute Y position: (g_y_transform) + (label_y_in_g) = 40 + (chartHeightForBars + 40) = 40 + 320 + 40 = 400px.
    // Canvas height is 720px. 720 - 180 (subtitle zone) = 540px.
    // 400px < 540px, so this is safely above the subtitle zone.
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', chartHeightForBars + 40) // 40px below the highest bar point in chart area
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
  }, [scales, data, xField, yField, maxValue, barColor, highlightColor, textColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // Unified background from JSON config
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px' // Overall padding for the scene
    }}>
      {/* Scene Title - positioned at the top, allowing space for subtitles below */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top for title
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc', // Bright white for title readability
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司旅客总数对比
      </div>
      
      {/* D3 Chart Container */}
      <svg 
        ref={svgRef} 
        width={960} // Width of the SVG canvas
        height={550} // Height of the SVG canvas, accommodating chart and labels
        style={{ 
          marginTop: '20px', // Push chart down from the title
          shapeRendering: 'geometricPrecision', // Ensures crisp lines and shapes
          textRendering: 'geometricPrecision' // Ensures crisp text
        }} 
      />
    </AbsoluteFill>
  );
};