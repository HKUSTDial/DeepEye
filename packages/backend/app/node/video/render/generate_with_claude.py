"""
使用 Claude API 生成完整的 TSX 信息图组件
参考 ChartGalaxy 论文的简约设计风格

支持串行和并行两种模式：
- 串行模式：逐个生成场景（默认，适合调试）
- 并行模式：多线程同时生成（适合批量生成，速度更快）

使用方法：
  python generate_with_claude.py                    # 串行模式
  python generate_with_claude.py --parallel         # 并行模式（4 线程）
  python generate_with_claude.py --parallel -w 8    # 并行模式（8 线程）
"""

import json
import os
import sys
import argparse
import time
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

# 导入项目现有的 LLM 客户端
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import settings
from app.node.video.config.generator import LLMClient
from app.node.video.render.tsx_sanitize import sanitize_tsx_for_browser, validate_component_syntax

# 从环境变量或 settings 获取配置
API_BASE = settings.LLM_BASE_URL or os.getenv("LLM_BASE_URL")
API_KEY = settings.LLM_API_KEY or os.getenv("LLM_API_KEY")
DEFAULT_MODEL = settings.LLM_MODEL or os.getenv("LLM_MODEL")
VIDEO_RUNTIME_BASE = os.getenv("VIDEO_RUNTIME_BASE", "/workspace/video_runtime")
DEFAULT_COMPONENTS_OUTPUT_DIR = os.getenv(
    "VIDEO_COMPONENTS_OUTPUT_BASE",
    os.path.join(VIDEO_RUNTIME_BASE, "claude_tsx_components"),
)

if not API_BASE:
    raise ValueError("LLM_BASE_URL is required. Please set it in .env file or environment variable.")
if not API_KEY:
    raise ValueError("LLM_API_KEY is required. Please set it in .env file or environment variable.")
if not DEFAULT_MODEL:
    raise ValueError("LLM_MODEL is required. Please set it in .env file or environment variable.")


def should_retry_on_error(error_msg: str, attempt: int, elapsed_time: float, max_general_retries: int = 10) -> Tuple[bool, str]:
    err = str(error_msg).lower()
    if any(k in err for k in ["余额不足", "insufficient", "quota exceeded", "no credit"]):
        return False, "余额不足（永久性错误）"
    if any(k in err for k in ["401", "403", "unauthorized", "forbidden"]):
        return False, "认证失败（永久性错误）"
    if "429" in err or "rate limit" in err or "throttling" in err or "too many requests" in err:
        if elapsed_time < 30 * 60:
            return True, "Rate Limit（允许重试至30分钟）"
        return False, "Rate Limit 超过最大时间限制"
    if attempt < max_general_retries:
        return True, f"临时性错误（最多{max_general_retries}次）"
    return False, f"已达到最大重试次数（{max_general_retries}次）"


def calculate_retry_wait_time(error_msg: str, attempt: int) -> int:
    err = str(error_msg).lower()
    if "429" in err or "rate limit" in err:
        return min(2 ** attempt, 60)
    return 2


def extract_dataset_name(video_meta):
    """
    从视频元数据中提取数据集名字（用于组件命名）
    去掉空格，保持简洁
    """
    title = video_meta.get('title', 'DataAnalysis')
    # 去掉空格和特殊字符，只保留字母数字
    dataset_name = ''.join(c for c in title if c.isalnum())
    # 如果太长，截取前20个字符
    if len(dataset_name) > 20:
        dataset_name = dataset_name[:20]
    return dataset_name


def create_tsx_generation_prompt(scene_data, video_meta, component_name="SceneComponent", scene_index=1, total_scenes=1):
    """
    创建生成 TSX 组件的 Prompt（简约设计风格，参考 ChartGalaxy 论文）
    """
    content = scene_data.get('content', {})
    chart_title = content.get('title', 'Visualization')
    chart_type = content.get('chart_type', 'bar_chart')
    data = content.get('data', [])
    data_binding = content.get('data_binding', {})
    style = content.get('style', {})
    
    # 提取背景色（必须使用，保持视频统一性）
    background_color = style.get('background_color', '#0f1419')
    container_background = style.get('container_background', background_color)
    
    # 提取场景标题和旁白文本（用于语义分析，让LLM自己决定颜色）
    narrations = scene_data.get('narration', [])
    narration_texts = [n.get('text', '') for n in narrations if isinstance(n, dict) and 'text' in n]
    semantic_context = f"Title: {chart_title}"
    if narration_texts:
        newline_char = "\n"
        semantic_context += f"{newline_char}Narration keywords: {' | '.join(narration_texts[:2])}"  # 只取前2条
    
    # 提取用户自然语言查询（如果有，用于指导设计方向）
    user_query = video_meta.get('user_query', '')
    
    # 构建用户要求部分（避免在f-string中使用反斜杠）
    user_requirements_section = ""
    if user_query:
        newline_char = "\n"
        quote_char = '"'
        user_requirements_section = "- **User Requirements**: " + quote_char + user_query + quote_char + newline_char + "  - Consider these requirements when designing this scene (color choices, layout, emphasis, etc.)"
    
    # 构建用户要求部分（用于Design Decision Process）
    user_requirements_design_section = ""
    if user_query:
        quote_char = '"'
        user_requirements_design_section = "- **User Requirements**: " + quote_char + user_query + quote_char + " - Consider these requirements when designing (e.g., user wants to emphasize certain patterns, comparisons, trends, etc.)"
    
    prompt = f"""
You are creating a CLEAN, MINIMAL infographic for data video narration.
Reference: ChartGalaxy paper design principles - SIMPLE, CLEAR, DATA-FOCUSED.

**CRITICAL VIDEO CONTEXT:**
- Video Title: "{video_meta.get('title', 'Data Insights')}"
- Current Scene: {scene_index} of {total_scenes}
- **Background colors are ALREADY unified in JSON config - MUST use them!**
- **DO NOT change background_color or container_background - they are already consistent across all scenes!**
{user_requirements_section}

**🎯 DIVERSITY REQUIREMENT:**
- Each scene MUST have a UNIQUE visual identity
- Avoid using the same color scheme or layout pattern for consecutive scenes
- Base colors on scene semantics (title + narration), not just chart type
- Use background colors as foundation, but create visual variety in accent colors

# CORE PRINCIPLES
1. **CLEAN & MINIMAL** - No clutter, no excessive decoration
2. **DATA FIRST** - Information clarity > visual effects
3. **PURPOSEFUL DESIGN** - Every element serves the data story
4. **SUBTITLE-FRIENDLY** - Reserve top 80px for subtitle overlay
5. **VISUAL CONSISTENCY** - Same background across all scenes in this video

# DESIGN GUIDELINES

## Layout Strategy (Choose based on data)
- **Chart-Dominant**: Large chart (80% width), title on top, 2-3 key metrics integrated INTO chart area
- **Split Focus**: Chart (60%) + highlight metric (40%) side-by-side
- **Hero Number**: One giant number (center) + small trend chart below

## Visual Style (Background colors are already unified!)

**🚨 CRITICAL: Background colors are ALREADY determined in JSON config!**

**MUST use these exact values (DO NOT change them):**
- background_color: {background_color}
- container_background: {container_background}

**These colors are already unified across all scenes in the video - you MUST use them!**

### Scene Differentiation Strategy (under unified background):

**🎨 Theme Color Selection (based on scene semantics, LLM decides):**

1. **Analyze scene semantics**:
   {semantic_context}
   - Understand the core meaning of the scene (revenue/delay/growth/correlation/distribution, etc.)
   - Determine emotional tone (positive/negative/neutral)

2. **Color Selection Principles** (flexible based on scene semantics):
   - **Financial/Revenue related** → Golden/amber color scheme (#fbbf24, #f59e0b, #d97706, etc.)
   - **Problems/Delays related** → Red/orange color scheme (#ef4444, #f97316, #dc2626, etc.)
   - **Growth/Positive related** → Green/cyan color scheme (#10b981, #059669, #34d399, etc.)
   - **Correlation/Relationship** → Blue-purple color scheme (#3b82f6, #8b5cf6, #6366f1, etc.)
   - **Distribution/Share** → Multi-color gradient or rainbow color scheme
   - **Neutral/Analysis** → Choose harmonious color scheme based on background (30-90° adjacent on color wheel)

3. **Color Harmony**:
   - Ensure selected colors harmonize with background color ({background_color})
   - Can use colors 30-90° adjacent on color wheel, or complementary colors (180°)
   - Maintain overall tone consistency, but each scene has unique primary color

4. **Implementation**:
   - Can use linear gradients (from primary to secondary color)
   - Highlight elements can use contrasting or complementary colors
   - Text color must ensure clear readability on background color

**Layout Selection** (based on data characteristics):
- **Chart-Dominant** (80% width): More data points (>5), need to show full picture
- **Split Focus** (60% chart + 40% metrics): Have 1-2 key metrics to highlight
- **Hero Number** (center large number + small chart): Single value is particularly important, needs emphasis

**Highlight Method Diversity**:
- Gradient fill (from light to dark)
- Glow effect (drop-shadow)
- Border emphasis (stroke)
- Size contrast (scale)
- Each scene uses different combinations to avoid repetition

### Typography:
- Title: 32-36px, bold
- Chart labels: 14-16px, readable
- Key numbers: 28-48px, prominent

## Data Presentation
- Highlight the MOST IMPORTANT data point (largest bar, max value) **IN THE CHART ITSELF**
- Format numbers clearly: "$620.1B", "15.7%", "199 min"
- **Data labels on chart elements (bars/points) are sufficient - NO redundant info cards!**

**🚫 CRITICAL: NO Redundant Information Cards**
- ❌ **DO NOT** add fixed tooltip/info boxes showing specific data point details (e.g., "App C: 10M installs, 4.6★")
- ❌ **DO NOT** add decorative information boxes in corners or sides
- ❌ **DO NOT** duplicate information that's already visible in chart labels
- ✅ **ONLY** add supplementary content if it provides **NEW, meaningful insights**:
  - Key aggregated metrics (Total, Average) that aren't in the chart
  - Important context or comparisons not shown in the data
  - But even then, integrate it INTO the chart area, not as separate cards

## Space Management (CRITICAL for subtitle overlay!)
**To support adding subtitles later (supporting 2-3 line subtitles), must reserve top and bottom space!**

- **TOP 80-100px**: Keep clear for title (can be at top 25-30px) + potential subtitle overlay
- **BOTTOM 160-180px**: **CRITICAL!** Reserve for subtitle display (supporting 2-3 lines) - don't place chart axis labels, category names, or any important content here
  - **Minimum 160px** for single-line subtitles
  - **180px recommended** for 2-3 line subtitles to ensure no overlap
- **Chart area**: Should be in the MIDDLE zone (between top 100px and bottom 160-180px)
  - Bar chart: Bars + labels should end above bottom 180px (at least 20px gap from subtitle zone)
  - Scatter/line: X-axis label should be at y: 360-370 MAX (reserve bottom 180px for subtitles)
  - Pie chart: Legend on LEFT (x: 80-300), Chart on RIGHT (center x: 600+, radius: 160-180px)
    - Legend should not extend below bottom 180px
    - Ensure at least 120px gap between legend and pie chart to avoid overlap
- **Safe zone**: Visualize the layout as having a "subtitle bar" at bottom 0-180px that will cover content
- **Margins**: 40-60px left/right edges

### Axis Labels Positioning (for scatter/line charts):
- **Y-axis label**: Position at `x: -70` or more negative to avoid overlap
- **X-axis label**: Position at `y: 360-370` MAX (reserve bottom 180px for subtitles, supporting 2-3 lines)
- **X-axis tick labels**: Should be at `y: 340-350` or higher (at least 20px above X-axis label)
- **Chart drawing area**: Should end at y: 340-350 MAX (leaving 180px+ for subtitle zone)

# YOUR TASK

## Data to Visualize
Title: "{chart_title}"
Type: {chart_type}
Canvas: {video_meta.get('width', 1280)}x{video_meta.get('height', 720)}px

Data Sample:
{json.dumps(data[:3], indent=2, ensure_ascii=False)}

Data Binding:
{json.dumps(data_binding, indent=2, ensure_ascii=False)}

**🚨 CRITICAL: Multiple Y-Axis Support (Grouped Bar Chart)**
- **If `y_axis` is an ARRAY** (e.g., `[{{"field": "avg_depdelay", "label": "Departure Delay"}}, {{"field": "avg_arrdelay", "label": "Arrival Delay"}}]`):
  - You MUST create a **GROUPED BAR CHART** (not a single bar chart)
  - Each category (x_axis value) should have MULTIPLE bars side-by-side
  - Each bar represents one y_axis field
  - Use different colors for each y_axis field (e.g., bar_colors from style.bar_colors if available)
  - Add a legend to distinguish between different y_axis fields
  - Example: For "Average Departure vs Arrival Delays by Carrier":
    - Each carrier (MQ, OO, UA, etc.) should have TWO bars:
      - One bar for "avg_depdelay" (Departure Delay)
      - One bar for "avg_arrdelay" (Arrival Delay)
    - Use d3.scaleBand() for grouping: create sub-groups within each category
    - Bars should be positioned side-by-side with small gap between them
- **If `y_axis` is a DICT** (single field):
  - Create a standard single bar chart (one bar per category)

**Grouped Bar Chart Implementation Example:**
```typescript
// For multiple y_axis fields, use nested scales
const xScale = d3.scaleBand()
  .domain(data.map(d => d[xField]))
  .range([0, chartWidth])
  .padding(0.2);

const yAxisFields = data_binding.y_axis; // Array of fields
const subGroups = yAxisFields.map(y => y.field);
const xSubgroup = d3.scaleBand()
  .domain(subGroups)
  .range([0, xScale.bandwidth()])
  .padding(0.05);

// Draw bars for each y_axis field
yAxisFields.forEach((yAxisConfig, i) => {{
  const yField = yAxisConfig.field;
  const barColor = style.bar_colors?.[i] || defaultColors[i];
  
  g.selectAll(`.bar-${{yField}}`)
    .data(data)
    .enter()
    .append('rect')
    .attr('class', `bar-${{yField}}`)
    .attr('x', d => xScale(d[xField]) + xSubgroup(yField))
    .attr('y', d => yScale(d[yField]))
    .attr('width', xSubgroup.bandwidth())
    .attr('height', d => innerHeight - yScale(d[yField]))
    .attr('fill', barColor);
}});

// Add legend for multiple y_axis fields
const legend = g.append('g')
  .attr('transform', `translate(${{chartWidth - 200}}, 20)`);
yAxisFields.forEach((yAxisConfig, i) => {{
  const yField = yAxisConfig.field;
  const barColor = style.bar_colors?.[i] || defaultColors[i];
  legend.append('rect')
    .attr('x', 0)
    .attr('y', i * 25)
    .attr('width', 15)
    .attr('height', 15)
    .attr('fill', barColor);
  legend.append('text')
    .attr('x', 20)
    .attr('y', i * 25 + 12)
    .text(yAxisConfig.label)
    .attr('fill', textColor)
    .style('font-size', '14px');
}});
```

## Color Configuration (from JSON)
**🚨 CRITICAL: MUST use these background colors from JSON config (DO NOT change them!):**
- background_color: {background_color}
- container_background: {container_background}

**Other colors (LLM decides, based on scene semantics):**
- **bar_color/chart_color**: Choose primary color based on scene title and narration semantics
- **highlight_color**: Choose accent color that harmonizes with primary color (can be complementary or adjacent color)
- **text_color**: Ensure clear readability on background color (usually dark text on light background, light text on dark background)
- **grid_color/axis_color**: Choose auxiliary color that harmonizes with background color (usually slightly brighter or darker than background, maintain low contrast)

**Important**: All colors must harmonize with background color ({background_color}), but each scene should have unique primary color, avoid using the same color scheme for all scenes.

## Scene Context
- Data Count: {len(data)} items
- Chart Type: {chart_type}

## Design Decision Process

**Step 0 (VIDEO-LEVEL, decide once):**
- **Background colors are ALREADY determined in JSON config - MUST use them!**
  - background_color: {background_color} (MUST use this exact value)
  - container_background: {container_background} (MUST use this exact value)
  - **DO NOT change these colors - they are unified across all scenes!**

**Step 1-6 (SCENE-LEVEL, independent for each scene):**

1. **Analyze scene semantics and user requirements**:
   {semantic_context}
   - Extract core meaning and emotional tone
   - Understand what information this scene should convey
   {user_requirements_design_section}

2. **Choose theme color scheme** (based on scene semantics, LLM decides):
   - Analyze scene title and narration to determine semantic type (revenue/delay/growth/correlation, etc.)
   - Choose appropriate primary color (bar_color/chart_color) based on semantics
   - Choose harmonious accent color (highlight_color)
   - Ensure text color is clearly readable on background color
   - **Ensure harmony with background color ({background_color}), but each scene has unique hue**
   - **Avoid using the same color scheme as previous scenes**

3. **Choose layout** (based on data characteristics):
   - Data count: {len(data)} items
   - If data points >5 and need to show full picture → Chart-Dominant
   - If single prominent extreme value needs emphasis → Hero Number  
   - If need to show both chart and key metrics simultaneously → Split Focus

4. **Design highlight method** (ensure diversity):
   - Avoid using the same highlight technique as previous scenes
   - Can combine: gradient fill, glow effect, border emphasis, size contrast
   - Each scene should have unique visual focus

5. **Plan layout space** (CRITICAL!):
   - Chart height: ~350-400px (not too tall, must fit in middle zone)
   - Chart vertical position: Center in middle zone (not extending to bottom 160-180px)
   - Bottom 160-180px: Reserved for 2-3 line subtitle overlay (180px recommended for safety)
   - X-axis labels: Position at y ≤ 360-370 (leaving 180px+ for subtitle zone)
   - X-axis tick labels: Position at y ≤ 340-350 (at least 20px above X-axis label)

6. **Ensure visual diversity**:
   - Check if too similar to previous scenes
   - If similar, adjust hue, layout, or highlight method
   - Each scene should have obvious visual differences

# TECHNICAL REQUIREMENTS

## D3.js Selection and Indexing (CRITICAL!)
**⚠️ Important: When using selectAll with multiple class selectors, the index i in each() callback is the element index in the selection, NOT the data item index!**

**Problem Example (WRONG):**
```javascript
// ❌ WRONG: Assume processedData has 3 items, each item creates 2 elements
// selectAll('.legend-label, .legend-metrics') selects 6 elements (indices 0-5)
// But processedData only has 3 items (indices 0-2)
svg.selectAll('.legend-label, .legend-metrics').each(function(d: any, i: number) {{
  const dataItem = processedData[i];  // ❌ When i >= 3, dataItem is undefined!
  // This causes: TypeError: Cannot read properties of undefined (reading 'displayLabel')
}});
```

**✅ Recommended Solution: Use Data Binding (Safest)**
```javascript
// ✅ CORRECT: Bind data when creating elements, child elements will inherit data automatically
const legendItems = legendGroup.selectAll('.legend-item')
  .data(processedData)
  .enter()
  .append('g')
  .attr('class', 'legend-item');

// When creating child elements, data is automatically bound
legendItems.append('text')
  .attr('class', 'legend-label')
  .text(d => d.displayLabel);

legendItems.append('text')
  .attr('class', 'legend-metrics')
  .text(d => `${{formatNumber(d[valueField])}} (${{d.percentage.toFixed(1)}}%)`);

// When selecting later, data is already correctly bound
legendItems.selectAll('.legend-label, .legend-metrics').each(function(d: any) {{
  // ✅ d is the data item, not undefined!
  const isHighlighted = highlightedItems.has(d.displayLabel);
  d3.select(this).style('opacity', isHighlighted ? 1 : 0.3);
}});
```

**Alternative: If you must use multiple class selectors, calculate data index**
```javascript
// ✅ CORRECT: Each data item has 2 elements, so divide by 2
svg.selectAll('.legend-label, .legend-metrics').each(function(d: any, i: number) {{
  const dataIndex = Math.floor(i / 2);  // Convert element index to data index
  const dataItem = processedData[dataIndex];
  if (dataItem) {{  // ⚠️ Must check if exists!
    const isHighlighted = highlightedItems.has(dataItem.displayLabel);
    d3.select(this).style('opacity', isHighlighted ? 1 : 0.3);
  }}
}});
```

**Rules Summary:**
- ✅ **Prefer data binding**: Bind data when creating elements to avoid index issues
- ⚠️ **If you must use multiple class selectors**: Calculate data index (`Math.floor(i / number_of_elements)`) and check if data item exists
- ❌ **Avoid**: Directly using `processedData[i]` without checking index bounds

## D3.js select() and selectAll() - CRITICAL!
**⚠️ CRITICAL: When selecting EXISTING elements, use select() directly, NOT data().enter().select()!**

**❌ WRONG - Will cause "not a valid selector" error:**
```javascript
// ❌ WRONG: Using data().enter().select() on existing elements
g.selectAll('.axis-line')
  .data(['y-axis', 'x-axis'])
  .enter()
  .select(`.${{d => d}}`)  // ❌ Function becomes string ".(d) => d" - invalid selector!
  .selectAll('line, path')
  .attr('stroke', axisColor);
```

**✅ CORRECT - Select existing elements directly:**
```javascript
// ✅ CORRECT: Select existing elements with string selectors
g.select('.y-axis').selectAll('line, path').attr('stroke', axisColor);
g.select('.x-axis').selectAll('line, path').attr('stroke', axisColor);

// OR if you need to iterate over multiple selectors:
['y-axis', 'x-axis'].forEach(className => {{
  g.select(`.${{className}}`).selectAll('line, path').attr('stroke', axisColor);
}});
```

**Rules:**
- ✅ `select()` and `selectAll()` accept ONLY string selectors (e.g., `'.class'`, `'#id'`, `'g'`)
- ✅ Use `select()` or `selectAll()` directly for existing elements
- ❌ NEVER use functions, arrow functions, or template strings with functions in selectors
- ❌ Don't use `data().enter().select()` - `enter()` is only for creating NEW elements with `append()`
- ✅ If you need dynamic selectors, build the string first, then use it

## SVG Clarity Optimization (Important!)
**CRITICAL**: To avoid blurriness, must add the following optimizations:
1. **SVG tag**: Add `shapeRendering: 'geometricPrecision'` and `textRendering: 'geometricPrecision'`
2. **All text elements**: Add the following styles:
   - `.style('font-family', 'system-ui, -apple-system, sans-serif')`
   - `.style('-webkit-font-smoothing', 'antialiased')`
   - `.style('text-rendering', 'geometricPrecision')`
3. **Shadow filter (forbid old-style writing that causes blur!)**:
   - ✅ **Correct**: Use `feDropShadow` (only blurs shadow, doesn't affect original shape)
     ```javascript
     shadow.append('feDropShadow')
       .attr('dx', 0).attr('dy', 4)
       .attr('stdDeviation', 6)
       .attr('flood-opacity', 0.3);
     ```
   - ❌ **Forbidden**: Use `feGaussianBlur` + `feOffset` (will blur the entire shape!)
     ```javascript
     // ❌ Don't write like this! Will cause shape blur!
     shadow.append('feGaussianBlur').attr('stdDeviation', 4);
     shadow.append('feOffset').attr('dx', 0).attr('dy', 2);
     ```

## Axis Label Layout (scatter/line charts CRITICAL!)
**For charts with axes (scatter, line), avoid label overlap:**
1. **Y-axis label positioning**:
   ```javascript
   g.append('text')
     .attr('x', -70)  // ✅ At least -70 to avoid overlap with tick numbers!
     .attr('y', 200)  // chart height / 2
     .attr('text-anchor', 'middle')
     .attr('transform', 'rotate(-90, -70, 200)')  // Rotation center must also be updated!
     .text('Y Axis Label');
   ```
2. **X-axis label positioning**:
   ```javascript
   g.append('text')
     .attr('x', 350)  // chart width / 2
     .attr('y', 360)  // ✅ CRITICAL: Must be ≤ 370 to leave 180px for subtitle zone!
     .attr('text-anchor', 'middle')
     .text('X Axis Label');
   ```
   **⚠️ IMPORTANT**: X-axis label must be at y ≤ 370 (for 720px canvas, leaving bottom 180px for subtitles)
3. **Common mistake**: `x: -30` for Y-axis label → will overlap! Should use `x: -70` or more negative

## Logarithmic Scale Axis Handling (CRITICAL!)
**⚠️ Important: For logarithmic scales using `d3.scaleLog()`, the `.ticks()` method does not work as expected!**

**Problem**: Logarithmic scales automatically generate many ticks between each order of magnitude (powers of 10), causing too many x-axis ticks and crowding.

**Solution**: Must use `.tickValues()` to manually specify tick values, instead of `.ticks()`.

**Correct Example (scatter chart, x-axis is logarithmic scale)**:
```javascript
// ❌ Wrong: Using .ticks() will cause too many ticks
const xAxis = d3.axisBottom(xScale)
  .ticks(5)  // Invalid for logarithmic scale!
  .tickFormat((d: any) => {{
    if (d >= 1000000) return "$" + (d / 1000000) + "M";
    if (d >= 1000) return "$" + (d / 1000) + "K";
    return d.toString();
  }});

// ✅ Correct: Use .tickValues() to manually specify tick values
// Choose appropriate tick values based on data range (usually multiples of 1, 2, 5, 10)
const xAxis = d3.axisBottom(xScale)
  .tickValues([1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, 50000000])
  .tickFormat((d: any) => {{
    if (d >= 1000000) return "$" + (d / 1000000) + "M";
    if (d >= 1000) return "$" + (d / 1000) + "K";
    return d.toString();
  }});

// Grid lines must also use the same tickValues
g.append('g')
  .attr('class', 'grid-x')
  .attr('transform', 'translate(0, 400)')
  .call(d3.axisBottom(xScale)
    .tickValues([1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, 50000000])
    .tickSize(-400)
    .tickFormat(() => "")
  );
```

**Tick Value Selection Principles**:
- Choose based on data min and max value range
- Usually choose multiples of 1, 2, 5, 10 for each order of magnitude (e.g., 1K, 2K, 5K, 10K, 20K, 50K, 100K...)
- Control tick count between 6-10, avoid too many
- Ensure tick values cover the entire data range

**When to Use Logarithmic Scale**:
- Data range spans multiple orders of magnitude (e.g., 1K to 50M)
- Data distribution shows exponential growth
- Need to better show relationship between small and large values

## Component Template
```typescript
import React, {{useEffect, useRef, useMemo}} from 'react';
import {{ AbsoluteFill }} from 'remotion';
import * as d3 from 'd3';

export const {component_name}: React.FC = () => {{
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = {json.dumps(data, indent=2, ensure_ascii=False)};
  
  // Extract field names from data_binding (see Data Binding JSON above)
  // 👈 CRITICAL: Read field names from the data_binding object provided above
  // - If data_binding has x_axis (dict): use data_binding.x_axis.field
  // - If data_binding has category (dict): use data_binding.category.field
  // - If data_binding.y_axis is an ARRAY: create grouped bar chart (see instructions above)
  // - If data_binding.y_axis is a DICT: create single bar chart
  // Example for single y_axis:
  //   const xField = data_binding.x_axis?.field || 'category';
  //   const yField = data_binding.y_axis?.field || 'value';
  // Example for multiple y_axis (array):
  //   const xField = data_binding.x_axis?.field || 'category';
  //   const yAxisFields = data_binding.y_axis; // Array of {{field, label}} objects
  //   // Then iterate through yAxisFields to create grouped bars
  
  // Color configuration
  // 👈 MUST use these background colors from JSON config (DO NOT change them!)
  const backgroundColor = '{background_color}';
  const containerBackground = '{container_background}';
  
  // 👈 Other colors: Choose based on scene semantics (title + narration)
  // Select colors that coordinate with backgroundColor but create unique identity for this scene
  // Example: If scene is about "Revenue Growth", use golden/amber colors (#fbbf24, #f59e0b)
  //          If scene is about "Departure Delays", use red/orange colors (#ef4444, #f97316)
  //          Ensure colors are harmonious with backgroundColor (adjacent 30-90° on color wheel)
  const textColor = '#e8eaed';  // Choose based on background: light text for dark bg, dark text for light bg
  const barColor = '#5b8ff9';   // Choose based on scene semantics (revenue→gold, delay→red, growth→green, etc.)
  const highlightColor = '#ff6b6b';  // Choose complementary or adjacent color to barColor
  const gridColor = '#555555';  // Choose subtle color that coordinates with backgroundColor
  const axisColor = '#888888';  // Choose subtle color that coordinates with backgroundColor
  
  // Calculate metrics
  // 👈 NOTE: This is an example for SINGLE y_axis. For multiple y_axis (array), 
  // you need to calculate maxValue across all y_axis fields, or handle each field separately.
  // Example for single y_axis:
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const avgValue = d3.mean(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // D3 scales
  // 👈 CRITICAL: Choose the right scale type based on data:
  // - For TIME-BASED data (line/scatter charts with dates): Use scaleTime + processedData
  // - For CATEGORICAL data (bar charts): Use scaleBand (no processedData needed)
  
  // Example 1: TIME-BASED data (line/scatter charts with dates)
  // ⚠️ CRITICAL: processedData MUST be in component scope if used in useEffect dependency arrays!
  const processedData = useMemo(() => {{
    const parseDate = d3.timeParse('%m/%d/%Y');  // Adjust format as needed (e.g., '%Y-%m-%d')
    return data.map(d => ({{
      ...d,
      parsedDate: parseDate(d[xField])
    }})).filter(d => d.parsedDate !== null).sort((a, b) => a.parsedDate - b.parsedDate);
  }}, [data]);
  
  const scales = useMemo(() => {{
    // For time-based: use scaleTime
    const xScale = d3.scaleTime()
      .domain(d3.extent(processedData, (d: any) => d.parsedDate) as [Date, Date])
      .range([0, 800]);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([320, 0]);  // ✅ Chart height ~320px (leaving 180px for subtitle zone)
    return {{ xScale, yScale }};  // ✅ Don't return processedData, it's already in component scope
  }}, [processedData, maxValue]);
  
  // Example 2: CATEGORICAL data (bar charts) - SINGLE y_axis
  // 👈 For multiple y_axis, you need nested scales (xScale + xSubgroup) as shown in instructions above
  // const scales = useMemo(() => {{
  //   const xScale = d3.scaleBand()
  //     .domain(data.map((d: any) => d[xField]))
  //     .range([0, 900])
  //     .padding(0.2);
  //   const yScale = d3.scaleLinear()
  //     .domain([0, maxValue * 1.1])
  //     .range([500, 0]);
  //   return {{ xScale, yScale }};
  // }}, [data]);
  
  // Static D3 rendering
  useEffect(() => {{
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Add gradients/shadows in <defs> based on semantic analysis
    const defs = svg.append('defs');
    
    // Create gradient based on scene semantics (choose colors that match scene meaning)
    // Example: For financial data, use golden gradient; for delays, use red-orange gradient
    const gradient = defs.append('linearGradient')
      .attr('id', 'accentGradient')
      .attr('x1', '0%').attr('y1', '0%')
      .attr('x2', '0%').attr('y2', '100%');
    // Choose gradient colors based on scene semantics (e.g., gold for revenue, red for delays, green for growth)
    gradient.append('stop').attr('offset', '0%').attr('stop-color', barColor);  // Use lighter shade
    gradient.append('stop').attr('offset', '100%').attr('stop-color', highlightColor);  // Use darker shade
    
    // Optional: Shadow filter (use feDropShadow to avoid blur!)
    const shadow = defs.append('filter').attr('id', 'shadow');
    shadow.append('feDropShadow')
      .attr('dx', 0)
      .attr('dy', 4)
      .attr('stdDeviation', 6)
      .attr('flood-opacity', 0.3);
    
    // Draw chart with proper spacing to avoid label overlap
    const g = svg.append('g').attr('transform', 'translate(80, 40)');
    const {{xScale, yScale}} = scales;
    
    // Draw bars (highlight max value with accent color)
    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('x', (d: any) => xScale(d[xField]) || 0)
      .attr('y', (d: any) => yScale(d[yField]))
      .attr('width', xScale.bandwidth())
      .attr('height', (d: any) => 320 - yScale(d[yField]))  // ✅ Chart height ~320px (leaving 180px for subtitle)
      .attr('fill', (d: any) => d[yField] === maxValue ? 'url(#accentGradient)' : barColor)
      .attr('rx', 8)
      .style('filter', 'url(#shadow)');
    
    // Value labels on top of bars
    g.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', (d: any) => yScale(d[yField]) - 15)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[yField])  // Format appropriately (e.g., "$620B")
      .attr('fill', (d: any) => d[yField] === maxValue ? highlightColor : textColor)
      .style('font-size', '18px')
      .style('font-weight', '700');
    
    // Category labels below chart
    // ⚠️ CRITICAL: y: 360-370 MAX to leave bottom 180px for subtitle (supporting 2-3 lines)!
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 360)  // ✅ 360 safe zone (bottom 180px reserved for 2-3 line subtitle)
      .attr('text-anchor', 'middle')
      .text((d: any) => d[xField])
      .attr('fill', textColor)
      .style('font-size', '16px');
  }}, [scales, maxValue]);
  
  return (
    <AbsoluteFill style={{{{ 
      background: '{container_background}',  // 👈 MUST use JSON config value: {container_background}
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '60px 40px'
    }}}}>
      {{/* Title */}}
      <div style={{{{
        position: 'absolute',
        top: 30,
        fontSize: '36px',
        fontWeight: '700',
        color: '#f8fafc',
        textAlign: 'center',
      }}}}>
        {chart_title}
      </div>
      
      {{/* Chart - centered, with space for labels */}}
      <svg 
        ref={{svgRef}} 
        width={{960}} 
        height={{550}} 
        style={{{{ 
          marginTop: '20px',
          shapeRendering: 'geometricPrecision',
          textRendering: 'geometricPrecision'
        }}}} 
      />
      
      {{{{/* NO EXTRA CARDS/METRICS - data labels on chart elements are enough! */}}}}
      {{{{/* ❌ DO NOT add fixed tooltip/info boxes like: <div>App C: 10M installs, 4.6★</div> */}}}}
      {{{{/* ✅ Highlight key data IN THE CHART ITSELF with size/color/stroke, not separate cards */}}}}
    </AbsoluteFill>
  );
}};
```

## CRITICAL RULES
✅ **STATIC ONLY** - No animations, no `spring()`, no `interpolate()`, no `useCurrentFrame()`
✅ **CLEAN & MINIMAL** - Simple design, 2-3 colors max, whitespace, clear hierarchy
✅ **DATA FIRST** - Chart should be large and readable, numbers formatted clearly
✅ **SUBTITLE SPACE** - Keep top 80px relatively clear for subtitle overlay, **BOTTOM 180px MUST be reserved** for subtitle display
✅ **SEMANTIC COLORS** - Match color to data meaning (gold=money, red=problem, green=growth)
✅ **HIGHLIGHT KEY DATA** - Use accent color/size for max/min/outlier IN THE CHART ITSELF
✅ **NO EXTRA METRICS** - Data labels on bars/points are sufficient, don't add separate stat cards
✅ **AVOID OVERLAP** - Ensure value labels and category labels have enough space (at least 40px apart)
✅ **PIE CHART LAYOUT** (if pie_chart):
  - Legend on LEFT side: x = 80-320 (width ~240px)
  - Pie chart on RIGHT side: center x = 640 (NOT 480!), radius = 160-180px
  - This creates ~200px gap between legend and chart, avoiding overlap
  - Example: `svg.append('g').attr('transform', 'translate(640, 280)')` for pie center

❌ **DO NOT**:
- Add "LEADER", "HIGHEST", "AVERAGE" stat cards (data labels are enough!)
- Add fixed tooltip/info boxes showing specific data point details (e.g., "App C: 10M installs, 4.6★" in a corner box)
- Add decorative information boxes in corners or sides that duplicate chart labels
- Put text/cards at bottom that overlaps with chart labels
- Copy "3 cards + chart" layout for every scene
- Over-decorate with gradients/shadows on everything
- Make subtitle area dense (keep top 80px breathable)
- **Remember: Data labels on chart elements are sufficient - highlight key data IN THE CHART with size/color/stroke, NOT with separate cards!**

## OUTPUT
Generate ONLY the complete TypeScript code - NO markdown blocks, NO explanations.
Start with imports, end with closing brace.
All D3 elements should be in FINAL visible state (full height, opacity 1).
Write every string literal in full (e.g. .style('filter', '...') and rgba(r,g,b,a) must be complete with closing quotes and parentheses).
"""
    return prompt


def generate_tsx_component(scene_data, video_meta, llm_client, output_path, verbose=True, scene_index=1, total_scenes=1):
    """
    使用 Claude 生成完整的 TSX 组件
    """
    scene_id = scene_data.get('id', 'unknown')
    chart_title = scene_data.get('content', {}).get('title', 'Visualization')
    
    # 从文件名生成组件名（例如：SceneChart1.tsx -> SceneChart1Component）
    base_name = os.path.splitext(os.path.basename(output_path))[0]  # SceneChart1
    component_name = f"{base_name}Component"  # SceneChart1Component
    
    if verbose:
        print(f"\n🎨 场景: {scene_id} ({scene_index}/{total_scenes})")
        print(f"   标题: {chart_title}")
        print(f"   组件名: {component_name}")
        content = scene_data.get('content', {})
        chart_type = content.get('chart_type', 'bar_chart')
        data = content.get('data', [])
        data_binding = content.get('data_binding', {})
        print(f"   图表类型: {chart_type}")
        # 检查是否是多Y轴
        y_axis_data = data_binding.get('y_axis', {})
        if isinstance(y_axis_data, list):
            print(f"   Y轴: 多Y轴 ({len(y_axis_data)} 个字段)")
            for i, y_axis in enumerate(y_axis_data, 1):
                if isinstance(y_axis, dict):
                    print(f"      - Y轴{i}: {y_axis.get('label', y_axis.get('field', 'unknown'))}")
        elif isinstance(y_axis_data, dict):
            print(f"   Y轴: {y_axis_data.get('label', y_axis_data.get('field', 'unknown'))}")
        print(f"   数据量: {len(data)} 条")
        print(f"   正在调用 Claude API（让 LLM 确定统一风格）...")
    
    # 构造 Prompt（直接传入完整 scene_data，让 LLM 自己解析）
    prompt = create_tsx_generation_prompt(scene_data, video_meta, component_name, scene_index, total_scenes)
    response = None
    try:
        # 调用 Claude API（使用大 token 数，确保不截断；提高temperature增加创造性）
        response, usage = llm_client.call(prompt, temperature=0.85, max_tokens=settings.LLM_MAX_TOKENS)
        
        # 清理响应
        tsx_code = response.strip()
        if tsx_code.startswith("```typescript") or tsx_code.startswith("```tsx"):
            tsx_code = tsx_code.split('\n', 1)[1]  # Remove first line
        if tsx_code.startswith("```"):
            tsx_code = tsx_code[3:]
        if tsx_code.endswith("```"):
            tsx_code = tsx_code[:-3]
        tsx_code = tsx_code.strip()
        tsx_code = sanitize_tsx_for_browser(tsx_code)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tsx_code)
        
        if verbose:
            print(f"   ✅ 生成成功: {os.path.basename(output_path)}")
            print(f"   文件大小: {len(tsx_code)} 字符")
        
        is_valid, syntax_err = validate_component_syntax(Path(output_path))
        if not is_valid:
            err_msg = f"语法验证失败: {syntax_err}"
            if verbose:
                print(f"   ❌ {err_msg}")
            return (False, err_msg)
        if verbose:
            print(f"   ✅ 语法验证通过")
        return (True, None)
    
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        print(f"   ❌ 图表 TSX 生成失败 [{chart_title}]: {err_msg}", flush=True)
        traceback.print_exc()
        if response is not None and len(response) > 0:
            snippet = (response[:500] if isinstance(response, str) else str(response)[:500]).replace("\n", " ")
            print(f"   📄 响应片段 (前500字符): {snippet}...", flush=True)
        return (False, err_msg)


def generate_single_scene_wrapper(
    scene,
    idx: int,
    total: int,
    video_meta,
    llm_client,
    output_dir: str,
    task_id: str = None,
    max_retries: int = 5,
) -> Tuple[int, str, bool, str]:
    """
    包装函数，用于并行执行（带校验+重试）
    """
    scene_id = scene.get('id', f'scene_{idx}')
    dataset_name = extract_dataset_name(video_meta)
    scene_id_camel = ''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())
    if task_id:
        component_name = f"{dataset_name}_{scene_id_camel}_{task_id}"
    else:
        component_name = f"{dataset_name}_{scene_id_camel}"
    output_file = os.path.join(output_dir, f"{component_name}.tsx")
    chart_title = scene.get('content', {}).get('title', 'Visualization')
    last_error = None
    start_time = time.time()
    attempt = 0
    while True:
        attempt += 1
        elapsed = time.time() - start_time
        try:
            success, error_detail = generate_tsx_component(
                scene, video_meta, llm_client, output_file,
                verbose=(attempt > 1), scene_index=idx, total_scenes=total
            )
            if success:
                file_size = os.path.getsize(output_file)
                retry_info = f" (重试 {attempt}次)" if attempt > 1 else ""
                return (idx, scene_id, True, f"✅ {chart_title} ({file_size} 字节){retry_info}")
            last_error = error_detail or "生成失败"
        except Exception as e:
            last_error = str(e)
        if attempt >= max_retries:
            should_retry, reason = False, f"已达到最大重试次数（{max_retries}次）"
        else:
            should_retry, reason = should_retry_on_error(last_error, attempt, elapsed, max_general_retries=max_retries)
        if should_retry:
            wait_time = calculate_retry_wait_time(last_error, attempt)
            print(f"   ⚠️  [{idx}/{total}] {chart_title} - 第 {attempt} 次失败，{wait_time}秒后重试...", flush=True)
            time.sleep(wait_time)
            continue
        print(f"   ❌ [{idx}/{total}] {chart_title} - 停止重试: {reason}", flush=True)
        break
    detail = f" - {last_error}" if last_error else " - 生成失败"
    return (idx, scene_id, False, f"❌ {chart_title}{detail} (尝试 {attempt} 次后失败)")


def main():
    default_config_path = os.getenv(
        "VIDEO_DEFAULT_CONFIG_PATH",
        "infographic_generation/generated_config_aligned.json",
    )
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='生成 TSX 信息图组件（默认并行模式）')
    parser.add_argument('--serial', action='store_true', help='使用串行模式（默认是并行）')
    parser.add_argument('-w', '--workers', type=int, default=4, help='并行线程数（默认4）')
    parser.add_argument('--config', type=str, 
                       default=default_config_path,
                       help='配置文件路径')
    parser.add_argument('--output', type=str,
                       default=DEFAULT_COMPONENTS_OUTPUT_DIR,
                       help='输出目录（基础路径）')
    parser.add_argument('--task-id', type=str, default=None,
                       help='任务ID（用于创建子目录隔离组件）')
    args = parser.parse_args()
    
    # 默认并行，除非指定 --serial
    use_parallel = not args.serial
    
    # 读取配置文件
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    video_meta = config.get('meta', {})
    all_scenes = config.get('scenes', [])
    
    # 如果提供了 task_id，则创建子目录
    if args.task_id:
        output_dir = os.path.join(args.output, args.task_id)
        print(f"📁 使用任务子目录: {output_dir}")
    else:
        output_dir = args.output
        print(f"📁 使用默认输出目录: {output_dir}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化 LLM 客户端
    mode_text = "并行模式" if use_parallel else "串行模式"
    workers_text = f"，{args.workers} 线程" if use_parallel else ""
    print(f"🚀 初始化 LLM 客户端 (Claude Sonnet 4，{mode_text}{workers_text})...")
    
    llm_client = LLMClient(
        api_base=API_BASE,
        api_key=API_KEY,
        model=DEFAULT_MODEL
    )
    
    # 提取图表场景
    chart_scenes = [s for s in all_scenes if s['type'] == 'chart']
    
    print(f"\n📊 视频标题: {video_meta.get('title', 'N/A')}")
    print(f"📊 共找到 {len(chart_scenes)} 个图表场景")
    print("="*70)
    
    success_count = 0
    
    if use_parallel:
        # 并行模式
        print(f"⚡ 使用并行模式生成（{args.workers} 个线程）...\n")
        results = []
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            # 提交所有任务
            future_to_scene = {
                executor.submit(
                    generate_single_scene_wrapper,
                    scene,
                    idx,
                    len(chart_scenes),
                    video_meta,
                    llm_client,
                    output_dir,
                    args.task_id
                ): idx
                for idx, scene in enumerate(chart_scenes, 1)
            }
            
            # 收集结果（按完成顺序）
            for future in as_completed(future_to_scene):
                idx, scene_id, success, message = future.result()
                results.append((idx, scene_id, success, message))
                print(f"[{idx}/{len(chart_scenes)}] {message}")
                if success:
                    success_count += 1
        
        # 按原始顺序排序（可选）
        results.sort(key=lambda x: x[0])
    else:
        # 串行模式（带校验+重试）
        print("📝 使用串行模式生成...\n")
        max_retries = 5
        for idx, scene in enumerate(chart_scenes, 1):
            scene_id = scene.get('id', f'scene_{idx}')
            dataset_name = extract_dataset_name(video_meta)
            component_name = f"{dataset_name}_{''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())}"
            output_file = os.path.join(output_dir, f"{component_name}.tsx")
            print(f"[{idx}/{len(chart_scenes)}]", end=" ")
            last_error = None
            start_time = time.time()
            for attempt in range(1, max_retries + 1):
                success, error_detail = generate_tsx_component(
                    scene, video_meta, llm_client, output_file,
                    verbose=True, scene_index=idx, total_scenes=len(chart_scenes)
                )
                if success:
                    success_count += 1
                    break
                last_error = error_detail or "生成失败"
                elapsed = time.time() - start_time
                should_retry, reason = should_retry_on_error(last_error, attempt, elapsed, max_general_retries=max_retries)
                if not should_retry or attempt == max_retries:
                    print(f"   ❌ 停止重试: {reason}", flush=True)
                    break
                wait_time = calculate_retry_wait_time(last_error, attempt)
                print(f"   ⚠️ 第 {attempt} 次失败，{wait_time}秒后重试...", flush=True)
                time.sleep(wait_time)
    
    # 总结
    print("\n" + "="*70)
    print(f"\n🎉 生成完成！")
    print(f"   成功: {success_count}/{len(chart_scenes)}")
    print(f"   输出目录: {output_dir}")
    print(f"\n📺 如何查看生成的场景：")
    print(f"\n   方法 1: 直接在浏览器打开 HTML 预览（推荐）")
    print(f"   -----------------------------------------------")
    print(f"   生成的组件在: {output_dir}/")
    print(f"   每个 .tsx 文件旁会自动生成 .html 预览文件")
    print(f"   双击 .html 文件即可在浏览器查看静态效果")
    print(f"\n   方法 2: 在 Remotion Studio 中预览（需要先注册）")
    print(f"   -----------------------------------------------")
    print(f"   1. 复制生成的 .tsx 文件到 src/components/CustomInfographic/")
    print(f"   2. 在 src/Root.tsx 中注册为 Composition")
    print(f"   3. 运行 'npm run dev' 启动 Remotion Studio")
    print(f"   4. 在浏览器中选择对应的 Composition 预览")
    print(f"\n   方法 3: 自动批量注册并预览")
    print(f"   -----------------------------------------------")
    print(f"   运行自动化脚本（如果有）可一键完成上述步骤")
    print(f"\n📂 现在可以打开 {output_dir} 目录查看生成的组件！")


if __name__ == "__main__":
    main()
