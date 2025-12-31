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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

# 导入项目现有的 LLM 客户端
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config_generation'))
from generator import LLMClient


def extract_scene_info(scene_data):
    """
    提取场景信息，供 LLM 分析（不做预判断）
    """
    content = scene_data.get('content', {})
    chart_title = content.get('title', 'Visualization')
    chart_type = content.get('chart_type', 'bar_chart')
    data = content.get('data', [])
    data_binding = content.get('data_binding', {})
    
    # 提取轴标签
    x_label = ''
    y_label = ''
    if 'x_axis' in data_binding:
        x_label = data_binding.get('x_axis', {}).get('label', '')
    elif 'category' in data_binding:
        x_label = data_binding.get('category', {}).get('label', '')
    
    if 'y_axis' in data_binding:
        y_label = data_binding.get('y_axis', {}).get('label', '')
    elif 'value' in data_binding:
        y_label = data_binding.get('value', {}).get('label', '')
    
    # 计算数据范围（帮助 LLM 理解数据规模）
    if data and len(data) > 0:
        y_field = data_binding.get('y_axis', {}).get('field') or data_binding.get('value', {}).get('field')
        if y_field:
            values = [d.get(y_field, 0) for d in data if isinstance(d.get(y_field), (int, float))]
            if values:
                data_range = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values)
                }
            else:
                data_range = None
        else:
            data_range = None
    else:
        data_range = None
    
    return {
        'title': chart_title,
        'chart_type': chart_type,
        'x_label': x_label,
        'y_label': y_label,
        'data_sample': data[:3],  # 前3条数据作为样本
        'data_count': len(data),
        'data_range': data_range
    }


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


def create_tsx_generation_prompt(scene_data, video_meta, scene_info, component_name="SceneComponent", scene_index=1, total_scenes=1):
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
        user_requirements_design_section = "- **用户要求**: " + quote_char + user_query + quote_char + " - 在设计时考虑这些要求（如用户要求强调某些模式、对比、趋势等）"
    
    # 提取字段名（避免在f-string中使用复杂表达式）
    x_field_expr = data_binding.get('x_axis', {}).get('field') or data_binding.get('category', {}).get('field', 'category')
    y_field_expr = data_binding.get('y_axis', {}).get('field') or data_binding.get('value', {}).get('field', 'value')
    
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

## Visual Style (背景色已统一！)

**🚨 CRITICAL: Background colors are ALREADY determined in JSON config!**

**MUST use these exact values (DO NOT change them):**
- background_color: {background_color}
- container_background: {container_background}

**These colors are already unified across all scenes in the video - you MUST use them!**

### 场景差异化策略（在统一背景下）：

**🎨 主题色选择（基于场景语义，LLM自己决定）：**

1. **分析场景语义**：
   {semantic_context}
   - 理解场景的核心含义（是revenue/delay/growth/correlation/distribution等）
   - 判断情感倾向（积极/消极/中性）

2. **颜色选择原则**（根据场景语义灵活选择）：
   - **Financial/Revenue相关** → 金色/琥珀色系（#fbbf24, #f59e0b, #d97706等）
   - **Problems/Delays相关** → 红色/橙色系（#ef4444, #f97316, #dc2626等）
   - **Growth/Positive相关** → 绿色/青色系（#10b981, #059669, #34d399等）
   - **Correlation/Relationship** → 蓝紫色系（#3b82f6, #8b5cf6, #6366f1等）
   - **Distribution/Share** → 多色渐变或彩虹色系
   - **Neutral/Analysis** → 根据背景色选择协调的色系（与背景色在色相环上相邻30-90度）

3. **颜色协调性**：
   - 确保选择的颜色与背景色({background_color})协调
   - 可以使用色相环上相邻30-90度的颜色，或互补色（180度）
   - 保持整体色调统一，但每个场景有独特的主色调

4. **实现方式**：
   - 可以使用线性渐变（从主色到辅助色）
   - 高亮元素可以使用对比色或互补色
   - 文本颜色要确保在背景色上清晰可读

**布局选择**（根据数据特点）：
- **Chart-Dominant** (80%宽度)：数据点较多(>5个)，需要展示全貌
- **Split Focus** (60%图表+40%指标)：有1-2个关键指标需要突出
- **Hero Number** (中心大数字+小图表)：单一数值特别重要，需要强调

**高亮方式多样性**：
- 渐变填充（从浅到深）
- 发光效果（drop-shadow）
- 边框强调（stroke）
- 大小对比（scale）
- 每个场景使用不同的组合方式，避免重复

**图标**：每个场景 0-1 个语义相关的图标

### 字体：
- Title: 32-36px, bold
- Chart labels: 14-16px, readable
- Key numbers: 28-48px, prominent

## Icon Usage (MINIMAL!)
- **Use 0-1 icons ONLY** (not 2-3!)
- Icon must ACCURATELY match the data's semantic meaning
- Place near title OR next to the max/min bar
- Unicode emoji preferred

**Icon Semantic Matching Guide** (choose carefully!):
- **Problems/Alerts**: ⚠️ 🚨 → ONLY for actual warnings, issues, failures, high delays
- **Analysis/Data**: 📊 📉 → for neutral data analysis, statistical studies, comparisons
- **Correlation/Relationships**: 🔗 📈 → for relationship analysis, trends, connections
- **Money/Finance**: 💰 💵 → for revenue, profit, costs, financial metrics
- **Growth/Success**: 📈 🚀 ✅ → for positive growth, improvements, achievements
- **Distribution/Share**: 🥧 → for pie charts, market share, percentages
- **Comparison**: ⚖️ → for A vs B comparisons, balance
- **Exploration**: 🔍 → for insights, discovery, deep analysis

**Common Mistakes to Avoid**:
- ❌ "Correlation Between X and Y" with ⚠️ → Should use 📊 or 🔗 (it's analysis, not a warning!)
- ❌ "Market Share Distribution" with 💰 → Should use 🥧 (it's distribution, not money!)
- ✅ "Highest Departure Delays" with ⚠️ → Correct! (it IS a problem)
- ✅ "Revenue Growth" with 💰 or 📈 → Correct!

**NO scattered icons everywhere!**

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
**为了后续添加字幕（支持2-3行长字幕），必须预留顶部和底部空间！**

- **TOP 80-100px**: Keep clear for title (can be at top 25-30px) + potential subtitle overlay
- **BOTTOM 130px**: **CRITICAL!** Reserve for subtitle display (支持2-3行) - don't place chart axis labels, category names, or any important content here
- **Chart area**: Should be in the MIDDLE zone (between top 100px and bottom 130px)
  - Bar chart: Bars + labels should end above bottom 150px
  - Scatter/line: X-axis label should be at y: 390-410 MAX (留出底部 130px 给字幕)
  - Pie chart: Legend on LEFT (x: 80-300), Chart on RIGHT (center x: 600+, radius: 160-180px)
    - Legend should not extend below bottom 150px
    - Ensure at least 120px gap between legend and pie chart to avoid overlap
- **Safe zone**: Visualize the layout as having a "subtitle bar" at bottom 0-130px that will cover content
- **Margins**: 40-60px left/right edges

### Axis Labels Positioning (for scatter/line charts):
- **Y-axis label**: Position at `x: -70` or more negative to avoid overlap
- **X-axis label**: Position at `y: 390` MAX (留出底部 130px 给字幕，支持2-3行)
- **X-axis tick labels**: Should be at `y: 370` or higher

# YOUR TASK

## Data to Visualize
Title: "{chart_title}"
Type: {chart_type}
Canvas: {video_meta.get('width', 1280)}x{video_meta.get('height', 720)}px

Data Sample:
{json.dumps(data[:3], indent=2, ensure_ascii=False)}

Data Binding:
{json.dumps(data_binding, indent=2, ensure_ascii=False)}

## Color Configuration (from JSON)
**🚨 CRITICAL: MUST use these background colors from JSON config (DO NOT change them!):**
- background_color: {background_color}
- container_background: {container_background}

**其他颜色（LLM自己决定，基于场景语义）：**
- **bar_color/chart_color**: 根据场景标题和旁白语义选择主色调
- **highlight_color**: 选择与主色调协调的强调色（可以是互补色或相邻色）
- **text_color**: 确保在背景色上清晰可读（通常浅色背景用深色文字，深色背景用浅色文字）
- **grid_color/axis_color**: 选择与背景色协调的辅助色（通常比背景色稍亮或稍暗，保持低对比度）

**重要**：所有颜色必须与背景色({background_color})协调，但每个场景应该有独特的主色调，避免所有场景使用相同的颜色方案。

## Scene Context
- Data Count: {scene_info['data_count']} items
{("" if not scene_info.get('data_range') else f"- Value Range: {scene_info['data_range']['min']:.1f} ~ {scene_info['data_range']['max']:.1f} (avg: {scene_info['data_range']['avg']:.1f})")}

## Design Decision Process

**Step 0 (VIDEO-LEVEL, 只决策一次):**
- **Background colors are ALREADY determined in JSON config - MUST use them!**
  - background_color: {background_color} (MUST use this exact value)
  - container_background: {container_background} (MUST use this exact value)
  - **DO NOT change these colors - they are unified across all scenes!**

**Step 1-6 (SCENE-LEVEL, 每个场景独立):**

1. **分析场景语义和用户要求**：
   {semantic_context}
   - 提取核心含义和情感倾向
   - 理解这个场景要传达什么信息
   {user_requirements_design_section}

2. **选择主题色系**（根据场景语义，LLM自己决定）：
   - 分析场景标题和旁白，确定语义类型（revenue/delay/growth/correlation等）
   - 根据语义选择合适的主色调（bar_color/chart_color）
   - 选择协调的强调色（highlight_color）
   - 确保文本颜色在背景色上清晰可读
   - **确保与背景色({background_color})协调，但每个场景有独特色相**
   - **避免与前面场景使用相同的颜色方案**

3. **选择布局**（根据数据特点）：
   - 数据量: {scene_info['data_count']} 个
   - 如果数据点>5且需要展示全貌 → Chart-Dominant
   - 如果有单一突出极值需要强调 → Hero Number  
   - 如果需要同时展示图表和关键指标 → Split Focus

4. **设计高亮方式**（确保多样性）：
   - 避免与前面场景使用相同的高亮手法
   - 可以组合使用：渐变填充、发光效果、边框强调、大小对比
   - 每个场景应该有独特的视觉重点

5. **规划布局空间**（CRITICAL!）：
   - Chart height: ~380-430px (not too tall)
   - Chart vertical position: Center in middle zone (not extending to bottom 130px)
   - Bottom 130px: Reserved for 2-3 line subtitle overlay
   - X-axis labels: Position at y ≤ 390

6. **添加0-1个图标**：根据语义精确匹配

7. **确保视觉多样性**：
   - 检查是否与前面场景过于相似
   - 如果相似，调整色相、布局或高亮方式
   - 每个场景应该有明显的视觉差异

# TECHNICAL REQUIREMENTS

## SVG 清晰度优化（重要！）
**CRITICAL**: 为了避免模糊，必须添加以下优化：
1. **SVG 标签**：添加 `shapeRendering: 'geometricPrecision'` 和 `textRendering: 'geometricPrecision'`
2. **所有文本元素**：添加以下样式：
   - `.style('font-family', 'system-ui, -apple-system, sans-serif')`
   - `.style('-webkit-font-smoothing', 'antialiased')`
   - `.style('text-rendering', 'geometricPrecision')`
3. **阴影滤镜（禁止导致模糊的老式写法！）**：
   - ✅ **正确**: 使用 `feDropShadow`（只模糊阴影，不影响原图形）
     ```javascript
     shadow.append('feDropShadow')
       .attr('dx', 0).attr('dy', 4)
       .attr('stdDeviation', 6)
       .attr('flood-opacity', 0.3);
     ```
   - ❌ **禁止**: 使用 `feGaussianBlur` + `feOffset`（会模糊整个图形！）
     ```javascript
     // ❌ 不要这样写！会导致图形模糊！
     shadow.append('feGaussianBlur').attr('stdDeviation', 4);
     shadow.append('feOffset').attr('dx', 0).attr('dy', 2);
     ```

## 坐标轴标签布局（散点图/折线图 CRITICAL！）
**For charts with axes (scatter, line), avoid label overlap:**
1. **Y-axis label positioning**:
   ```javascript
   g.append('text')
     .attr('x', -70)  // ✅ 至少 -70 才不会与刻度数字重叠！
     .attr('y', 200)  // chart height / 2
     .attr('text-anchor', 'middle')
     .attr('transform', 'rotate(-90, -70, 200)')  // 旋转中心也要更新！
     .text('Y Axis Label');
   ```
2. **X-axis label positioning**:
   ```javascript
   g.append('text')
     .attr('x', 350)  // chart width / 2
     .attr('y', 450)  // 比最下方的刻度标签低至少 30px
     .attr('text-anchor', 'middle')
     .text('X Axis Label');
   ```
3. **Common mistake**: `x: -30` for Y-axis label → 会重叠！应该用 `x: -70` 或更负

## 对数刻度轴处理（CRITICAL！）
**⚠️ 重要：对于使用 `d3.scaleLog()` 的对数刻度，`.ticks()` 方法不会按预期工作！**

**问题**：对数刻度会在每个数量级（10的幂）之间自动生成大量刻度，导致 x 轴刻度过多、拥挤不堪。

**解决方案**：必须使用 `.tickValues()` 手动指定刻度值，而不是 `.ticks()`。

**正确示例（散点图，x 轴为对数刻度）**：
```javascript
// ❌ 错误：使用 .ticks() 会导致刻度过多
const xAxis = d3.axisBottom(xScale)
  .ticks(5)  // 对数刻度下无效！
  .tickFormat((d: any) => {{
    if (d >= 1000000) return "$" + (d / 1000000) + "M";
    if (d >= 1000) return "$" + (d / 1000) + "K";
    return d.toString();
  }});

// ✅ 正确：使用 .tickValues() 手动指定刻度值
// 根据数据范围选择合适的刻度值（通常选择 1, 2, 5, 10 的倍数）
const xAxis = d3.axisBottom(xScale)
  .tickValues([1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, 50000000])
  .tickFormat((d: any) => {{
    if (d >= 1000000) return "$" + (d / 1000000) + "M";
    if (d >= 1000) return "$" + (d / 1000) + "K";
    return d.toString();
  }});

// 网格线也必须使用相同的 tickValues
g.append('g')
  .attr('class', 'grid-x')
  .attr('transform', 'translate(0, 400)')
  .call(d3.axisBottom(xScale)
    .tickValues([1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000, 50000000])
    .tickSize(-400)
    .tickFormat(() => "")
  );
```

**刻度值选择原则**：
- 根据数据的最小值和最大值范围选择
- 通常选择每个数量级的 1、2、5、10 倍（例如：1K, 2K, 5K, 10K, 20K, 50K, 100K...）
- 刻度数量控制在 6-10 个之间，避免过多
- 确保刻度值覆盖整个数据范围

**何时使用对数刻度**：
- 数据范围跨越多个数量级（例如：1K 到 50M）
- 数据分布呈指数增长
- 需要更好地展示小值和大值的关系

## Component Template
```typescript
import React, {{useEffect, useRef, useMemo}} from 'react';
import {{ AbsoluteFill }} from 'remotion';
import * as d3 from 'd3';

export const {component_name}: React.FC = () => {{
  const svgRef = useRef<SVGSVGElement>(null);
  
  // Hardcoded data
  const data = {json.dumps(data, indent=2, ensure_ascii=False)};
  const xField = "{x_field_expr}";
  const yField = "{y_field_expr}";
  
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
  const maxValue = d3.max(data, (d: any) => d[yField]) || 0;
  const minValue = d3.min(data, (d: any) => d[yField]) || 0;
  const avgValue = d3.mean(data, (d: any) => d[yField]) || 0;
  const maxItem = data.find((d: any) => d[yField] === maxValue);
  
  // D3 scales (bar chart example)
  const scales = useMemo(() => {{
    const xScale = d3.scaleBand()
      .domain(data.map((d: any) => d[xField]))
      .range([0, 900])
      .padding(0.2);
    const yScale = d3.scaleLinear()
      .domain([0, maxValue * 1.1])
      .range([500, 0]);
    return {{ xScale, yScale }};
  }}, [data]);
  
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
    
    // Optional: Shadow filter (使用 feDropShadow 避免模糊！)
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
      .attr('height', (d: any) => 400 - yScale(d[yField]))
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
    // ⚠️ IMPORTANT: y: 390 or LESS to leave bottom 130px for subtitle (支持2-3行)!
    g.selectAll('.category-label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', (d: any) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
      .attr('y', 390)  // ✅ 390 safe zone (bottom 130px reserved for 2-3 line subtitle)
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
      {{/* Title with optional 0-1 icon */}}
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
✅ **0-1 ICONS** - Use emoji only if it reinforces the story (e.g., 💰 for revenue)
✅ **DATA FIRST** - Chart should be large and readable, numbers formatted clearly
✅ **SUBTITLE SPACE** - Keep top 80px relatively clear for subtitle overlay
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
- Use multiple decorative icons everywhere
- Copy "3 cards + chart" layout for every scene
- Over-decorate with gradients/shadows on everything
- Make subtitle area dense (keep top 80px breathable)
- **Remember: Data labels on chart elements are sufficient - highlight key data IN THE CHART with size/color/stroke, NOT with separate cards!**

## OUTPUT
Generate ONLY the complete TypeScript code - NO markdown blocks, NO explanations.
Start with imports, end with closing brace.
All D3 elements should be in FINAL visible state (full height, opacity 1).
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
        print(f"   正在提取场景信息...")
    
    # 提取场景信息（不做预判断）
    scene_info = extract_scene_info(scene_data)
    
    if verbose:
        print(f"   图表类型: {scene_info['chart_type']}")
        print(f"   Y轴: {scene_info['y_label']}")
        print(f"   数据量: {scene_info['data_count']} 条")
        print(f"   正在调用 Claude API（让 LLM 确定统一风格）...")
    
    # 构造 Prompt（传入唯一的组件名 + 场景索引信息）
    prompt = create_tsx_generation_prompt(scene_data, video_meta, scene_info, component_name, scene_index, total_scenes)
    
    try:
        # 调用 Claude API（使用大 token 数，确保不截断；提高temperature增加创造性）
        response = llm_client.call(prompt, temperature=0.85, max_tokens=8000)
        
        # 清理响应
        tsx_code = response.strip()
        if tsx_code.startswith("```typescript") or tsx_code.startswith("```tsx"):
            tsx_code = tsx_code.split('\n', 1)[1]  # Remove first line
        if tsx_code.startswith("```"):
            tsx_code = tsx_code[3:]
        if tsx_code.endswith("```"):
            tsx_code = tsx_code[:-3]
        tsx_code = tsx_code.strip()
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tsx_code)
        
        if verbose:
            print(f"   ✅ 生成成功: {os.path.basename(output_path)}")
            print(f"   文件大小: {len(tsx_code)} 字符")
        
        return True
    
    except Exception as e:
        if verbose:
            print(f"   ❌ 生成失败: {e}")
        return False


def generate_single_scene_wrapper(
    scene, 
    idx: int,
    total: int,
    video_meta, 
    llm_client, 
    output_dir: str
) -> Tuple[int, str, bool, str]:
    """
    包装函数，用于并行执行（返回结果用于汇总）
    """
    scene_id = scene.get('id', f'scene_{idx}')
    dataset_name = extract_dataset_name(video_meta)
    component_name = f"{dataset_name}_{''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())}"
    output_file = os.path.join(output_dir, f"{component_name}.tsx")
    chart_title = scene.get('content', {}).get('title', 'Visualization')
    
    try:
        success = generate_tsx_component(
            scene, 
            video_meta, 
            llm_client, 
            output_file, 
            verbose=False,  # 并行模式下先不打印详细信息
            scene_index=idx,
            total_scenes=total
        )
        if success:
            # 读取文件大小
            file_size = os.path.getsize(output_file)
            return (idx, scene_id, True, f"✅ {chart_title} ({file_size} 字节)")
        else:
            return (idx, scene_id, False, f"❌ {chart_title} - 生成失败")
    except Exception as e:
        return (idx, scene_id, False, f"❌ {chart_title} - {str(e)}")


def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='生成 TSX 信息图组件（默认并行模式）')
    parser.add_argument('--serial', action='store_true', help='使用串行模式（默认是并行）')
    parser.add_argument('-w', '--workers', type=int, default=4, help='并行线程数（默认4）')
    parser.add_argument('--config', type=str, 
                       default='infographic_generation/generated_20251216_045823_aligned_flight.json',
                       help='配置文件路径')
    parser.add_argument('--output', type=str,
                       default='infographic_generation/output/claude_tsx_components',
                       help='输出目录')
    args = parser.parse_args()
    
    # 默认并行，除非指定 --serial
    use_parallel = not args.serial
    
    # 读取配置文件
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    video_meta = config.get('meta', {})
    all_scenes = config.get('scenes', [])
    
    # 初始化 LLM 客户端
    mode_text = "并行模式" if use_parallel else "串行模式"
    workers_text = f"，{args.workers} 线程" if use_parallel else ""
    print(f"🚀 初始化 LLM 客户端 (Claude Sonnet 4，{mode_text}{workers_text})...")
    
    llm_client = LLMClient(
        api_base="https://newapi.deepwisdom.ai",
        api_key="sk-Rq3hmLp1zTqnvUMow4sninyeuGk8rlE2xnIihASNWkeEfiPv",
        model="claude-sonnet-4-20250514"
    )
    
    # 提取图表场景
    chart_scenes = [s for s in all_scenes if s['type'] == 'chart']
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
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
                    args.output
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
        # 串行模式
        print("📝 使用串行模式生成...\n")
        for idx, scene in enumerate(chart_scenes, 1):
            scene_id = scene.get('id', f'scene_{idx}')
            dataset_name = extract_dataset_name(video_meta)
            component_name = f"{dataset_name}_{''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())}"
            output_file = os.path.join(args.output, f"{component_name}.tsx")
            
            print(f"[{idx}/{len(chart_scenes)}]", end=" ")
            success = generate_tsx_component(
                scene, 
                video_meta, 
                llm_client, 
                output_file, 
                verbose=True,
                scene_index=idx,
                total_scenes=len(chart_scenes)
            )
            
            if success:
                success_count += 1
    
    # 总结
    print("\n" + "="*70)
    print(f"\n🎉 生成完成！")
    print(f"   成功: {success_count}/{len(chart_scenes)}")
    print(f"   输出目录: {args.output}")
    print(f"\n📺 如何查看生成的场景：")
    print(f"\n   方法 1: 直接在浏览器打开 HTML 预览（推荐）")
    print(f"   -----------------------------------------------")
    print(f"   生成的组件在: {args.output}/")
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
    print(f"\n📂 现在可以打开 {args.output} 目录查看生成的组件！")


if __name__ == "__main__":
    main()


