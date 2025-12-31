"""
方案2：LLM 二次加工 - 给静态组件添加动画
读取已生成的静态 TSX 组件，根据配置中的 animations，添加动画逻辑
支持批量处理和并行执行
"""

import json
import os
import sys
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

# 导入项目现有的 LLM 客户端
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config_generation'))
from generator import LLMClient


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


def create_animation_prompt(static_tsx_code, animations_config, narrations, scene_title, scene_time_range):
    """
    构造 Prompt：让 LLM 在静态组件基础上添加动画和字幕
    """
    scene_start_time = scene_time_range[0]
    
    # 读取参考动画代码（基于固定模板 barAnimations.ts 的逻辑）
    reference_animation = """
// 参考示例：基于固定模板的动画逻辑（ConfigDrivenChart/barAnimations.ts）

// useEffect 2: ANIMATION UPDATES
useEffect(() => {{
  if (!svgRef.current) return;
  const svg = d3.select(svgRef.current);
  const g = svg.select('g');
  if (g.empty()) return;

  const {{yScale}} = scales;
  const innerHeight = 400;  // 根据实际图表高度调整

  // 1. ENTRANCE ANIMATION - 检查是否已完成
  const entranceAnim = animations.find((a: any) => a.type === 'entrance');
  
  if (entranceAnim) {{
    const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
    const animEnd = animStart + entranceAnim.duration * fps;
    
      // ✅ CRITICAL: 动画结束后，强制所有元素到最终状态
      // 必须恢复所有可能的元素类型，避免遗漏导致元素消失
      if (frame >= animEnd) {{
        // Bar Chart 元素
        g.selectAll('.bar').each(function(d: any) {{
          const bar = d3.select(this);
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        }});
        g.selectAll('.value-label, .category-label').style('opacity', 1);
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
        
        // Scatter/Line Chart 额外元素（如果存在）
        g.selectAll('.dot, .circle').style('opacity', 0.8);
        g.selectAll('.city-label, .data-label').style('opacity', 1);
        g.selectAll('.grid-x, .grid-y').style('opacity', 0.3);
        g.selectAll('.line, .path').style('opacity', 1);
        
        // Pie Chart 元素（如果存在pieG）
        svg.selectAll('.arc').style('opacity', 1).style('transform', 'scale(1)');
        svg.selectAll('.percentage-label').style('opacity', 1);
        svg.selectAll('.legend-rect, .legend-destination, .legend-percentage').style('opacity', 1);
        
        // 继续执行 emphasis 动画（不 return）
    }} else if (frame >= animStart) {{
      // 入场动画进行中
      const totalTime = (frame - animStart) / fps;  // 当前经过的秒数

      // 柱子逐个生长
      g.selectAll<SVGRectElement, any>('.bar').each(function(d: any, i: number) {{
        const bar = d3.select(this);
        const delayPerBar = 0.12;  // 每个柱子延迟 0.12 秒（固定值）
        const animDuration = 0.6;   // 单个柱子动画时长 0.6 秒
        const barStart = i * delayPerBar;
        const barEnd = barStart + animDuration;

        if (totalTime >= barStart && totalTime <= barEnd) {{
          // 柱子动画进行中
          const barProgress = (totalTime - barStart) / animDuration;
          const eased = d3.easeCubicOut(barProgress);
          const targetHeight = innerHeight - yScale(d[yField]);
          const currentHeight = targetHeight * eased;

          bar
            .attr('height', Math.max(0, currentHeight))
            .attr('y', innerHeight - Math.max(0, currentHeight))
            .style('opacity', eased);
        }} else if (totalTime > barEnd) {{
          // 柱子动画完成
          const targetHeight = innerHeight - yScale(d[yField]);
          bar
            .attr('height', targetHeight)
            .attr('y', innerHeight - targetHeight)
            .style('opacity', 1);
        }}
      }});

      // 标签延迟淡入（category + value 同时）
      g.selectAll<SVGTextElement, any>('.value-label, .category-label').each(function(d: any, i: number) {{
        const label = d3.select(this);
        const delayPerBar = 0.12;
        const labelDelay = 0.3;  // 额外延迟 0.3 秒（固定值）
        const animDuration = 0.4;
        const labelStart = i * delayPerBar + labelDelay;
        const labelEnd = labelStart + animDuration;

        if (totalTime >= labelStart && totalTime <= labelEnd) {{
          const labelProgress = (totalTime - labelStart) / animDuration;
          const eased = d3.easeCubicOut(labelProgress);
          label.style('opacity', eased);
        }} else if (totalTime > labelEnd) {{
          label.style('opacity', 1);
        }}
      }});
      
      // 轴标签淡入
      const axisStart = 0.3;
      const axisDuration = 0.4;
      if (totalTime >= axisStart && totalTime <= axisStart + axisDuration) {{
        const axisProgress = (totalTime - axisStart) / axisDuration;
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', axisProgress);
      }} else if (totalTime > axisStart + axisDuration) {{
        g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
      }}
    }}
  }}

  // 2. EMPHASIS ANIMATION - 高亮特定数据
  // ✅ CRITICAL: 必须正确处理多个同时激活的 emphasis 动画
  // 问题：如果多个 emphasis 动画时间重叠（例如同时提到 "Minneapolis and Dallas"），
  // 逐个遍历会导致后面的动画覆盖前面的效果，只能看到最后一个高亮。
  // 解决方案：先收集所有激活的动画，然后一次性处理所有需要高亮的数据项。
  const emphasisAnims = animations.filter((a: any) => a.type === 'emphasis') || [];
  let hasActiveEmphasis = false;
  
  // 先收集所有当前激活的 emphasis 动画
  const activeEmphasisAnims = emphasisAnims.filter((anim: any) => {{
    const animStart = (anim.time_start - sceneStartOffset) * fps;
    const animDuration = anim.duration * fps;
    return frame >= animStart && frame < animStart + animDuration;
  }});
  
  if (activeEmphasisAnims.length > 0) {{
    hasActiveEmphasis = true;
    
    // 计算所有激活动画的平均 pulse（用于同步效果）
    let maxPulse = 1;
    activeEmphasisAnims.forEach((anim: any) => {{
      const animStart = (anim.time_start - sceneStartOffset) * fps;
      const animDuration = anim.duration * fps;
      const progress = (frame - animStart) / animDuration;
      const pulse = Math.sin(progress * Math.PI * 6) * 0.05 + 1;
      maxPulse = Math.max(maxPulse, pulse);
    }});

    // 收集所有需要高亮的数据项（使用 Set 避免重复）
    const highlightedItems = new Set<string>();
    activeEmphasisAnims.forEach((anim: any) => {{
      const filter = anim.target_data?.data_filter;
      if (filter) {{
        // 找到匹配的数据项
        data.forEach((d: any) => {{
          const matches = Object.keys(filter).every(
            (key) => d[key] === filter[key]
          );
          if (matches) {{
            highlightedItems.add(d[xField]);  // 使用 xField（如 "city"）作为唯一标识
          }}
        }});
      }}
    }});

    // 一次性处理所有柱子/数据点（避免循环覆盖）
    g.selectAll<SVGRectElement, any>('.bar').each(function(d: any) {{
      const bar = d3.select(this);
      const isHighlighted = highlightedItems.has(d[xField]);

      if (isHighlighted) {{
        bar
          .style('opacity', 1)
          .attr('stroke', '#ff6b6b')
          .attr('stroke-width', 4 * maxPulse)
          .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
      }} else {{
        bar.style('opacity', 0.3).attr('stroke', 'none').style('filter', 'none');
      }}
    }});
    
    // 对于散点图，同样处理 .dot 或 .circle
    g.selectAll<SVGCircleElement, any>('.dot, .circle').each(function(d: any) {{
      const dot = d3.select(this);
      const isHighlighted = highlightedItems.has(d[xField]);

      if (isHighlighted) {{
        dot
          .style('opacity', 1)
          .attr('stroke', '#ff6b6b')
          .attr('stroke-width', 4 * maxPulse)
          .style('filter', 'drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))');
      }} else {{
        dot.style('opacity', 0.3).attr('stroke', (d: any) => d[yField] === maxValue ? '#1d4ed8' : '#475569');
      }}
    }});
  }}

  // 3. 恢复正常状态（仅在没有 emphasis 时）
  // ✅ CRITICAL: 确保恢复所有元素，避免遗漏导致元素消失
  if (!hasActiveEmphasis && entranceAnim && frame >= (entranceAnim.time_start - sceneStartOffset + entranceAnim.duration) * fps) {{
    // Bar Chart 元素
    g.selectAll('.bar').attr('stroke', 'none').style('opacity', 1);
    g.selectAll('.value-label, .category-label').style('opacity', 1);
    
    // Scatter Chart 元素
    g.selectAll('.dot, .circle').attr('stroke', 'none').style('opacity', 0.8);
    g.selectAll('.city-label, .data-label').style('opacity', 1);
    g.selectAll('.grid-x, .grid-y').style('opacity', 0.3);
    
    // Pie Chart 元素（如果有pieG）
    const pieG = svg.selectAll('g').filter(function() {{
      const transform = d3.select(this).attr('transform');
      return transform && transform.includes('translate') && transform.includes('280');
    }});
    if (!pieG.empty()) {{
      pieG.selectAll('.arc').style('opacity', 1).style('transform', 'scale(1)');
      pieG.selectAll('.percentage-label').style('opacity', 1);
    }}
    
    // 通用元素（所有图表类型）
    g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
    svg.selectAll('.legend-rect, .legend-destination, .legend-percentage').style('opacity', 1);
  }}

}}, [frame, fps, scales, animations, data, xField, yField, sceneStartOffset]);
"""
    
    prompt = f"""
你是一个 **React + D3.js + Remotion 动画专家**。

# 任务
我有一个静态的 D3 信息图组件（已经渲染得很好），现在需要你**只添加动画逻辑**，不要修改静态渲染部分。

# 场景信息
- 标题: "{scene_title}"
- 动画配置:
{json.dumps(animations_config, indent=2)}

- 字幕配置:
{json.dumps(narrations, indent=2)}

# 现有的静态组件代码
```typescript
{static_tsx_code}
```

# 参考动画示例（FlightDataInfographicV2.tsx）
{reference_animation}

---

# 你的任务（非常重要！）

## ✅ 要做的事情：
1. **添加必要的 imports**：
   - 如果缺少，添加：`import {{useCurrentFrame, useVideoConfig}} from 'remotion';`
   
2. **在组件内部添加这些 hooks 和时间偏移变量**：
   ```typescript
   const frame = useCurrentFrame();
   const {{fps}} = useVideoConfig();
   
   // 场景时间偏移（用于独立预览）
   const sceneStartOffset = {scene_start_time};  // 原视频中场景的开始时间
   ```
   
   **重要**：配置中的所有时间（`time_start`, `time_end`）都是基于视频的绝对时间。
   由于这个组件是独立预览的，需要将所有时间减去 `sceneStartOffset` 才能从第0帧开始播放。

3. **添加第二个 useEffect** 来处理动画（在现有 useEffect 之后）：
   - 根据配置中的 `animations` 数组实现动画
   - **entrance 动画**：柱子从底部生长，标签淡入
     - **CRITICAL**: 入场动画结束后（frame >= animEnd），必须强制恢复所有元素到最终状态
     - **必须恢复的元素（根据图表类型）：**
       - Bar Chart: `.bar`, `.value-label`, `.category-label`, `.x-axis-label`, `.y-axis-label`
       - Scatter Chart: `.dot`, `.city-label`, `.data-label`, `.grid-x`, `.grid-y`, `.x-axis-label`, `.y-axis-label`
       - Line Chart: `.line`, `.dot`, `.grid-x`, `.grid-y`, `.x-axis-label`, `.y-axis-label`
       - Pie Chart: `.arc`, `.percentage-label`, `.legend-rect`, `.legend-destination`, `.legend-percentage`
     - **⚠️ 常见错误**：
       1. 只恢复主要元素（如柱子、点），忘记恢复网格线、坐标轴等辅助元素
       2. 使用宽泛的选择器（如 `g.selectAll('g text')`）会选中所有text，可能与其他元素冲突
       3. **【重要】混用 `.style('opacity', ...)` 和 `.attr('opacity', ...)`** - 这会导致元素不可见！
          - CSS样式（.style）的优先级高于SVG属性（.attr）
          - 如果静态渲染用 `.style('opacity', 0)` 隐藏元素，动画就必须用 `.style('opacity', ...)` 显示
          - 如果混用，CSS的 `opacity: 0` 会一直覆盖 `.attr('opacity', ...)` 的设置
     - **✅ 正确做法**：
       1. 使用精确的class选择器（如 `.city-label`, `.grid-x`）而不是标签选择器（如 `text`, `line`）
       2. **统一使用 `.style('opacity', ...)` 控制透明度**，与静态渲染保持一致
   - **emphasis 动画**：高亮匹配的数据点，降低其他元素透明度
   - 使用 `frame` 和 `fps` 计算动画进度
   - 参考上面的示例代码实现逻辑

4. **添加字幕显示逻辑**：
   - 在 JSX 的 `<AbsoluteFill>` 内部底部添加字幕区域
   - 根据当前时间（`frame / fps`）显示对应的字幕
   - **CRITICAL**: 字幕在底部 35-130px 区域（静态图已预留 130px 空间，支持2-3行长字幕）
   - 字幕样式参考（优化后支持更长字幕）：
   ```jsx
   {{getCurrentNarration() && (
     <div style={{{{
       position: 'absolute',
       bottom: 35,  // 底部 35px（在预留的 130px 空间内，支持2-3行）
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
     }}}}>
       {{getCurrentNarration().text}}
     </div>
   )}}
   ```
   - 创建辅助函数 `getCurrentNarration()` 返回当前时间对应的字幕对象：
   ```typescript
   const getCurrentNarration = () => {{
     const currentTime = frame / fps;
     return narrations.find(narr => 
       currentTime >= (narr.time_start - sceneStartOffset) && 
       currentTime <= (narr.time_end - sceneStartOffset)
     );
   }};
   ```
   **注意**：字幕时间也要减去 `sceneStartOffset`

4. **修改初始状态**（在第一个 useEffect 里）：
   - 柱子初始 `height: 0`，`y: innerHeight`，`opacity: 0`
   - 标签初始 `opacity: 0`
   - 这样动画才能从0开始生长

5. **保持代码结构清晰**：
   - 添加注释说明每个动画阶段
   - 使用 d3 缓动函数（如 `d3.easeElasticOut`）

## ❌ 不要做的事情：
- ❌ 不要删除或大幅修改现有的 useEffect（静态渲染）
- ❌ 不要改变 scales、data、margin 等核心变量
- ❌ 不要修改 JSX 布局结构
- ❌ 不要添加不必要的复杂逻辑

## 🎯 动画配置解读
{f"- entrance: 从 {animations_config[0]['time_start']}s 开始，持续 {animations_config[0]['duration']}s" if animations_config and animations_config[0].get('type') == 'entrance' else ""}
{f"- emphasis: 高亮 {animations_config[1].get('target_data', {}).get('data_filter', {})} 的数据点" if len(animations_config) > 1 and animations_config[1].get('type') == 'emphasis' else ""}

## ⚡ 动画优化要求（非常重要！）

### 1. **Entrance 动画时间控制（CRITICAL！使用绝对时间，不是相对进度！）**

**核心原则：**
- ✅ 使用 **绝对时间（秒）** 而不是相对进度比例
- ✅ 固定的延迟时间（0.12秒/柱、0.3秒标签延迟、0.6秒柱子动画、0.4秒标签动画）
- ✅ 入场动画结束后，立即强制恢复所有元素到最终状态

**实现方式：**
```javascript
const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
const animEnd = animStart + entranceAnim.duration * fps;

// ✅ 第一步：检查动画是否已结束
if (frame >= animEnd) {{
  // 入场动画已完成，强制所有元素到最终状态
  g.selectAll('.bar').each(function(d: any) {{
    const bar = d3.select(this);
    const targetHeight = innerHeight - yScale(d[yField]);
    bar.attr('height', targetHeight).attr('y', innerHeight - targetHeight).style('opacity', 1);
  }});
  g.selectAll('.value-label, .category-label').style('opacity', 1);
  g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
  
  // 继续执行 emphasis 动画（不 return）
}} else if (frame >= animStart) {{
  // 第二步：入场动画进行中，使用绝对时间
  const totalTime = (frame - animStart) / fps;  // 当前经过的秒数

  // 柱子动画
  g.selectAll('.bar').each(function(d: any, i: number) {{
    const delayPerBar = 0.12;  // 固定延迟 0.12 秒
    const animDuration = 0.6;  // 固定时长 0.6 秒
    const barStart = i * delayPerBar;
    const barEnd = barStart + animDuration;

    if (totalTime >= barStart && totalTime <= barEnd) {{
      const barProgress = (totalTime - barStart) / animDuration;
      const eased = d3.easeCubicOut(barProgress);
      // ... 设置高度和 opacity
    }} else if (totalTime > barEnd) {{
      // 柱子动画完成，设置到最终状态
    }}
  }});

  // 标签动画（category + value 同时）
  g.selectAll('.value-label, .category-label').each(function(d: any, i: number) {{
    const delayPerBar = 0.12;
    const labelDelay = 0.3;  // 固定延迟 0.3 秒
    const animDuration = 0.4; // 固定时长 0.4 秒
    const labelStart = i * delayPerBar + labelDelay;
    const labelEnd = labelStart + animDuration;

    if (totalTime >= labelStart && totalTime <= labelEnd) {{
      const labelProgress = (totalTime - labelStart) / animDuration;
      label.style('opacity', d3.easeCubicOut(labelProgress));
    }} else if (totalTime > labelEnd) {{
      label.style('opacity', 1);
    }}
  }});
}}
```

**时间参数（固定值，不要改）：**
- 柱子延迟：`0.12 秒/个`
- 柱子动画时长：`0.6 秒`
- 标签额外延迟：`0.3 秒`
- 标签淡入时长：`0.4 秒`
- 轴标签延迟：`0.3 秒`，淡入时长：`0.4 秒`

### 2. **Emphasis 动画（CRITICAL - 必须正确处理多个同时激活的动画）**：
- ⚠️ **重要问题**：当多个 emphasis 动画时间重叠时（例如同时提到 "Minneapolis and Dallas"），
  如果逐个遍历动画，后面的动画会覆盖前面的效果，导致只能看到最后一个高亮。
- ✅ **正确做法**：
  1. **先收集所有当前激活的 emphasis 动画**（检查 `frame >= animStart && frame < animStart + animDuration`）
  2. **收集所有需要高亮的数据项**（使用 `Set<string>` 存储匹配的数据项标识，如 `d[xField]`）
  3. **一次性处理所有数据点**（遍历所有柱子/点，检查是否在 highlightedItems 中，避免循环覆盖）
- 高亮的柱子使用红色边框（`stroke: '#ff6b6b'`, `stroke-width: 3-5px`）
- 添加发光效果：`drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))`
- 脉冲效果不要太夸张，缩放范围 `Math.sin(...) * 0.05 + 1`（1.0-1.05x）
- 非高亮柱子透明度降至 `0.3`
- 对于散点图，同样处理 `.dot` 或 `.circle` 元素
   
### 3. **选择器规范（CRITICAL！避免元素冲突）**：
- ✅ **使用精确的 class 选择器**：`.bar`, `.dot`, `.city-label`, `.grid-x`, `.grid-y`, etc.
- ❌ **避免宽泛的标签选择器**：`text`, `line`, `circle`, `g text` - 这些会选中所有同类元素，导致冲突
- ❌ **错误示例**：`g.selectAll('g text')` - 会选中所有在g内的text，包括标签、坐标轴刻度等
- ✅ **正确示例**：`g.selectAll('.city-label')` - 只选中特定class的元素

### 4. **过渡平滑**：
- 使用 `d3.easeCubicOut` 或 `d3.easeQuadOut`，避免突变
- emphasis 开始/结束时要平滑过渡
   
### 5. **信息卡片动画**（如果有info cards）：
- 卡片也应该有淡入动画
- 延迟 0.4-0.5 相对进度

# 输出格式
输出完整的 TypeScript 代码（包含动画）：
- 不要用 markdown 代码块（```）
- 不要添加解释说明
- 直接输出完整的可运行代码
- 组件名改为：`export const SceneComponentAnimated`

现在开始生成带动画的组件：
"""
    return prompt


def add_animations_with_llm(static_tsx_path, animations_config, narrations, scene_title, scene_time_range, llm_client, output_path, verbose=True):
    """
    使用 LLM 给静态组件添加动画和字幕
    """
    if verbose:
        print(f"\n🎬 正在为场景添加动画和字幕...")
        print(f"   标题: {scene_title}")
        print(f"   场景时间: {scene_time_range[0]}s - {scene_time_range[1]}s")
        print(f"   动画数量: {len(animations_config)}")
        print(f"   字幕数量: {len(narrations)}")
    
    # 读取静态组件代码
    with open(static_tsx_path, 'r', encoding='utf-8') as f:
        static_code = f.read()
    
    if verbose:
        print(f"   静态组件大小: {len(static_code)} 字符")
        print(f"   正在调用 Claude API...")
    
    # 构造 Prompt
    prompt = create_animation_prompt(static_code, animations_config, narrations, scene_title, scene_time_range)
    
    try:
        # 调用 LLM
        response = llm_client.call(prompt, temperature=0.7, max_tokens=12000)
        
        # 清理响应
        animated_code = response.strip()
        if animated_code.startswith("```typescript") or animated_code.startswith("```tsx"):
            animated_code = animated_code.split('\n', 1)[1]
        if animated_code.startswith("```"):
            animated_code = animated_code[3:]
        if animated_code.endswith("```"):
            animated_code = animated_code[:-3]
        animated_code = animated_code.strip()
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(animated_code)
        
        if verbose:
            print(f"   ✅ 生成成功: {os.path.basename(output_path)}")
            print(f"   文件大小: {len(animated_code)} 字符 (增加了 {len(animated_code) - len(static_code)} 字符)")
        
        return True
    
    except Exception as e:
        if verbose:
            print(f"   ❌ 生成失败: {e}")
        return False


def process_single_scene_wrapper(
    scene,
    idx: int,
    total: int,
    llm_client,
    static_input_dir: str,
    output_dir: str
) -> Tuple[int, str, bool, str]:
    """
    包装函数，用于并行执行
    """
    scene_id = scene.get('id', f'scene_{idx}')
    scene_title = scene.get('content', {}).get('title', 'Unknown')
    dataset_name = extract_dataset_name(video_meta)
    component_name = f"{dataset_name}_{''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())}"
    
    # 输入文件路径
    static_tsx_path = os.path.join(static_input_dir, f"{component_name}.tsx")
    if not os.path.exists(static_tsx_path):
        return (idx, scene_id, False, f"❌ {scene_title} - 静态文件不存在: {component_name}.tsx")
    
    # 输出文件路径
    output_path = os.path.join(output_dir, f"{component_name}Animated.tsx")
    
    animations_config = scene.get('animations', [])
    narrations = scene.get('narration', [])
    scene_time_range = scene.get('time_range', [0, 10])
    
    try:
        success = add_animations_with_llm(
            static_tsx_path,
            animations_config,
            narrations,
            scene_title,
            scene_time_range,
            llm_client,
            output_path,
            verbose=False
        )
        
        if success:
            file_size = os.path.getsize(output_path)
            return (idx, scene_id, True, f"✅ {scene_title} ({file_size} 字节)")
        else:
            return (idx, scene_id, False, f"❌ {scene_title} - 生成失败")
    except Exception as e:
        return (idx, scene_id, False, f"❌ {scene_title} - {str(e)}")


if __name__ == "__main__":
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='给静态 TSX 组件添加动画（支持批量和并行）')
    parser.add_argument('--serial', action='store_true', help='使用串行模式（默认是并行）')
    parser.add_argument('-w', '--workers', type=int, default=5, help='并行线程数（默认5）')
    parser.add_argument('--config', type=str, 
                       default='infographic_generation/generated_20251216_045823_aligned_flight.json',
                       help='配置文件路径')
    parser.add_argument('--input', type=str,
                       default='infographic_generation/output/claude_tsx_components',
                       help='静态组件输入目录')
    parser.add_argument('--output', type=str,
                       default='infographic_generation/output/claude_tsx_animated',
                       help='动画组件输出目录')
    args = parser.parse_args()
    
    # 默认并行，除非指定 --serial
    use_parallel = not args.serial
    
    # 读取配置文件
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    video_meta = config.get('meta', {})
    all_scenes = config.get('scenes', [])
    chart_scenes = [s for s in all_scenes if s['type'] == 'chart']
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 初始化 LLM 客户端
    mode_text = "并行模式" if use_parallel else "串行模式"
    workers_text = f"，{args.workers} 线程" if use_parallel else ""
    print(f"🚀 初始化 LLM 客户端 (Claude Sonnet 4，{mode_text}{workers_text})...")
    
    llm_client = LLMClient(
        api_base="https://newapi.deepwisdom.ai",
        api_key="sk-Rq3hmLp1zTqnvUMow4sninyeuGk8rlE2xnIihASNWkeEfiPv",
        model="claude-sonnet-4-20250514"
    )
    
    print(f"\n📊 视频标题: {video_meta.get('title', 'N/A')}")
    print(f"📊 共找到 {len(chart_scenes)} 个图表场景")
    print("="*70)
    
    # 开始计时
    start_time = time.time()
    
    success_count = 0
    results = []
    
    if use_parallel:
        # 并行模式
        print(f"⚡ 使用并行模式生成（{args.workers} 个线程）...\n")
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    process_single_scene_wrapper,
                    scene, idx, len(chart_scenes),
                    llm_client, args.input, args.output
                ): idx for idx, scene in enumerate(chart_scenes, 1)
            }
            
            for future in as_completed(futures):
                idx, scene_id, success, message = future.result()
                results.append((idx, scene_id, success, message))
                print(f"[{idx}/{len(chart_scenes)}] {message}")
                if success:
                    success_count += 1
        
        # 按场景顺序排序
        results.sort(key=lambda x: x[0])
    else:
        # 串行模式
        print("📝 使用串行模式生成...\n")
        for idx, scene in enumerate(chart_scenes, 1):
            scene_id = scene.get('id', f'scene_{idx}')
            scene_title = scene.get('content', {}).get('title', 'Unknown')
            dataset_name = extract_dataset_name(video_meta)
            component_name = f"{dataset_name}_{''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())}"
            
            static_tsx_path = os.path.join(args.input, f"{component_name}.tsx")
            if not os.path.exists(static_tsx_path):
                print(f"[{idx}/{len(chart_scenes)}] ❌ {scene_title} - 静态文件不存在")
                continue
            
            output_path = os.path.join(args.output, f"{component_name}Animated.tsx")
            
            animations_config = scene.get('animations', [])
            narrations = scene.get('narration', [])
            scene_time_range = scene.get('time_range', [0, 10])
            
            print(f"[{idx}/{len(chart_scenes)}]")
            print(f"   📊 {scene_title}")
            print(f"   🎬 {len(animations_config)} 个动画, 💬 {len(narrations)} 条字幕")
            
            success = add_animations_with_llm(
                static_tsx_path,
                animations_config,
                narrations,
                scene_title,
                scene_time_range,
                llm_client,
                output_path,
                verbose=True
            )
            
            if success:
                success_count += 1
    
    # 计算总耗时
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / len(chart_scenes) if chart_scenes else 0
    
    # 总结
    print("\n" + "="*70)
    print(f"\n🎉 动画添加完成！")
    print(f"   成功: {success_count}/{len(chart_scenes)}")
    print(f"   输出目录: {args.output}")
    print(f"\n⏱️  耗时统计：")
    print(f"   总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    print(f"   平均每个场景: {avg_time:.1f} 秒")
    if use_parallel:
        print(f"   并行线程数: {args.workers}")
    print(f"\n💡 下一步：")
    print(f"   1. 检查生成的动画组件")
    print(f"   2. 运行自动注册脚本更新 Root.tsx")
    print(f"   3. 在 Remotion Studio 预览动画效果")

