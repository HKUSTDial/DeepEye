import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideoba_AnalysisCarrierDelayComparison_20260217_145526ComponentAnimated: React.FC  = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  {
    "carrier": "AA",
    "delay_type": "平均出发延误",
    "value": 15.41
  },
  {
    "carrier": "AA",
    "delay_type": "平均到达延误",
    "value": 9.48
  },
  {
    "carrier": "EV",
    "delay_type": "平均出发延误",
    "value": 16.53
  },
  {
    "carrier": "EV",
    "delay_type": "平均到达延误",
    "value": 12.76
  },
  {
    "carrier": "MQ",
    "delay_type": "平均出发延误",
    "value": 33.98
  },
  {
    "carrier": "MQ",
    "delay_type": "平均到达延误",
    "value": 38.98
  },
  {
    "carrier": "OO",
    "delay_type": "平均出发延误",
    "value": 25.3
  },
  {
    "carrier": "OO",
    "delay_type": "平均到达延误",
    "value": 26.06
  },
  {
    "carrier": "UA",
    "delay_type": "平均出发延误",
    "value": 25.24
  },
  {
    "carrier": "UA",
    "delay_type": "平均到达延误",
    "value": 15.6
  }
];
  
  // Data Binding fields
  const xField = "carrier";
  const yField = "value";
  const seriesField = "delay_type"; // Used for grouping bars within each xField category
  
  // Color configuration - CRITICAL: Background colors from JSON config (DO NOT change!)
  const backgroundColor = '#0f1419';
  const containerBackground = '#0f1419';
  
  // Other colors: Chosen based on scene semantics (delays/problems -> red/orange scheme)
  const textColor = '#e8eaed'; // Light text for dark background
  const gridColor = '#444444'; // Subtle grid lines
  const axisColor = '#777777'; // Subtle axis lines and ticks

  // Theme colors for "Delays/Problems" - different shades for departure vs. arrival
  const barColorDeparture = '#f97316'; // Orange for departure delays
  const barColorArrival = '#ef4444';   // Red for arrival delays
  
  // Highlight colors based on narration: MQ has highest, AA performs best
  const highlightColorWorstBar = '#dc2626'; // Darker Red for MQ's highest bar fill
  const highlightGradientWorstStart = '#ff6b6b'; // Brighter red for gradient top (MQ)
  const highlightGradientWorstEnd = '#dc2626';   // Darker red for gradient bottom (MQ)
  
  const highlightColorBestBorder = '#3b82f6'; // Light Blue border for AA's best bar
  const highlightColorBestText = '#60a5fa';   // Light Blue text for AA's best label

  // Calculate metrics for highlighting specific data points
  const maxDelayItem = useMemo(() => {
    // Narration: "MQ的平均出发和到达延误最高，尤其到达延误近39分钟"
    return data.find(d => d.carrier === "MQ" && d.delay_type === "平均到达延误");
  }, [data]);

  const minArrivalDelayItem = useMemo(() => {
    // Narration: "AA表现最佳" -> assume lowest arrival delay
    return data.find(d => d.carrier === "AA" && d.delay_type === "平均到达延误");
  }, [data]);
  
  const allValues = data.map(d => d.value);
  const maxValue = d3.max(allValues) || 0; // Max value across all bars for Y-scale domain
  
  // D3 scales
  const scales = useMemo(() => {
    const carriers = Array.from(new Set(data.map(d => d[xField]))); // Unique carriers for main groups
    const delayTypes = Array.from(new Set(data.map(d => d[seriesField]))); // Unique delay types for sub-groups

    // Chart dimensions within the SVG for proper spacing (refer to space management guidelines)
    const chartWidth = 960 - 80 - 40; // SVG width (960) - left margin (80) - right margin (40)
    const chartHeight = 550 - 40 - 180; // SVG height (550) - top margin (40) - bottom margin (180 for subtitles)

    const xScale = d3.scaleBand()
      .domain(carriers)
      .range([0, chartWidth])
      .padding(0.2); // Padding between carrier groups

    const xSubgroupScale = d3.scaleBand()
      .domain(delayTypes)
      .range([0, xScale.bandwidth()])
      .padding(0.05); // Padding between bars within a carrier group

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // Y-axis from 0 to slightly above max value
      .range([chartHeight, 0]); // Y-axis maps to chart height (inverted for SVG)
      
    return { xScale, xSubgroupScale, yScale, chartWidth, chartHeight, delayTypes };
  }, [data, xField, seriesField, maxValue]);
  
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous renders
    
    const { xScale, xSubgroupScale, yScale, chartWidth, chartHeight, delayTypes } = scales;
    
    // Define gradients and filters in <defs>
    const defs = svg.append('defs');
    
    // Gradient for the worst delay bar (MQ arrival delay)
    const worstDelayGradient = defs.append('linearGradient')
      .attr('id', 'worstDelayGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    worstDelayGradient.append('stop').attr('offset', '0%').attr('stop-color', highlightGradientWorstStart);
    worstDelayGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightGradientWorstEnd);
    
    // Shadow filter (using feDropShadow to avoid blurring the entire shape)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0) // Horizontal offset
      .attr('dy', 4) // Vertical offset
      .attr('stdDeviation', 6) // Blur amount
      .attr('flood-opacity', 0.3); // Shadow opacity
    
    // Main group for the chart, translated to apply margins
    const g = svg.append('g').attr('transform', 'translate(80, 40)'); // Left margin 80, Top margin 40

    // X-axis (Carrier labels)
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartHeight})`) // Position at bottom of chart area
      .call(d3.axisBottom(xScale).tickSizeOuter(0)) // No outer ticks
      .selectAll('text')
      .attr('transform', 'translate(0, 10)') // Adjust label position 10px below axis line
      .style('font-size', '16px')
      .style('fill', axisColor)
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Style X-axis line and ticks
    g.select('.x-axis').select('.domain').attr('stroke', axisColor);
    g.select('.x-axis').selectAll('.tick line').attr('stroke', axisColor);

    // Y-axis (Delay time in minutes)
    const yAxis = d3.axisLeft(yScale)
      .ticks(5) // Approximately 5 ticks
      .tickFormat(d => `${d} 分钟`); // Format as "X 分钟"

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .style('font-size', '14px')
      .style('fill', axisColor)
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    // Style Y-axis line and grid lines
    g.select('.y-axis').select('.domain').attr('stroke', axisColor);
    g.select('.y-axis').selectAll('.tick line').attr('stroke', gridColor).attr('stroke-dasharray', '4 4'); // Dashed grid lines

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -60) // Positioned to avoid overlap with tick numbers
      .attr('y', chartHeight / 2) // Centered vertically
      .attr('text-anchor', 'middle')
      .attr('transform', `rotate(-90, -60, ${chartHeight / 2})`) // Rotate for vertical label
      .text('平均延误时间 (分钟)')
      .style('font-size', '16px')
      .style('fill', textColor)
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Draw grouped bars for each delay type
    delayTypes.forEach((delayType: string) => {
      g.selectAll(`.bar-${delayType.replace(/\s/g, '-')}`) // Replace spaces for valid class name
        .data(data.filter(d => d[seriesField] === delayType)) // Filter data for current delay type
        .enter()
        .append('rect')
        .attr('class', `bar-${delayType.replace(/\s/g, '-')}`)
        .attr('x', (d: any) => xScale(d[xField])! + xSubgroupScale(d[seriesField])!) // X position for subgroup bar
        .attr('y', (d: any) => yScale(d[yField])) // Y position based on value
        .attr('width', xSubgroupScale.bandwidth()) // Width of subgroup bar
        .attr('height', (d: any) => chartHeight - yScale(d[yField])) // Height of bar
        .attr('fill', (d: any) => {
          if (d.carrier === maxDelayItem?.carrier && d.delay_type === maxDelayItem?.delay_type) {
            return 'url(#worstDelayGradient)'; // Fill with gradient for MQ's highest
          }
          return delayType === '平均出发延误' ? barColorDeparture : barColorArrival; // Default colors
        })
        .attr('rx', 4) // Rounded corners
        .style('filter', (d: any) => {
          if (d.carrier === maxDelayItem?.carrier && d.delay_type === maxDelayItem?.delay_type) {
            return 'url(#shadow)'; // Apply shadow for MQ's highest
          }
          return 'none';
        })
        .attr('stroke', (d: any) => {
          if (d.carrier === minArrivalDelayItem?.carrier && d.delay_type === minArrivalDelayItem?.delay_type) {
            return highlightColorBestBorder; // Add border for AA's best
          }
          return 'none';
        })
        .attr('stroke-width', (d: any) => {
          if (d.carrier === minArrivalDelayItem?.carrier && d.delay_type === minArrivalDelayItem?.delay_type) {
            return 2; // Border width
          }
          return 0;
        });
    });

    // Value labels on top of bars
    delayTypes.forEach((delayType: string) => {
      g.selectAll(`.value-label-${delayType.replace(/\s/g, '-')}`)
        .data(data.filter(d => d[seriesField] === delayType))
        .enter()
        .append('text')
        .attr('class', `value-label-${delayType.replace(/\s/g, '-')}`)
        .attr('x', (d: any) => xScale(d[xField])! + xSubgroupScale(d[seriesField])! + xSubgroupScale.bandwidth() / 2)
        .attr('y', (d: any) => yScale(d[yField]) - 8) // Position slightly above bar
        .attr('text-anchor', 'middle')
        .text((d: any) => d[yField].toFixed(1)) // Display value with one decimal place
        .attr('fill', (d: any) => {
            if (d.carrier === maxDelayItem?.carrier && d.delay_type === maxDelayItem?.delay_type) {
              return highlightGradientWorstStart; // Use brighter red for MQ's text
            }
            if (d.carrier === minArrivalDelayItem?.carrier && d.delay_type === minArrivalDelayItem?.delay_type) {
              return highlightColorBestText; // Use light blue for AA's text
            }
            return textColor; // Default text color
        })
        .style('font-size', '14px')
        .style('font-weight', (d: any) => {
            if ((d.carrier === maxDelayItem?.carrier && d.delay_type === maxDelayItem?.delay_type) ||
                (d.carrier === minArrivalDelayItem?.carrier && d.delay_type === minArrivalDelayItem?.delay_type)) {
                return '700'; // Bold for highlighted text
            }
            return '400';
        })
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });

    // Legend for delay types
    const legend = g.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(${chartWidth - 200}, 10)`); // Positioned at top-right inside chart area

    delayTypes.forEach((delayType: string, i: number) => {
      const legendColor = delayType === '平均出发延误' ? barColorDeparture : barColorArrival;
      
      const legendItem = legend.append('g')
        .attr('transform', `translate(0, ${i * 25})`); // Vertical spacing for legend items

      legendItem.append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', 15)
        .attr('height', 15)
        .attr('fill', legendColor)
        .attr('rx', 3); // Rounded corners for legend color box

      legendItem.append('text')
        .attr('x', 20)
        .attr('y', 12) // Vertically align text with color box
        .text(delayType)
        .attr('fill', textColor)
        .style('font-size', '14px')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    });

  }, [scales, maxDelayItem, minArrivalDelayItem, textColor, barColorDeparture, barColorArrival, highlightColorWorstBar, highlightColorBestBorder, highlightColorBestText, highlightGradientWorstStart, highlightGradientWorstEnd, gridColor, axisColor]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, // CRITICAL: MUST use JSON config value #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px' // Provides outer margin for the entire scene
    }}>
      {/* Title - positioned at the top, respecting the 30px offset and top 80px subtitle zone */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from the top of the video canvas
        fontSize: '36px',
        fontWeight: '700',
        color: textColor,
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司平均出发和到达延误对比
      </div>
      
      {/* Chart SVG container - positioned below the title, with space for labels and subtitles */}
      <svg 
        ref={svgRef} 
        width={960} // Total SVG width
        height={550} // Total SVG height, including internal margins
        style={{ 
          marginTop: '20px', // Space between the external title and the SVG content
          shapeRendering: 'geometricPrecision', // SVG rendering quality
          textRendering: 'geometricPrecision' // Text rendering quality
        }} 
      />
    </AbsoluteFill>
  );
};