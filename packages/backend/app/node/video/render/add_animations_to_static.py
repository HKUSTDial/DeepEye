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
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple, Optional

# 导入项目配置和 LLM 客户端
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.config import settings
from app.node.video.config.generator import LLMClient
from app.node.video.render.tsx_sanitize import sanitize_tsx_for_browser, validate_component_syntax

# ---------------------------------------------------------------------------
# Retry helpers (align with DataMagic core)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Timeline fallback (when config has no aligned timestamps)
# ---------------------------------------------------------------------------
DEFAULT_NARRATION_DURATION = 3.0
DEFAULT_MIN_SCENE_DURATION = 5.0
DEFAULT_ANIMATION_OFFSET = 0.0
DEFAULT_ANIMATION_PADDING = 0.2


def _ensure_scene_timing_fields(scene, scene_start_time: float) -> float:
    """
    Ensure scene has:
    - narration[*].time_start/time_end (absolute seconds)
    - scene.time_range (absolute seconds)
    - animations[*].time_start/duration when trigger_narration is present

    Returns: scene duration (seconds)
    """
    narrations = scene.get("narration", []) or []

    # 1) Narration time stamps
    scene_time = 0.0
    for narr in narrations:
        if not isinstance(narr, dict):
            continue
        if "time_start" not in narr or "time_end" not in narr:
            narr_start = scene_start_time + scene_time
            narr_end = narr_start + DEFAULT_NARRATION_DURATION
            narr["time_start"] = round(narr_start, 3)
            narr["time_end"] = round(narr_end, 3)
            scene_time += DEFAULT_NARRATION_DURATION
        else:
            try:
                scene_time = max(scene_time, float(narr["time_end"]) - scene_start_time)
            except Exception:
                scene_time += DEFAULT_NARRATION_DURATION

    if scene_time < DEFAULT_MIN_SCENE_DURATION:
        scene_time = DEFAULT_MIN_SCENE_DURATION

    # 2) Scene time range
    if "time_range" not in scene or not isinstance(scene.get("time_range"), list) or len(scene["time_range"]) < 2:
        scene["time_range"] = [round(scene_start_time, 3), round(scene_start_time + scene_time, 3)]

    # 3) Animation time stamps (absolute)
    animations = scene.get("animations", []) or []
    for anim in animations:
        if not isinstance(anim, dict):
            continue
        if "time_start" in anim and "duration" in anim:
            continue

        trigger_idx = anim.get("trigger_narration", None)
        if isinstance(trigger_idx, int) and 0 <= trigger_idx < len(narrations):
            narr = narrations[trigger_idx]
            try:
                t0 = float(narr.get("time_start", scene_start_time))
                t1 = float(narr.get("time_end", t0 + DEFAULT_NARRATION_DURATION))
            except Exception:
                t0 = scene_start_time
                t1 = t0 + DEFAULT_NARRATION_DURATION

            anim["time_start"] = round(t0 + DEFAULT_ANIMATION_OFFSET, 3)
            anim["duration"] = round((t1 - t0) + DEFAULT_ANIMATION_PADDING, 3)
            continue

        # Fallbacks:
        # - entrance: start at scene start
        # - others: start at scene start as well
        anim["time_start"] = round(scene_start_time, 3)
        anim["duration"] = round(DEFAULT_MIN_SCENE_DURATION, 3)

    return scene_time


def ensure_config_has_timeline(config: dict) -> dict:
    """
    Ensure whole config has a reasonable absolute timeline even if audio/TTS alignment failed.
    """
    scenes = config.get("scenes", []) or []
    current_time = 0.0
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_duration = _ensure_scene_timing_fields(scene, current_time)
        current_time += float(scene_duration)

    meta = config.setdefault("meta", {})
    if "video_duration" not in meta:
        meta["video_duration"] = round(current_time, 2)
    return config

# 从环境变量或 settings 获取配置
API_BASE = settings.LLM_BASE_URL or os.getenv("LLM_BASE_URL")
API_KEY = settings.LLM_API_KEY or os.getenv("LLM_API_KEY")
DEFAULT_MODEL = settings.LLM_MODEL or os.getenv("LLM_MODEL")
VIDEO_RUNTIME_BASE = os.getenv("VIDEO_RUNTIME_BASE", "/workspace/video_runtime")
DEFAULT_COMPONENTS_INPUT_DIR = os.getenv(
    "VIDEO_COMPONENTS_OUTPUT_BASE",
    os.path.join(VIDEO_RUNTIME_BASE, "claude_tsx_components"),
)
DEFAULT_ANIMATED_OUTPUT_DIR = os.getenv(
    "VIDEO_ANIMATED_OUTPUT_BASE",
    os.path.join(VIDEO_RUNTIME_BASE, "claude_tsx_animated"),
)

if not API_BASE:
    raise ValueError("LLM_BASE_URL is required. Please set it in .env file or environment variable.")
if not API_KEY:
    raise ValueError("LLM_API_KEY is required. Please set it in .env file or environment variable.")
if not DEFAULT_MODEL:
    raise ValueError("LLM_MODEL is required. Please set it in .env file or environment variable.")


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
You are a **React + D3.js + Remotion animation expert**.

# Task
I have a static D3 infographic component (already well-rendered), and I need you to **only add animation logic**, without modifying the static rendering part.

# Scene Information
- Title: "{scene_title}"
- Animation Configuration:
{json.dumps(animations_config, indent=2)}

- Subtitle Configuration:
{json.dumps(narrations, indent=2)}

# Existing Static Component Code
```typescript
{static_tsx_code}
```

# Reference Animation Example (FlightDataInfographicV2.tsx)
{reference_animation}

---

# Your Task (Very Important!)

## ✅ Things to Do:
1. **Add necessary imports**:
   - If missing, add: `import {{useCurrentFrame, useVideoConfig}} from 'remotion';`
   
2. **Add these hooks and time offset variable inside the component**:
   ```typescript
   const frame = useCurrentFrame();
   const {{fps}} = useVideoConfig();
   
   // Scene time offset (for independent preview)
   const sceneStartOffset = {scene_start_time};  // Start time of the scene in the original video
   ```
   
   **Important**: All times in the configuration (`time_start`, `time_end`) are based on absolute video time.
   Since this component is for independent preview, you need to subtract `sceneStartOffset` from all times to start playback from frame 0.

3. **Add a second useEffect** to handle animations (after the existing useEffect):
   - Implement animations based on the `animations` array in the configuration
   - **entrance animation**: Bars grow from bottom, labels fade in
     - **CRITICAL**: After the entrance animation ends (frame >= animEnd), you must force all elements to their final state
     - **Elements that must be restored (by chart type):**
       - Bar Chart: `.bar`, `.value-label`, `.category-label`, `.x-axis-label`, `.y-axis-label`
       - Scatter Chart: `.dot`, `.city-label`, `.data-label`, `.grid-x`, `.grid-y`, `.x-axis-label`, `.y-axis-label`
       - Line Chart: `.line`, `.dot`, `.grid-x`, `.grid-y`, `.x-axis-label`, `.y-axis-label`
       - Pie Chart: `.arc`, `.percentage-label`, `.legend-rect`, `.legend-destination`, `.legend-percentage`
     - **⚠️ Common Mistakes**:
       1. Only restoring main elements (bars, dots) but forgetting auxiliary elements like grid lines and axes
       2. Using broad selectors (like `g.selectAll('g text')`) which selects all text, potentially conflicting with other elements
       3. **【Important】Mixing `.style('opacity', ...)` and `.attr('opacity', ...)`** - This will make elements invisible!
          - CSS styles (.style) have higher priority than SVG attributes (.attr)
          - If static rendering uses `.style('opacity', 0)` to hide elements, animations must use `.style('opacity', ...)` to show them
          - If mixed, CSS `opacity: 0` will always override `.attr('opacity', ...)` settings
     - **✅ Correct Approach**:
       1. Use precise class selectors (like `.city-label`, `.grid-x`) instead of tag selectors (like `text`, `line`)
       2. **Consistently use `.style('opacity', ...)` to control opacity**, matching static rendering
   - **emphasis animation**: Highlight matching data points, reduce opacity of other elements
   - Use `frame` and `fps` to calculate animation progress
   - Refer to the example code above to implement the logic

4. **Add subtitle display logic**:
   - Add subtitle area at the bottom inside JSX `<AbsoluteFill>`
   - Display corresponding subtitle based on current time (`frame / fps`)
   - **CRITICAL**: Subtitles are in the bottom 35-130px area (static chart has reserved 130px space, supporting 2-3 line subtitles)
   - Subtitle style reference (optimized to support longer subtitles):
   ```jsx
   {{getCurrentNarration() && (
     <div style={{{{
       position: 'absolute',
       bottom: 35,  // Bottom 35px (within the reserved 130px space, supporting 2-3 lines)
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
   - Create helper function `getCurrentNarration()` that returns the subtitle object for current time:
   ```typescript
   const getCurrentNarration = () => {{
     const currentTime = frame / fps;
     return narrations.find(narr => 
       currentTime >= (narr.time_start - sceneStartOffset) && 
       currentTime <= (narr.time_end - sceneStartOffset)
     );
   }};
   ```
   **Note**: Subtitle times must also subtract `sceneStartOffset`

5. **Modify initial state** (in the first useEffect):
   - Bars initial `height: 0`, `y: innerHeight`, `opacity: 0`
   - Labels initial `opacity: 0`
   - This allows animations to grow from 0

6. **Keep code structure clear**:
   - Add comments explaining each animation stage
   - Use d3 easing functions (like `d3.easeElasticOut`)

## ❌ Things NOT to Do:
- ❌ Do not delete or significantly modify existing useEffect (static rendering)
- ❌ Do not change core variables like scales, data, margin
- ❌ Do not modify JSX layout structure
- ❌ Do not add unnecessary complex logic

## 🎯 Animation Configuration Interpretation
{f"- entrance: starts at {animations_config[0]['time_start']}s, duration {animations_config[0]['duration']}s" if animations_config and animations_config[0].get('type') == 'entrance' else ""}
{f"- emphasis: highlight data points matching {animations_config[1].get('target_data', {}).get('data_filter', {})}" if len(animations_config) > 1 and animations_config[1].get('type') == 'emphasis' else ""}

## ⚡ Animation Optimization Requirements (Very Important!)

### 1. **Entrance Animation Time Control (CRITICAL! Use absolute time, not relative progress!)**

**Core Principles:**
- ✅ Use **absolute time (seconds)** instead of relative progress ratio
- ✅ Fixed delay times (0.12s per bar, 0.3s label delay, 0.6s bar animation, 0.4s label animation)
- ✅ After entrance animation ends, immediately force all elements to final state

**Implementation:**
```javascript
const animStart = (entranceAnim.time_start - sceneStartOffset) * fps;
const animEnd = animStart + entranceAnim.duration * fps;

// ✅ Step 1: Check if animation has ended
if (frame >= animEnd) {{
  // Entrance animation completed, force all elements to final state
  g.selectAll('.bar').each(function(d: any) {{
    const bar = d3.select(this);
    const targetHeight = innerHeight - yScale(d[yField]);
    bar.attr('height', targetHeight).attr('y', innerHeight - targetHeight).style('opacity', 1);
  }});
  g.selectAll('.value-label, .category-label').style('opacity', 1);
  g.selectAll('.x-axis-label, .y-axis-label').style('opacity', 1);
  
  // Continue executing emphasis animations (don't return)
}} else if (frame >= animStart) {{
  // Step 2: Entrance animation in progress, use absolute time
  const totalTime = (frame - animStart) / fps;  // Current elapsed seconds

  // Bar animation
  g.selectAll('.bar').each(function(d: any, i: number) {{
    const delayPerBar = 0.12;  // Fixed delay 0.12 seconds
    const animDuration = 0.6;  // Fixed duration 0.6 seconds
    const barStart = i * delayPerBar;
    const barEnd = barStart + animDuration;

    if (totalTime >= barStart && totalTime <= barEnd) {{
      const barProgress = (totalTime - barStart) / animDuration;
      const eased = d3.easeCubicOut(barProgress);
      // ... set height and opacity
    }} else if (totalTime > barEnd) {{
      // Bar animation completed, set to final state
    }}
  }});

  // Label animation (category + value simultaneously)
  g.selectAll('.value-label, .category-label').each(function(d: any, i: number) {{
    const delayPerBar = 0.12;
    const labelDelay = 0.3;  // Fixed delay 0.3 seconds
    const animDuration = 0.4; // Fixed duration 0.4 seconds
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

**Time Parameters (fixed values, do not change):**
- Bar delay: `0.12 seconds per bar`
- Bar animation duration: `0.6 seconds`
- Label additional delay: `0.3 seconds`
- Label fade-in duration: `0.4 seconds`
- Axis label delay: `0.3 seconds`, fade-in duration: `0.4 seconds`

### 2. **Emphasis Animation (CRITICAL - Must correctly handle multiple simultaneously active animations)**:
- ⚠️ **Important Issue**: When multiple emphasis animations overlap in time (e.g., simultaneously mentioning "Minneapolis and Dallas"),
  if you iterate through animations one by one, later animations will overwrite earlier effects, causing only the last highlight to be visible.
- ✅ **Correct Approach**:
  1. **First collect all currently active emphasis animations** (check `frame >= animStart && frame < animStart + animDuration`)
  2. **Collect all data items that need highlighting** (use `Set<string>` to store matching data item identifiers, like `d[xField]`)
  3. **Process all data points at once** (iterate through all bars/points, check if in highlightedItems, avoid loop overwriting)
- Highlighted bars use red border (`stroke: '#ff6b6b'`, `stroke-width: 3-5px`)
- Add glow effect: `drop-shadow(0 0 15px rgba(255, 107, 107, 0.8))` — write the full string in one go; never truncate.
- Do NOT use `declare module 'd3'` or any `declare module`; if you need a helper (e.g. leastSquares), use `(d3 as any).leastSquares = function(...) { ... }` at runtime.
- Pulse effect should not be too exaggerated, scale range `Math.sin(...) * 0.05 + 1` (1.0-1.05x)
- Non-highlighted bars reduce opacity to `0.3`
- For scatter plots, also handle `.dot` or `.circle` elements
   
### 3. **Selector Standards (CRITICAL! Avoid element conflicts)**:
- ✅ **Use precise class selectors**: `.bar`, `.dot`, `.city-label`, `.grid-x`, `.grid-y`, etc.
- ❌ **Avoid broad tag selectors**: `text`, `line`, `circle`, `g text` - these select all elements of the same type, causing conflicts
- ❌ **Wrong example**: `g.selectAll('g text')` - selects all text within g, including labels, axis ticks, etc.
- ✅ **Correct example**: `g.selectAll('.city-label')` - only selects elements with specific class

### 4. **Smooth Transitions - D3 Ease Function Correct Usage (CRITICAL!)**:
- ✅ **Correct usage**: Directly call ease function, pass progress value (0-1)
  - `d3.easeCubicOut(progress)` - Cubic ease out (recommended, smooth and natural)
  - `d3.easeQuadOut(progress)` - Quadratic ease out
  - `d3.easeElasticOut(progress)` - Elastic ease out (has bounce effect)
  - `d3.easeBackOut(progress)` - Back ease out (has slight overshoot)
  - `d3.easeLinear(progress)` - Linear (no easing)
- ❌ **Wrong usage** (these APIs don't exist!):
  - `d3.easeBackOut.exponent(1.2)(progress)` - ❌ easeBackOut has no .exponent() method
  - `d3.easeBackOut.overshoot(1.2)(progress)` - ❌ easeBackOut has no .overshoot() method
  - `d3.easeCubicOut.exponent(...)` - ❌ All ease functions have no .exponent() method
- **Correct example**:
  ```javascript
  const progress = (totalTime - startTime) / duration;
  const eased = d3.easeCubicOut(progress);  // ✅ Correct
  element.style('opacity', eased);
  ```
- Emphasis start/end should have smooth transitions
   
### 5. **Info Card Animation** (if info cards exist):
- Cards should also have fade-in animation
- Delay 0.4-0.5 relative progress

# Output Format
Output complete TypeScript code (with animations):
- Do not use markdown code blocks (```)
- Do not add explanations
- Directly output complete runnable code
- Component name changed to: `export const SceneComponentAnimated`

Now start generating the animated component:
"""
    return prompt


def add_animations_with_llm(static_tsx_path, animations_config, narrations, scene_title, scene_time_range, llm_client, output_path, verbose=True) -> Tuple[bool, Optional[str]]:
    """
    使用 LLM 给静态组件添加动画和字幕。
    返回 (True, None) 成功，(False, error_detail) 失败，便于排查。
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
    response = None
    try:
        # 调用 LLM
        response, usage = llm_client.call(prompt, temperature=0.7, max_tokens=settings.LLM_MAX_TOKENS)
        
        # 清理响应
        animated_code = response.strip()
        if animated_code.startswith("```typescript") or animated_code.startswith("```tsx"):
            animated_code = animated_code.split('\n', 1)[1]
        if animated_code.startswith("```"):
            animated_code = animated_code[3:]
        if animated_code.endswith("```"):
            animated_code = animated_code[:-3]
        animated_code = animated_code.strip()
        animated_code = sanitize_tsx_for_browser(animated_code)
        
        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(animated_code)

        if verbose:
            print(f"   ✅ 生成成功: {os.path.basename(output_path)}")
            print(f"   文件大小: {len(animated_code)} 字符 (增加了 {len(animated_code) - len(static_code)} 字符)")

        # 语法校验，不通过则返回失败以触发重试
        if verbose:
            print(f"   🔍 验证语法...")
        is_valid, error_msg = validate_component_syntax(Path(output_path))
        if not is_valid:
            if verbose:
                print(f"   ❌ 语法验证失败: {error_msg}")
            return (False, error_msg or "语法验证失败")
        if verbose:
            print(f"   ✅ 语法验证通过")
        return (True, None)

    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        # 始终打印详细错误，便于排查（不依赖 verbose）
        print(f"   ❌ 动画生成失败 [{scene_title}]: {err_msg}")
        traceback.print_exc()
        if response is not None and len(response) > 0:
            snippet = (response[:500] if isinstance(response, str) else str(response)[:500]).replace("\n", " ")
            print(f"   📄 响应片段 (前500字符): {snippet}...")
        return (False, err_msg)


def process_single_scene_wrapper(
    scene,
    idx: int,
    total: int,
    llm_client,
    static_input_dir: str,
    output_dir: str,
    video_meta: dict,
    task_id: str = None,
    max_retries: int = 5
) -> Tuple[int, str, bool, str]:
    """
    包装函数，用于并行执行。支持语法校验 + 失败重试（最多 max_retries 次）。
    """
    scene_id = scene.get('id', f'scene_{idx}')
    scene_title = scene.get('content', {}).get('title', 'Unknown')
    dataset_name = extract_dataset_name(video_meta)
    scene_id_camel = ''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())
    
    if task_id:
        component_name = f"{dataset_name}_{scene_id_camel}_{task_id}"
    else:
        component_name = f"{dataset_name}_{scene_id_camel}"
    
    static_tsx_path = os.path.join(static_input_dir, f"{component_name}.tsx")
    if not os.path.exists(static_tsx_path):
        return (idx, scene_id, False, f"❌ {scene_title} - 静态文件不存在: {component_name}.tsx")
    
    output_path = os.path.join(output_dir, f"{component_name}Animated.tsx")
    animations_config = scene.get('animations', [])
    narrations = scene.get('narration', [])
    scene_time_range = scene.get('time_range', [0, 10])
    
    last_error = None
    start_time = time.time()
    attempt = 0
    
    while True:
        attempt += 1
        elapsed = time.time() - start_time
        try:
            success, err_detail = add_animations_with_llm(
                static_tsx_path,
                animations_config,
                narrations,
                scene_title,
                scene_time_range,
                llm_client,
                output_path,
                verbose=(attempt > 1),
            )
            if success:
                file_size = os.path.getsize(output_path)
                retry_info = f" (重试 {attempt}次)" if attempt > 1 else ""
                return (idx, scene_id, True, f"✅ {scene_title} ({file_size} 字节){retry_info}")
            last_error = err_detail or "添加动画失败（返回 False）"
        except Exception as e:
            last_error = str(e)
            if attempt == 1:
                traceback.print_exc()
        
        should_retry, reason = should_retry_on_error(last_error, attempt, elapsed, max_retries)
        if should_retry:
            wait_time = calculate_retry_wait_time(last_error, attempt)
            print(f"   ⚠️  [{idx}/{total}] {scene_title} - 第 {attempt} 次尝试失败，{wait_time}秒后重试...")
            time.sleep(wait_time)
            continue
        print(f"   ❌ [{idx}/{total}] {scene_title} - 停止重试: {reason}")
        break
    
    # 重试用尽，fallback 到静态组件
    detail = last_error or "生成失败"
    print(f"   ⚠️  动画生成失败，使用静态组件作为fallback: {scene_title}")
    try:
        import re
        with open(static_tsx_path, 'r', encoding='utf-8') as f:
            static_code = f.read()
        pattern = r'export const (\w+)(\s*:\s*React\.FC[^=]*)?\s*='
        match = re.search(pattern, static_code)
        if match:
            original_export = match.group(1)
            if not original_export.endswith('Animated'):
                new_export = original_export + 'Animated'
                static_code = re.sub(
                    rf'export const {re.escape(original_export)}(\s*:\s*React\.FC[^=]*)?\s*=',
                    f'export const {new_export}\\1 =',
                    static_code,
                    count=1
                )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(static_code)
        file_size = os.path.getsize(output_path)
        return (idx, scene_id, True, f"⚠️  {scene_title} - 动画生成失败，已使用静态组件 ({file_size} 字节)")
    except Exception as fallback_err:
        print(f"   ❌ Fallback也失败: {fallback_err}")
        return (idx, scene_id, False, f"❌ {scene_title} - {detail} (fallback失败: {fallback_err})")


if __name__ == "__main__":
    default_config_path = os.getenv(
        "VIDEO_DEFAULT_CONFIG_PATH",
        "infographic_generation/generated_config_aligned.json",
    )
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='给静态 TSX 组件添加动画（支持批量和并行）')
    parser.add_argument('--serial', action='store_true', help='使用串行模式（默认是并行）')
    parser.add_argument('-w', '--workers', type=int, default=5, help='并行线程数（默认5）')
    parser.add_argument('--config', type=str, 
                       default=default_config_path,
                       help='配置文件路径')
    parser.add_argument('--input', type=str,
                       default=DEFAULT_COMPONENTS_INPUT_DIR,
                       help='静态组件输入目录（基础路径）')
    parser.add_argument('--output', type=str,
                       default=DEFAULT_ANIMATED_OUTPUT_DIR,
                       help='动画组件输出目录（基础路径）')
    parser.add_argument('--task-id', type=str, default=None,
                       help='任务ID（用于子目录隔离）')
    args = parser.parse_args()
    
    # 如果提供了 task_id，则使用子目录
    if args.task_id:
        input_dir = os.path.join(args.input, args.task_id)
        output_dir = os.path.join(args.output, args.task_id)
        print(f"📁 使用任务子目录")
        print(f"   输入: {input_dir}")
        print(f"   输出: {output_dir}")
    else:
        input_dir = args.input
        output_dir = args.output
        print(f"📁 使用默认目录")
        print(f"   输入: {input_dir}")
        print(f"   输出: {output_dir}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 默认并行，除非指定 --serial
    use_parallel = not args.serial
    
    # 读取配置文件
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    # 若缺少 time_start/time_range 等字段，补一份可用的时间轴（避免 KeyError: 'time_start'）
    config = ensure_config_has_timeline(config)
    
    video_meta = config.get('meta', {})
    all_scenes = config.get('scenes', [])
    chart_scenes = [s for s in all_scenes if s['type'] == 'chart']
    
    # 初始化 LLM 客户端
    mode_text = "并行模式" if use_parallel else "串行模式"
    workers_text = f"，{args.workers} 线程" if use_parallel else ""
    print(f"🚀 初始化 LLM 客户端 (Claude Sonnet 4，{mode_text}{workers_text})...")
    
    llm_client = LLMClient(
        api_base=API_BASE,
        api_key=API_KEY,
        model=DEFAULT_MODEL
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
                    llm_client, input_dir, output_dir, video_meta, args.task_id
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
        # 串行模式（同样走 wrapper，带校验+重试）
        print("📝 使用串行模式生成...\n")
        for idx, scene in enumerate(chart_scenes, 1):
            _, _, success, message = process_single_scene_wrapper(
                scene, idx, len(chart_scenes),
                llm_client, input_dir, output_dir, video_meta, args.task_id
            )
            print(f"[{idx}/{len(chart_scenes)}] {message}")
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
    print(f"   输出目录: {output_dir}")
    print(f"\n⏱️  耗时统计：")
    print(f"   总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
    print(f"   平均每个场景: {avg_time:.1f} 秒")
    if use_parallel:
        print(f"   并行线程数: {args.workers}")
    print(f"\n💡 下一步：")
    print(f"   1. 检查生成的动画组件")
    print(f"   2. 运行自动注册脚本更新 Root.tsx")
    print(f"   3. 在 Remotion Studio 预览动画效果")
