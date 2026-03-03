"""Prompt templates for Dashboard Engineering implementation

This module defines all prompt templates used in Dashboard Engineering implementation.
"""

# ============================================================================
# Layout and Position Generation Prompt
# ============================================================================

LAYOUT_POSITION_GENERATION_PROMPT = """
You are a dashboard layout expert. Your task is to add layout configuration and position information to a dashboard configuration based on the Dashboard Configuration Specification, chart aspect ratios, and importance levels.

## Dashboard Configuration Specification Summary

### Layout Structure:
```json
{{
  "layout": {{
    "type": "grid",
    "columns": 4,
    "gap": 1.0,
    "pageTemplate": "public/templates/page_default.html"
  }}
}}
```

### Position Structure (for each block):
```json
{{
  "position": {{
    "col": 1,
    "row": 1,
    "span": 2,
    "rowSpan": 2
  }}
}}
```

## Chart Aspect Ratio and Dimension Information:
{chart_dimensions}

## Layout Design Strategy:

### 1. Chart Importance Levels:
- **Primary Chart**: Most important visualization, largest size
  - Span: 2-4 columns (depending on total columns)
  - RowSpan: 2-3 rows
  - Position: Prominent location (top-left or center-left)
  - Characteristics: Key metrics, overview charts, main trend analysis
  
- **Secondary Charts**: Supporting visualizations, medium size
  - Span: 1-2 columns
  - RowSpan: 1-2 rows
  - Position: Surrounding the primary chart
  - Characteristics: Detailed breakdowns, supplementary insights
  
- **Tertiary Charts**: Additional context, smaller size
  - Span: 1 column
  - RowSpan: 1 row
  - Position: Fill remaining spaces
  - Characteristics: Filters, KPIs, minor details

### 2. Aspect Ratio Considerations:
- **Wide charts (width/height > 2.0)**: 
  - Use larger span (2-4 columns), smaller rowSpan (1-2)
  - Suitable for: time series, horizontal bar charts, area charts
  
- **Square charts (0.8 < width/height < 1.2)**:
  - Use balanced span and rowSpan (e.g., span: 2, rowSpan: 2)
  - Suitable for: scatter plots, pie charts, heatmaps
  
- **Tall charts (width/height < 0.8)**:
  - Use smaller span (1-2 columns), larger rowSpan (2-3)
  - Suitable for: vertical bar charts, hierarchical trees

### 3. Layout Patterns:

**Pattern A: Single Primary**
```
┌─────────────┬─────┬─────┐
│             │ S1  │ S2  │
│   Primary   ├─────┼─────┤
│             │ S3  │ S4  │
└─────────────┴─────┴─────┘
```

**Pattern B: Dual Primary **
```
┌───────────┬───────────┐
│ Primary 1 │ Primary 2 │
├─────┬─────┼─────┬─────┤
│ S1  │ S2  │ S3  │ S4  │
└─────┴─────┴─────┴─────┘
```

**Pattern C: Magazine Layout **
```
┌─────────────┬───────────┐
│             │    S1     │
│   Primary   ├─────┬─────┤
│             │ S2  │ S3  │
├─────┬─────┬─┴─────┴─────┤
│ S4  │ S5  │     S6      │
└─────┴─────┴─────────────┘
```

**Pattern D: Fill Remaining Space**
```
❌ BAD - Leaving empty columns:
┌─────┬─────┬─────┬─────┐
│  1  │  2  │  3  │  4  │
├─────┼─────┼─────┼─────┤
│  5  │  6  │  7  │ [EMPTY]│  ← Do not leave empty!
└─────┴─────┴─────┴─────┘

✅ GOOD - Expand last chart to fill:
┌─────┬─────┬─────┬─────┐
│  1  │  2  │  3  │  4  │
├─────┼─────┴─────┴─────┤
│  5  │       7         │  ← Expand to fill!
└─────┴─────────────────┘

✅ GOOD - Distribute evenly:
┌─────┬─────┬─────┬─────┐
│  1  │  2  │  3  │  4  │
├─────┴─────┼─────┴─────┤
│     5     │     6     │  ← Each occupies 2 columns
└───────────┴───────────┘
```

## Rules and Best Practices:

1. **Determine Column Count**: 
   - 2-3 columns for small dashboards (< 5 charts)
   - 4 columns for medium dashboards (5-10 charts)
   - 6 columns for large dashboards (> 10 charts)

2. **Identify Primary Charts**:
   - Look for keywords in description: "overview", "main", "trend", "total", "summary"
   - Charts with multiple series or complex visualizations
   - First 1-2 charts are often primary unless explicitly stated otherwise

3. **Respect Aspect Ratios**:
   - Read the chart_dimensions data to get actual width/height from HTML files
   - Match span/rowSpan to the chart's natural aspect ratio
   - Avoid extreme distortions (e.g., don't force a wide chart into 1 column)

4. **Visual Hierarchy**:
   - Place header blocks at the very top (row: 1, full width)
   - Place highlight/KPI blocks in row 2 (small, span: 1)
   - Place primary chart(s) starting from row 3
   - Arrange secondary charts around primary charts
   - Fill gaps with tertiary charts

5. **Flow and Alignment**:
   - Left-to-right, top-to-bottom reading order
   - Align related charts (e.g., chart + its breakdown)
   - Leave no awkward gaps in the grid
   - Ensure positions don't overlap
   - CRITICAL: Row/rowSpan ranges must not overlap; the occupied rectangles [row..row+rowSpan-1] × [col..col+span-1] of any two blocks must not intersect

6. **Fill Remaining Space (IMPORTANT - Avoid leaving empty spaces)**:
   - **Last chart should expand to fill remaining columns**: If there are empty columns at the end of the last row, increase the last chart's span to occupy all remaining space
   - **Examples**:
     * 4 columns layout with 7 charts → Last row: 1 chart with span=4 (fill all 4 columns)
     * 4 columns layout with 8 charts → Last row: 2 charts, each span=2 (fill all 4 columns)
     * 6 columns layout with 10 charts → Last row: 1 chart with span=6 (fill all 6 columns)
   - **Calculation**: For the last row, calculate remaining_cols = total_columns - sum(previous_charts_span_in_same_row), then set last_chart_span = remaining_cols
   - **Avoid orphan cells**: No single empty cells should be left at the end of rows
   - **Maximize space utilization**: Prefer larger charts over leaving gaps
   - **Priority rule**: Fill > Balance > Aesthetic

7. **Responsive Considerations**:
   - Don't exceed the total column count
   - Ensure each row is fully utilized
   - Balance the layout (avoid all charts on one side)

## Current Dashboard Configuration:
```json
{config_json}
```

## Task:
1. **Analyze the chart dimensions** provided above to understand each chart's aspect ratio
2. **Identify chart importance levels** based on descriptions and chart types:
   - Assign 1-2 primary charts
   - Assign 3-5 secondary charts
   - Assign remaining as tertiary charts
3. **Choose optimal column count** (2-6) based on total number of charts and their aspect ratios
4. **Design layout pattern** (Pattern A/B/C or custom) that best fits the chart set
5. **Add "layout" object** at root level with "type", "columns", "gap", "pageTemplate"
6. **Add "position" object** to each block with appropriate "col", "row", "span", "rowSpan"
7. **Verify layout**:
   - No overlaps
   - Strictly forbid vertical overlap caused by rowSpan (row intervals must not intersect)
   - All positions are valid (col + span <= columns + 1)
   - Aspect ratios are respected
   - Visual hierarchy is maintained
   - **Last row is fully filled**: No empty columns at the end of the last row (expand the last chart if needed)
   - **No orphan cells**: Each row should be completely filled or strategically arranged
8. **Return ONLY the complete modified JSON configuration**, no explanations or markdown code blocks

Output the complete dashboard configuration with layout and position information added.
"""

# ============================================================================
# Page Theme Generation Prompt
# ============================================================================

PAGE_THEME_GENERATION_PROMPT = """
You are a visual design expert specializing in data dashboard aesthetics.
Your task is to generate a beautiful, themed CSS style based on the dashboard's main topic or question.

==============================
🎯 PURPOSE
==============================
Your primary goal is to create a visually coherent theme that matches the *real-world context* implied by the topic/question.

Topics may contain abstract business terms such as "transaction", "sales", or "revenue".  
⚠️ Do NOT interpret them literally as "finance", "retail", or "corporate" unless the topic explicitly describes a financial/banking environment.

➡️ If the topic relates to sales or transactions, you MUST extract the **actual product type or service being sold** from the topic/question (e.g., coffee, food, toys, books, skincare, digital products).  
Do not generalize to "retail" or "commerce" without confirming the category.

==============================
🧩 INPUT
==============================
Topic or Question:
{question}

HTML Template (format reference only — not style guidance):
```html
{template_content}
```

==============================
🧭 TASKS
==============================

**Step 0: Context Extraction**  
- Carefully read the first 1–2 sentences of the topic/question.  
- Extract specific subject information such as:
  - WHO is operating (e.g., company or business name)?
  - WHAT is being sold (specific product or service)?
  - WHERE is it happening (location, environment)?
- If the topic involves sales, identify the specific **domain of sales** — e.g., "coffee shop", "pizza restaurant", "children's toys", "skincare products", "art prints".

**Step 1: Scene Construction**  
- Based on Step 0, describe a realistic usage scenario (e.g., "a café manager in NYC tracking morning vs evening drink sales").  
- Keep it specific and consistent with the subject and setting.

**Step 2: Thematic Design**  
- Describe the tone and atmosphere that fits the context (e.g., cozy, elegant, fun, calm).
- Define what mood or feeling the color palette should evoke (e.g., warm, energetic, modern, luxurious).

**Step 3: Generate CSS Theme Variables**  
- Modify only the following `:root` CSS variables:
  - --bg
  - --card
  - --card-2
  - --text
  - --muted
  - --brand
  - --shadow
- Ensure good contrast, readability, and visual balance.

**Step 4: Header and Title Personalization**  
- Treat the page header as the opening title and brief guidance (header). Update the document `<title>` and the visible header title/subtitle to reflect the topic context.
- The main title should be a concise, user-friendly dashboard title derived from the question/topic.
- Add a short, personalized tagline or prompt line under the title (e.g., one sentence describing what the user can explore).
- Do NOT change the page structure: only replace the textual content of existing title/header placeholders.

**Step 5: Respect Default Template Design**  
- The default template already defines `header.main`, `.grid`, `.card`, `.toolbar`, `.badge`, and fonts. Keep these classes and leverage the visual system (shadows, gradients, rounded corners).
- Highlights should emphasize key numbers (use larger, bold font similar to `.highlight-value` color `var(--brand)`). Make highlight cards visually distinct from regular chart cards (e.g., stronger accent border, slightly different background gradient, or subtle shadow variation).
- Different card types (highlight vs view/chart cards) should have visual distinction: use complementary but different tones, border styles, or opacity levels to create clear visual hierarchy.
- Maintain readable font sizes (titles ~24px for header, filter titles ~13px, card titles ~15px).

**Step 6: Output the Final HTML**  
- **CRITICAL**: You MUST use the EXACT same HTML structure as the default template provided above.
- **DO NOT** add any example content, sample data, or placeholder cards.
- **DO NOT** create a full page layout with hardcoded content.
- **ONLY** do the following:
  1. Update the CSS variable values in the `:root` section
  2. Update the `<title>` tag text
  3. Update the default text in `id="header-title"` and `id="header-subtitle"` (keep the HTML structure identical)
- Keep ALL other HTML structure exactly as in the default template (including the `<style>` block structure, `<header>`, `<div id="controls">`, `<div id="grid">`).
- Add Step 0–2 reasoning as HTML comments at the top of the style block.

==============================
🎨 STYLE GUIDANCE
==============================
- Avoid default "corporate" or "tech" themes unless the topic clearly belongs to finance, SaaS, or IT.
- Choose a palette that reflects the inferred business/product type:
   - ☕ Coffee shop → warm browns, latte beige, soft cream
   - 🍔 Restaurant → appetizing reds, golden yellows, wood tones
   - 🎨 Art / Creative → vivid or pastel creative palettes
   - 🧸 Toys → fun and playful colors (e.g., primary or pastel)
   - 🛍️ Fashion / skincare → stylish muted or luxurious palettes
   - 📚 Education → clean blues, chalky greens, paper whites
   - 🌤️ Weather / outdoors → soft sky blues, stormy grays

- Avoid using one flat color across the entire page; introduce subtle contrast and layered tones.
- Ensure page background and each card background are visually coordinated but not identical (e.g., light bg + slightly deeper card, or soft gradient).
- Use consistent, harmonious variations (e.g., `--card` vs `--card-2`) to create hierarchy without overwhelming saturation.

Return ONLY the complete HTML template with updated styles. Do not include any explanations or markdown code blocks.
"""

# ============================================================================
# Chart Beautification Prompt
# ============================================================================

CHART_BEAUTIFICATION_PROMPT = """
You are an ECharts visualization expert. Your task is to beautify a chart configuration to match a given page theme while preserving all data.

## Page Theme Colors (extract from page template):
{theme_colors}

## Current Chart Configuration:
```javascript
{chart_config}
```

## Rules:
1. **CRITICAL: Do NOT modify any data arrays** in series, xAxis, or yAxis
2. **CRITICAL: Do NOT add, remove, or modify backgroundColor in any way
3. **Do NOT include comments** in the output; the result must be a valid JSON object only.
4. **CRITICAL: Do NOT use JavaScript functions** (e.g., `function(value) {{...}}`) in formatter or any other properties. JSON cannot store functions. Instead, use ECharts string template formatters:
   - For date formatting: use ECharts date formatter templates like `'{{MM}}/{{dd}}'` or `'{{yyyy}}-{{MM}}-{{dd}}'` or `'{{MMM}}/{{dd}}'`
     * ECharts date formatter syntax: `{{yyyy}}` (year), `{{MM}}` (month 01-12), `{{dd}}` (day 01-31), `{{MMM}}` (month abbreviation)
     * Example: `"formatter": "{{MM}}/{{dd}}"` will display "01/15" for January 15th
   - For number formatting: use string templates like `'{{value}}'` or `'{{value}}.0'` or `'{{value}}k'` for thousands
   - For time axis: ECharts automatically formats dates when `type: 'time'` is used, so you may omit formatter or use string templates like `'{{MM}}/{{dd}}'`
   - Examples of valid formatters:
     * `"formatter": "{{MM}}/{{dd}}"` for date (month/day) - CORRECT ✅
     * `"formatter": "{{value}}"` for simple value display
     * `"formatter": "{{value}}k"` for thousands suffix
     * `"formatter": "{{value}}.0"` for decimal formatting
   - **DO NOT use**:
     * `function(value) {{ return ... }}` - JavaScript functions cannot be stored in JSON ❌
     * `"{{date.getMonth() + 1}}/{{date.getDate()}}"` - ECharts does NOT execute JavaScript code in strings ❌
     * Any JavaScript expressions or code snippets in strings ❌
5. X/Y axes requirements:
   - Do NOT rotate x-axis labels. Keep rotation at 0.
   - If x-axis labels are too dense, set label interval to 'auto' or an integer step to show at intervals; hide overlapping labels.
   - For time/date data on x-axis, use type: 'time' or ensure category labels are formatted as readable dates; avoid rotating; prefer smart intervals and string template formatter (e.g., `"{{MM}}/{{dd}}"` for month/day).
   - For y-axis numeric values, apply readable string template formatter (e.g., `"{{value}}"` or `"{{value}}k"` for thousands).
   - **If data values are close together (small differences), adjust y-axis min value to start from a non-zero baseline to enhance visual distinction between data points.**
   - Beautify both axes: axis line, tick, splitLine styles with soft contrast matching the theme.
6. You MAY modify:
   - Color schemes (series colors, axis colors, etc.)
   - Layout properties (grid, margins, spacing)
   - Axis styling (line styles, label formatting, font sizes)
   - Legend styling and positioning
   - Tooltip styling
   - Animation properties
   - Label visibility and formatting
6. Ensure colors match or complement the page theme
7. Maintain readability with proper contrast
8. Use modern, clean visual design
9. Keep the chart functional and user-friendly

## Task:
Beautify the chart configuration to create a visually appealing, theme-consistent chart while keeping all data intact.

Return ONLY the complete modified JavaScript option configuration (the object assigned to option_xxx). Do not include variable declaration or explanations.
"""

