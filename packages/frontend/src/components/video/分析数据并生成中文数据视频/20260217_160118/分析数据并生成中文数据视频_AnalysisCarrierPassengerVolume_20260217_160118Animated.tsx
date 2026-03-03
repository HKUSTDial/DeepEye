export const SceneComponentAnimated: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);

  // Remotion hooks
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Scene time offset (for independent preview)
  const sceneStartOffset = 29.138; // Start time of the scene in the original video

  // Animation configuration
  const animations = [
    {
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation",
      "time_start": 29.138,
      "duration": 6.461999999999997
    },
    {
      "id": "emphasis_AA",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "carrier": "AA"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight AA when mentioned",
      "time_start": 29.463,
      "duration": 5.936999999999998,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "AA",
        "word_time": 29.463
      }
    },
    {
      "id": "emphasis_UA",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 0,
      "target_data": {
        "data_filter": {
          "carrier": "UA"
        }
      },
      "style": {
        "intensity": 0.1
      },
      "description": "Highlight UA when mentioned",
      "time_start": 30.313000000000002,
      "duration": 5.086999999999996,
      "_debug_info": {
        "word_aligned": true,
        "keyword": "UA",
        "word_time": 30.313000000000002
      }
    }
  ];

  // Subtitle configuration
  const narrations = [
    {
      "text": "而AA和UA航空公司乘客量巨大，这可能影响了其运营效率。",
      "time_start": 29.138,
      "time_end": 35.4,
      "audio_file": "20260217_160118_analysis_carrier_passenger_volume_narr0.wav"
    }
  ];

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

  // Data binding fields
  const xField = "carrier";
  const yField = "sum_passengers";

  // Color configuration - CRITICAL: background_color and container_background are fixed!
  const backgroundColor = '#0f1419'; // MUST use this exact value from JSON config
  const containerBackground = '#0f1419'; // MUST use this exact value from JSON config

  // Scene-specific colors based on "Comparison of Total Passengers by Airline" and "AA and UA huge volumes affecting efficiency"
  // Neutral/Analytical with a hint of scale/potential issue. Using a blue-purple base with a vibrant cyan highlight.
  const textColor = '#e8eaed'; // Light text for dark background
  const barColor = '#4f46e5'; // Indigo for general bars (blue-purple for comparison/analysis)
  const highlightColorStart = '#22d3ee'; // Vibrant Cyan for highlighted bars (AA, UA)
  const highlightColorEnd = '#0ea5e9'; // Sky Blue for gradient end, creating a distinct pop
  const gridColor = '#333333'; // Subtle dark grey for grid lines
  const axisColor = '#888888'; // Lighter grey for axes

  // Calculate metrics
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const maxItems = data.filter((d: any) => d[yField] === maxValue);
  const carriersToHighlight = ['AA', 'UA']; // As per narration keywords

  // D3 scales
  const chartWidth = 960; // Total SVG width is 960
  const chartHeight = 320; // Drawing area height, leaving space for title and critical subtitle zone (180px at bottom)

  const scales = useMemo(() => {
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, chartWidth * 0.8]) // Use 80% of the SVG width for bars, centered
      .padding(0.4); // Increased padding for cleaner look

    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1]) // 10% extra for top padding
      .range([chartHeight, 0]); // Inverted for SVG coordinates

    return { xScale, yScale };
  }, [data, maxValue, chartWidth, chartHeight]);

  // Static D3 rendering (Initial state for animations)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Add gradients/shadows in <defs>
    const defs = svg.append('defs');

    // Gradient for highlighted bars
    const highlightGradient = defs.append('linearGradient')
      .attr('id', 'highlightGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    highlightGradient.append('stop').attr('offset', '0%').attr('stop-color', highlightColorStart);
    highlightGradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColorEnd);

    // Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'barShadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);

    // Calculate margins for chart group to center it horizontally within the SVG
    const chartAreaWidth = scales.xScale.range()[1];
    const horizontalMargin = (chartWidth - chartAreaWidth) / 2;

    const g = svg.append('g').attr('transform', `translate(${horizontalMargin}, 40)`); // Y-offset 40px from SVG top to leave space for title

    // Y-axis grid lines
    const yAxisGrid = d3.axisLeft(scales.yScale)
      .tickSize(-chartAreaWidth)
      .tickFormat(() => "")
      .ticks(5);

    g.append('g')
      .attr('class', 'grid-y')
      .call(yAxisGrid)
      .selectAll('line')
      .attr('stroke', gridColor)
      .attr('stroke-dasharray', '4 4')
      .style('opacity', 0); // Initial state for animation

    // Y-axis
    const yAxis = d3.axisLeft(scales.yScale)
      .ticks(5)
      .tickFormat((d: any) => `${d3.format(".2s")(d)}`); // Format numbers (e.g., 240K)

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis)
      .selectAll('text')
      .attr('fill', textColor)
      .style('font-size', '14px')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Initial state for animation

    g.select('.y-axis').selectAll('path, line')
      .attr('stroke', axisColor)
      .style('opacity', 0); // Initial state for animation


    // Draw bars - Initial state for animation
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', (d: any) => scales.xScale(d[xField]) || 0)
      .attr('y', chartHeight) // Start at bottom of chart area
      .attr('width', scales.xScale.bandwidth())
      .attr('height', 0) // Start with zero height
      .attr('fill', (d: any) => carriersToHighlight.includes(d[xField]) ? 'url(#highlightGradient)' : barColor)
      .attr('rx', 8) // Rounded corners for aesthetics
      .attr('ry', 8)
      .style('filter', 'url(#barShadow)')
      .style('opacity', 0); // Start invisible

    // Value labels on top of bars - Initial state for animation
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', (d: any) => (scales.xScale(d[xField]) || 0) + scales.xScale.bandwidth() / 2)
      .attr('y', (d: any) => scales.yScale(d[yField]) - 15) // Position above bar (will be animated)
      .attr('text-anchor', 'middle')
      .text((d: any) => d3.format(".2s")(d[yField])) // Format numbers (e.g., 240K)
      .attr('fill', (d: any) => carriersToHighlight.includes(d[xField]) ? highlightColorStart : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible

    // Category labels below chart - Initial state for animation
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'category-label')
      .attr('x', (d: any) => (scales.xScale(d[xField]) || 0) + scales.xScale.bandwidth() / 2)
      .attr('y', chartHeight + 40) // Positioned 40px below the chart bars (chartHeight is 320)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px')
      .style('font-weight', '600')
      .style('font-family', 'system-ui, -apple-system, sans-serif')
      .style('-webkit-font-smoothing', 'antialiased')
      .style('text-rendering', 'geometricPrecision')
      .style('opacity', 0); // Start invisible

  }, [scales, data, maxValue, xField, yField, textColor, barColor, highlightColorStart, highlightColorEnd, gridColor, axisColor, carriersToHighlight, chartHeight]);

  // Second useEffect for animation logic
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const g = svg.select('g');
    if (g.empty()) return;

    const { yScale } = scales;
    const innerHeight = chartHeight; // This is the height of the actual bar drawing area (320px)

    // 1. ENTRANCE ANIMATION
    const entranceAnim = animations.find((a: any) => a.type === 'entrance');

    if (entranceAnim) {
      const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
      const animEnd = animStart + entranceAnim.duration * fps;

      // CRITICAL: After animation ends, force all elements to final state
      if (frame >= animEnd) {
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', yScale(d[yField]))
            .style('opacity', 1);
        });
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.select('.y-axis').selectAll('text').style('opacity', 1);
        g.select('.y-axis').selectAll('path, line').style('opacity', 1);
        g.select('.grid-y').selectAll('line').style('opacity', 1);

      } else if (frame >= animStart) {
        // Entrance animation in progress
        const totalTime = (frame - animStart) / fps; // Current elapsed seconds

        // Bars grow from bottom
        g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {
          const bar = d3.select(this);
          const delayPerBar = 0.12; // Fixed delay 0.12 seconds
          const animDuration = 0.6; // Fixed duration 0.6 seconds
          const barStart = i * delayPerBar;
          const barEnd = barStart + animDuration;

          if (totalTime >= barStart && totalTime <= barEnd) {
            const barProgress = (totalTime - barStart) / animDuration;
            const eased = d3.easeCubicOut(barProgress);
            const targetHeight = innerHeight - yScale(d[yField]);
            const currentHeight = targetHeight * eased;

            bar
              .attr('height', Math.max(0, currentHeight))
              .attr('y', innerHeight - Math.max(0, currentHeight)) // Bars grow upwards from innerHeight
              .style('opacity', eased);
          } else if (totalTime > barEnd) {
            // Bar animation completed, set to final state
            const targetHeight = innerHeight - yScale(d[yField]);
            bar
              .attr('height', targetHeight)
              .attr('y', yScale(d[yField]))
              .style('opacity', 1);
          }
        });

        // Labels (value and category) fade in
        g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {
          const label = d3.select(this);
          const delayPerBar = 0.12;
          const labelDelay = 0.3; // Additional delay 0.3 seconds
          const animDuration = 0.4; // Fade-in duration 0.4 seconds
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

        // Axis and grid lines fade in
        const axisStart = 0.3;
        const axisDuration = 0.4;
        if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {
          const axisProgress = (totalTime - axisStart) / axisDuration;
          const eased = d3.easeCubicOut(axisProgress);
          g.select('.y-axis').selectAll('text').style('opacity', eased);
          g.select('.y-axis').selectAll('path, line').style('opacity', eased);
          g.select('.grid-y').selectAll('line').style('opacity', eased);
        } else if (totalTime > axisStart + axisDuration) {
          g.select('.y-axis').selectAll('text').style('opacity', 1);
          g.select('.y-axis').selectAll('path, line').style('opacity', 1);
          g.select('.grid-y').selectAll('line').style('opacity', 1);
        }
      }
    }

    // 2. EMPHASIS ANIMATION
    const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
    let hasActiveEmphasis = false;

    const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      return frame >= animStart && frame < animStart + animDuration;
    });

    if (activeEmphasisAnims.length > 0) {
      hasActiveEmphasis = true;

      let maxPulse = 1;
      activeEmphasisAnims.forEach((anim: any) => {
        const animStart = (anim.time_start - sceneStartOffset) * fps;
        const animDuration = anim.duration * fps;
        const progress = (frame - animStart) / animDuration;
        // Pulse effect: oscillates between 1 - 0.05 and 1 + 0.05 (0.95 to 1.05)
        const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
        maxPulse = Math.max(maxPulse, pulse);
      });

      const highlightedItems = new Set<string>();
      activeEmphasisAnims.forEach((anim: any) => {
        const filter = anim.target_data?.data_filter;
        if (filter) {
          data.forEach((d: any) => {
            const matches = Object.keys(filter).every(
              (key) => d[key] === filter[key]
            );
            if (matches) {
              highlightedItems.add(d[xField]);
            }
          });
        }
      });

      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {
        const bar = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);

        if (isHighlighted) {
          bar
            .style('opacity', 1)
            .attr('stroke', '#ff6b6b') // Red stroke for highlight
            .attr('stroke-width', 4 * maxPulse) // Pulsing stroke width
            .style('filter', 'url(#barShadow) drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))'); // Combined with existing shadow + glow
        } else {
          bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'url(#barShadow)'); // Non-highlighted bars reduce opacity, keep original shadow
        }
      });

      // Value labels should also be affected by emphasis
      g.selectAll<SVGTextElement, any>('.value-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });
      // Category labels should also be affected by emphasis
      g.selectAll<SVGTextElement, any>('.category-label').each(function(d: any) {
        const label = d3.select(this);
        const isHighlighted = highlightedItems.has(d[xField]);
        label.style('opacity', isHighlighted ? 1 : 0.3);
      });

    }

    // 3. Restore normal state (only if no emphasis is active AND entrance is done)
    const entranceDone = entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps;

    if (!hasActiveEmphasis && entranceDone) {
      g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1).style('filter', 'url(#barShadow)');
      g.selectAll('.value-label, .category-label').style('opacity', 1);
    }

  }, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset, chartHeight, highlightColorStart, barColor, textColor]); // Added all relevant dependencies

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
      background: backgroundColor, // CRITICAL: MUST use JSON config value: #0f1419
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start', // Align to top to control spacing
      padding: '0px 40px' // Horizontal padding
    }}>
      {/* Title - Reserve top space */}
      <div style={{
        position: 'absolute',
        top: 30, // 30px from top, leaving space for potential top subtitle line
        width: '100%',
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        WebkitFontSmoothing: 'antialiased',
        textRendering: 'geometricPrecision'
      }}>
        各航空公司乘客总数比较
      </div>

      {/* Chart - positioned below the title, with ample space for bottom subtitles */}
      <svg
        ref={svgRef}
        width={chartWidth}
        height={chartHeight + 110} // chartHeight (320) + title_offset(40) + label_offset(40) + safe_gap (30) = 430. Add 110 to 320 to accommodate axis and labels in the main svg
        style={{
          marginTop: '100px', // Pushes chart down, leaving top 80-100px for title/subtitle
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }}
      />

      {/* CRITICAL: BOTTOM 180px is reserved for subtitle overlay */}
      {/* DO NOT place any critical visual elements below y=540 (720-180=540) */}
      {/* Our chart elements end around y=320 (bars) + 40 (labels) = 360 within the SVG's G group. */}
      {/* SVG's top margin is 100px. So, 100 + 360 = 460px from canvas top. This is safe! */}

      {/* Subtitle display */}
      {getCurrentNarration() && (
        <div style={{
          position: 'absolute',
          bottom: 35, // Bottom 35px (within the reserved 130px space, supporting 2-3 lines)
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