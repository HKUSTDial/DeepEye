import React, { useEffect, useRef, useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import * as d3 from 'd3';

export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Scene time offset (for independent preview)
  const sceneStartOffset = 26.625; // Start time of the scene in the original video

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

  // Animation and Narration Configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 26.625,
      "duration": 10.849999999999998
    },
    {
      "id": "emphasis_minneapolis",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "destcity": "Minneapolis"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Minneapolis when mentioned",
      "time_start": 26.625,
      "duration": 10.849999999999998
    },
    {
      "id": "emphasis_los_angeles",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "destcity": "Los Angeles"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight Los Angeles when mentioned",
      "time_start": 26.625,
      "duration": 10.849999999999998
    }
  ];

  const narrations = [
    {
      "text": "接着，我们转向目的地城市。明尼阿波利斯平均抵达延误近20分钟，而洛杉矶则表现出色，仅约5分钟。",
      "time_start": 26.625,
      "time_end": 37.275,
      "audio_file": "20260217_145526_analysis_destcity_delay_distribution_narr0.wav"
    }
  ];

  // Color configuration (CRITICAL: background colors from JSON config - DO NOT CHANGE!)
  const backgroundColor = '#0f1419';
  // const containerBackground = '#0f1419'; // Not used directly, but kept for reference

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

  // First useEffect: Static rendering and initial states for animation
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
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial opacity for tick labels
    g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor).style('opacity', 0); // Initial opacity for axis line/ticks

    // Y-axis label
    g.append('text')
      .attr('class', 'y-axis-label') // Added class for animation targeting
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
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible for animation

    // Horizontal grid lines
    g.append('g')
      .attr('class', 'grid-y')
      .call(d3.axisLeft(yScale)
        .tickSize(-chartWidth) // Extend grid lines across chart width
        .tickFormat(() => '') // No labels for grid lines
      )
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '2,2')
      .style('opacity', 0); // Initial opacity for grid lines
    g.select('.grid-y').select('path').remove(); // Remove the domain line of the grid

    // Bars
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', chartHeight) // Start at the bottom for animation
      .attr('width', xScale.bandwidth())
      .attr('height', 0) // Start with 0 height for animation
      .attr('fill', (d: any) => {
        if (d[xField] === maxItem?.[xField]) return 'url(#worstGradient)';
        if (d[xField] === minItem?.[xField]) return 'url(#bestGradient)';
        return 'url(#generalGradient)';
      })
      .attr('rx', 8) // Rounded corners for bars
      .attr('ry', 8)
      .style('filter', 'url(#shadow)') // Apply shadow
      .style('opacity', 0); // Start invisible for animation

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
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible for animation

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
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible for animation

  }, [scales, maxValue, minValue, maxItem, minItem, chartWidth, chartHeight, barColor, highlightColorWorst, highlightColorBest, textColor, gridColor, axisColor, xField, yField, yAxisLabel, chartMargin.left, chartMargin.top]);


  // Second useEffect: Animation logic
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { xScale, yScale } = scales;
    const innerHeight = chartHeight; // D3 drawing area height

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');

    if (entranceAnim) {
      const animStartFrame = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEndFrame = animStartFrame + entranceAnim.duration * fps;

      // CRITICAL: After animation ends, force all elements to final state
      if (frame >= animEndFrame) {
        // Bar Chart elements
        g.selectAll('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1)
            .attr('stroke', 'none') // Ensure no leftover stroke from emphasis
            .style('filter', 'url(#shadow)'); // Restore shadow
        });
        g.selectAll('.value-label, .category-label, .y-axis-label').style('opacity', 1);
        g.select('.y-axis').selectAll('text, line, path').style('opacity', 1); // Restore tick labels, axis line/ticks
        g.select('.grid-y').selectAll('line').style('opacity', 1); // Restore grid lines

        // Continue to emphasis animation logic, do not return
      } else if (frame >= animStartFrame) {
        // Entrance animation in progress
        const totalTime = (frame - animStartFrame) / fps; // Current elapsed seconds

        // Bars grow from bottom
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12; // Each bar delayed by 0.12 seconds
          const animDuration = 0.6; // Single bar animation duration 0.6 seconds
          const barStart = i * delayPerBar;
          const barEnd = barStart + animDuration;

          if (totalTime >= barStart && totalTime <= barEnd) {
            const barProgress = (totalTime - barStart) / animDuration;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight))
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            // Bar animation completed, set to final state
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', innerHeight - targetHeight)
              .style('opacity', 1);
          }
        });

        // Value and Category labels fade in
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3; // Additional delay for labels
          const animDuration = 0.4; // Label fade-in duration
          const labelStart = i * delayPerBar + labelDelay;
          const labelEnd = labelStart + animDuration;

          if (totalTime >= labelStart && totalTime <= labelEnd) {
            const labelProgress = (totalTime - labelStart) / animDuration;
            const eased = d3.easeCubicOut(labelProgress);
            label.style('opacity', eased);
          } else if (totalTime > labelEnd) {
            label.style('opacity', 1);
          }
        });

        // Y-axis label, tick labels, axis lines, and grid lines fade in
        const axisStart = 0.3; // Axis elements start fading in after 0.3 seconds of totalTime
        const axisDuration = 0.4; // Axis elements fade-in duration
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.select('.y-axis-label').style('opacity', eased);
          g.select('.y-axis').selectAll('text, line, path').style('opacity', eased);
          g.select('.grid-y').selectAll('line').style('opacity', eased);
        } else if (totalTime > axisStart + axisDuration) {
          g.select('.y-axis-label').style('opacity', 1);
          g.select('.y-axis').selectAll('text, line, path').style('opacity', 1);
          g.select('.grid-y').selectAll('line').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;

    // Collect all currently active emphasis animations
    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStartFrame = (anim.time_start - sceneStartOffset) * fps;
      const animDurationFrame = anim.duration * fps;
      return frame >= animStartFrame && frame < animStartFrame + animDurationFrame;
    });

    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;

      // Calculate a combined pulse effect for all active emphasis animations
      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStartFrame = (anim.time_start - sceneStartOffset) * fps;
        const animDurationFrame = anim.duration * fps;
        const progress = (frame - animStartFrame) / animDurationFrame;
        // Pulse effect: oscillates between 1 and 1.05
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      // Collect all data items that need highlighting from all active emphasis animations
      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          data.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d[xField]); // Use xField (e.g., "destcity") as unique identifier
            }
          });
        }
      });

      // Process all bars based on collected highlighted items
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b')
            .attr('stroke-width', 4 * maxPulse)
            .style('filter', 'url(#shadow) drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Combine with existing shadow
        } else {
          bar
            .style('opacity', 0.3)
            .attr('stroke', 'none')
            .style('filter', 'url(#shadow)'); // Restore original shadow
        }
      });

      // Also adjust opacity for value and category labels
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any) {
          const label = d3.select(this);
          const isHighlighted = highlightedItems.has(d[xField]);
          label.style('opacity', isHighlighted ? 1 : 0.3);
      });

      // For bar charts, axis labels and grid lines are usually not dimmed during item emphasis
      // If needed, they would be handled here, but for now, they remain at full opacity.
    }

    // 3. Restore normal state (only if no emphasis is active AND entrance animation is complete)
    // CRITICAL: Ensure all elements are restored, preventing elements from remaining invisible
    if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {
      g.selectAll('.bar')
        .attr('stroke', 'none')
        .style('opacity', 1)
        .style('filter', 'url(#shadow)'); // Restore shadow

      g.selectAll('.value-label, .category-label, .y-axis-label').style('opacity', 1);
      g.select('.y-axis').selectAll('text, line, path').style('opacity', 1);
      g.select('.grid-y').selectAll('line').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, chartHeight, maxItem, minItem, barColor, highlightColorWorst, highlightColorBest, textColor]);

  // Helper function to get current narration text
  const getCurrentNarration = () => {
    const currentTime = frame / fps;
    return narrations.find(narr =>
      currentTime >= (narr.time_start - sceneStartOffset) &&
      currentTime <= (narr.time_end - sceneStartOffset)
    );
  };

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

      {/* Subtitle Display */}
      {getCurrentNarration() && (
        <div style={{
          position: 'absolute',
          bottom: 35,
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(10px)',
          padding: '15px 30px',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          color: '#ffffff',
          fontSize: '17px',
          fontWeight: '500',
          lineHeight: '1.45',
          maxWidth: '90%',
          textAlign: 'center',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
        }}>
          {getCurrentNarration().text}
        </div>
      )}
    </AbsoluteFill>
  );
};