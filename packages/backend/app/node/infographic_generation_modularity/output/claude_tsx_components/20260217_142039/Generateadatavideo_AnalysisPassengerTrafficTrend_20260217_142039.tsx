import React, {useEffect, useRef, useMemo} from 'react';
import { AbsoluteFill } from 'remotion';
import * as d3 from 'd3';

export const Generateadatavideo_AnalysisPassengerTrafficTrend_20260217_142039Component: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = [
  { "date": "2015-01-01", "sum_passengers": 15462, "count": 113 },
  { "date": "2015-01-02", "sum_passengers": 18891, "count": 134 },
  { "date": "2015-01-03", "sum_passengers": 15103, "count": 109 },
  { "date": "2015-01-04", "sum_passengers": 17087, "count": 124 },
  { "date": "2015-01-05", "sum_passengers": 18232, "count": 135 },
  { "date": "2015-01-06", "sum_passengers": 17142, "count": 134 },
  { "date": "2015-01-07", "sum_passengers": 16888, "count": 131 },
  { "date": "2015-01-08", "sum_passengers": 15889, "count": 123 },
  { "date": "2015-01-09", "sum_passengers": 16325, "count": 125 },
  { "date": "2015-01-10", "sum_passengers": 11762, "count": 88 },
  { "date": "2015-01-11", "sum_passengers": 14638, "count": 113 },
  { "date": "2015-01-12", "sum_passengers": 17745, "count": 136 },
  { "date": "2015-01-13", "sum_passengers": 16858, "count": 134 },
  { "date": "2015-01-14", "sum_passengers": 17416, "count": 136 },
  { "date": "2015-01-15", "sum_passengers": 17171, "count": 135 },
  { "date": "2015-01-16", "sum_passengers": 17556, "count": 136 },
  { "date": "2015-01-17", "sum_passengers": 11704, "count": 87 },
  { "date": "2015-01-18", "sum_passengers": 14371, "count": 108 },
  { "date": "2015-01-19", "sum_passengers": 17029, "count": 130 },
  { "date": "2015-01-20", "sum_passengers": 17605, "count": 135 },
  { "date": "2015-01-21", "sum_passengers": 17311, "count": 135 },
  { "date": "2015-01-22", "sum_passengers": 17086, "count": 135 },
  { "date": "2015-01-23", "sum_passengers": 16667, "count": 134 },
  { "date": "2015-01-24", "sum_passengers": 11600, "count": 89 },
  { "date": "2015-01-25", "sum_passengers": 14103, "count": 116 },
  { "date": "2015-01-26", "sum_passengers": 14126, "count": 104 },
  { "date": "2015-01-27", "sum_passengers": 12435, "count": 90 },
  { "date": "2015-01-28", "sum_passengers": 17055, "count": 129 },
  { "date": "2015-01-29", "sum_passengers": 18061, "count": 136 },
  { "date": "2015-01-30", "sum_passengers": 18253, "count": 137 }
  ];
  
  // Data Binding
  const data_binding = {
    "x_axis": { "field": "date", "label": "日期", "type": "temporal" },
    "y_axis": { "field": "sum_passengers", "label": "总客流量", "type": "quantitative" }
  };

  const xField = data_binding.x_axis.field;
  const yField = (data_binding.y_axis as { field: string }).field;

  // Color configuration (CRITICAL: Background colors are fixed!)
  const backgroundColor = '#0f1419'; 
  const textColor = '#e8eaed'; 
  const chartColor = '#5BC0DE'; // Calm, analytical blue for trend
  const highlightColor = '#6FFFE9'; // Brighter aqua/cyan for highlight
  const gridColor = '#333a40'; // Subtle dark grey for grid
  const axisColor = '#7a8087'; // Medium grey for axis labels

  // Canvas and margins
  const width = 1280;
  const height = 720;
  
  // chartMargin defines the space around the 'g' element that contains the chart.
  // chartMargin.top: space for the main title.
  // chartMargin.bottom: space for x-axis labels and padding to the 180px subtitle zone.
  const chartMargin = { top: 100, right: 60, bottom: 40, left: 100 }; 
  const usableChartWidth = width - chartMargin.left - chartMargin.right; // 1280 - 100 - 60 = 1120px
  const chartDrawingHeight = 320; // Explicitly define the height of the actual line drawing area.

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  
  // Ensure maxItem also gets parsedDate for consistent usage with scales
  const maxItem = useMemo(() => {
    const parsedData = data.map(d => ({
      ...d,
      parsedDate: parseDate(d[xField] as string)
    })).filter(d => d.parsedDate !== null);
    return parsedData.find((d: any) => d[yField] === maxValue);
  }, [data, xField, maxValue]);

  // Process data for time scale
  const parseDate = d3.timeParse('%Y-%m-%d');
  const processedData = useMemo(() => {
    return data.map(d => ({
      ...d,
      parsedDate: parseDate(d[xField] as string)
    })).filter(d => d.parsedDate !== null).sort((a, b) => (a.parsedDate as Date).getTime() - (b.parsedDate as Date).getTime());
  }, [data, xField]);

  // D3 scales
  const { xScale, yScale } = useMemo(() => {
    const xScale = d3.scaleTime()
      .domain(d3.extent(processedData, (d: any) => d.parsedDate) as [Date, Date])
      .range([0, usableChartWidth]);

    const yScale = d3.scaleLinear()
      .domain([d3.min(processedData, (d:any) => d[yField])! * 0.9, maxValue * 1.05]) 
      .range([chartDrawingHeight, 0]); 

    return { xScale, yScale };
  }, [processedData, maxValue, usableChartWidth, chartDrawingHeight, yField]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); 

    // SVG clarity optimizations
    svg.attr('shape-rendering', 'geometricPrecision')
       .attr('text-rendering', 'geometricPrecision');
    
    // Main group for the chart, translated to respect top and left margins
    const g = svg.append('g')
      .attr('transform', `translate(${chartMargin.left}, ${chartMargin.top})`);

    // Add defs for shadow filter (feDropShadow for clean shadows)
    const defs = svg.append('defs');
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    // Add X gridlines
    g.append('g')
      .attr('class', 'grid-x')
      .attr('transform', `translate(0, ${chartDrawingHeight})`)
      .call(d3.axisBottom(xScale)
        .tickSize(-chartDrawingHeight)
        .tickFormat(() => "")
        .ticks(d3.timeDay.every(5)) // Show fewer ticks, e.g., every 5 days
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Add Y gridlines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-usableChartWidth)
        .tickFormat(() => "")
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2');

    // Define the line generator
    const line = d3.line<any>()
      .x(d => xScale(d.parsedDate as Date))
      .y(d => yScale(d[yField]));

    // Draw the line path
    g.append('path')
      .datum(processedData)
      .attr('fill', 'none')
      .attr('stroke', chartColor)
      .attr('stroke-width', 4)
      .attr('d', line);

    // Add circles for each data point
    g.selectAll('.dot')
      .data(processedData)
      .enter()
      .append('circle')
      .attr('class', 'dot')
      .attr('cx', d => xScale(d.parsedDate as Date))
      .attr('cy', d => yScale(d[yField]))
      .attr('r', 5)
      .attr('fill', chartColor)
      .attr('stroke', backgroundColor)
      .attr('stroke-width', 2);

    // Highlight the max value point and label (IN THE CHART ITSELF)
    if (maxItem && maxItem.parsedDate) { 
      g.append('circle')
        .attr('cx', xScale(maxItem.parsedDate as Date))
        .attr('cy', yScale(maxItem[yField]))
        .attr('r', 8)
        .attr('fill', highlightColor)
        .attr('stroke', backgroundColor)
        .attr('stroke-width', 3)
        .style('filter', 'url(#shadow)');

      g.append('text')
        .attr('x', xScale(maxItem.parsedDate as Date))
        .attr('y', yScale(maxItem[yField]) - 20)
        .attr('text-anchor', 'middle')
        .text(`${maxItem[yField].toLocaleString()}`)
        .attr('fill', highlightColor)
        .style('font-size', '22px')
        .style('font-weight', 'bold')
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .style('-webkit-font-smoothing', 'antialiased')
        .style('text-rendering', 'geometricPrecision');
    }

    // Add the X Axis
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0, ${chartDrawingHeight})`)
      .call(d3.axisBottom(xScale)
        .ticks(d3.timeDay.every(5)) 
        .tickFormat(d3.timeFormat('%m/%d'))
      )
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor);

    // Add the Y Axis
    g.append('g')
      .attr('class', 'y-axis')
      .call(d3.axisLeft(yScale).ticks(5).tickFormat(d3.format(".2s"))) // Format as "15K", "20K"
      .selectAll('text')
      .attr('fill', axisColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');
    
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);

    // X Axis Label (CRITICAL: ensure y position is above 180px subtitle zone)
    // Absolute Y position: chartMargin.top + chartDrawingHeight + chartMargin.bottom = 100 + 320 + 40 = 460px
    // This is well above 720 - 180 = 540px.
    g.append('text')
      .attr('class', 'x-axis-label')
      .attr('x', usableChartWidth / 2)
      .attr('y', chartDrawingHeight + chartMargin.bottom) 
      .attr('text-anchor', 'middle')
      .text(data_binding.x_axis.label)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

    // Y Axis Label (CRITICAL: ensure x position is negative enough to avoid tick label overlap)
    g.append('text')
      .attr('class', 'y-axis-label')
      .attr('x', -chartDrawingHeight / 2) 
      .attr('y', -60) // Adjusted to be further left from y-axis
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90)')
      .text(data_binding.y_axis.label)
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision');

  }, [processedData, xScale, yScale, usableChartWidth, chartDrawingHeight, maxValue, maxItem, xField, yField, chartColor, highlightColor, textColor, gridColor, axisColor, chartMargin]);
  
  return (
    <AbsoluteFill style={{ 
      background: backgroundColor, 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0px 40px' 
    }}>
      {/* Title (CRITICAL: Reserve top 80px) */}
      <div style={{
        position: 'absolute',
        top: 30, // Centered vertically within the top 80-100px clear zone
        fontSize: '36px',
        fontWeight: '700',
        color: textColor,
        textAlign: 'center',
        width: '100%',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        客流量随时间变化趋势
      </div>
      
      {/* Chart container */}
      <svg 
        ref={svgRef} 
        width={width} 
        height={height} 
        style={{ 
          marginTop: '20px', 
          overflow: 'visible' 
        }} 
      />
    </AbsoluteFill>
  );
};