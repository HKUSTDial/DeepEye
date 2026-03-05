"""
为其他场景（Opening, Closing, Stat Cards）添加动画
读取静态组件，使用 LLM 添加动画逻辑
支持批量处理和并行执行
"""

import json
import os
import sys
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
from pathlib import Path

# 导入项目配置和 LLM 客户端
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


def create_opening_animation_prompt(static_tsx_code, scene_data, scene_time_range):
    """为 Opening 场景创建动画 Prompt"""
    scene_start_time = scene_time_range[0]
    duration = scene_time_range[1] - scene_time_range[0]
    
    prompt = f"""
You are adding ANIMATIONS to an OPENING SCENE component.

**SCENE TIMING:**
- Scene starts at: {scene_start_time}s
- Duration: {duration}s
- FPS: 30

**ANIMATION REQUIREMENTS:**

1. **Import Remotion hooks**:
```tsx
import {{ useCurrentFrame, useVideoConfig }} from 'remotion';
```

2. **Add animation logic inside component**:
```tsx
export const ComponentName: React.FC<SceneProps> = ({{ 
  sceneStartOffset = 0,
  narrations = []
}}) => {{
  const frame = useCurrentFrame();
  const {{ fps }} = useVideoConfig();
  
  // CRITICAL: In Sequence, frame starts from 0 (local frame number)
  // relativeTime is time relative to scene start (in seconds)
  const relativeTime = frame / fps;
  
  // absoluteTime is used for subtitle matching (absolute video time)
  const absoluteTime = sceneStartOffset + relativeTime;
  
  // Animation parameters
  const titleDelay = 0.2;      // Title appears after 0.2s
  const subtitleDelay = 0.5;   // Subtitle appears after 0.5s
  const animDuration = 0.6;    // Animation duration: 0.6s
  
  // Title animation (fade in + slide up)
  const titleProgress = Math.max(0, Math.min(1, (relativeTime - titleDelay) / animDuration));
  const titleOpacity = titleProgress;
  const titleY = (1 - titleProgress) * 20; // Slide up 20px
  
  // Subtitle animation (fade in + slide up)
  const subtitleProgress = Math.max(0, Math.min(1, (relativeTime - subtitleDelay) / animDuration));
  const subtitleOpacity = subtitleProgress;
  const subtitleY = (1 - subtitleProgress) * 20;
  
  // Subtitle logic: find current narration based on absoluteTime
  const currentNarration = narrations.find(
    n => absoluteTime >= n.time_start && absoluteTime < n.time_end
  );
  
  return (
    <AbsoluteFill>
      {{/* Title - add opacity and transform */}}
      <div style={{{{ 
        ...originalTitleStyle, 
        opacity: titleOpacity,
        transform: `translateY(${{titleY}}px)`,
      }}}}>
        Title Text
      </div>
      
      {{/* Subtitle - add opacity and transform */}}
      <div style={{{{ 
        ...originalSubtitleStyle, 
        opacity: subtitleOpacity,
        transform: `translateY(${{subtitleY}}px)`,
      }}}}>
        Subtitle Text
      </div>

      {{/* Narration Subtitles */}}
      {{currentNarration && (
        <div
          style={{{{
            position: 'absolute',
            bottom: 35,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            pointerEvents: 'none',
          }}}}
        >
          <div
            style={{{{
              background: 'rgba(0, 0, 0, 0.75)',
              padding: '12px 24px',
              borderRadius: 8,
              maxWidth: '90%',
              textAlign: 'center',
            }}}}
          >
            <span
              style={{{{
                color: '#ffffff',
                fontSize: 17,
                fontWeight: 500,
                lineHeight: 1.45,
                fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
              }}}}
            >
              {{currentNarration.text}}
            </span>
          </div>
        </div>
      )}}
    </AbsoluteFill>
  );
}};
```

3. **Key points**:
   - **CRITICAL**: `frame` in Sequence is LOCAL (starts from 0), NOT global frame number
   - Use `relativeTime = frame / fps` for animation timing (relative to scene start)
   - Use `absoluteTime = sceneStartOffset + relativeTime` for subtitle matching
   - Title fades in and slides up from y=20 to y=0
   - Subtitle fades in slightly later with same effect
   - Narration subtitles appear at bottom based on absoluteTime
   - All elements should reach full opacity and y=0 after animation completes

**ORIGINAL STATIC CODE:**
```tsx
{static_tsx_code}
```

**YOUR TASK:**
1. Add Remotion imports (`useCurrentFrame`, `useVideoConfig`)
2. Add animation logic at the beginning of the component
3. Modify inline styles to include opacity and transform animations
4. Keep all other code unchanged (structure, colors, text, etc.)
5. Ensure animations are smooth and natural

**CRITICAL:**
- DO NOT change the component structure or content
- ONLY add animation logic and modify inline styles
- Ensure all elements are fully visible after animation completes
- Use `relativeTime` (not absolute `frame`) for timing

Return ONLY the complete animated TSX code, no explanation.
"""
    
    return prompt


def create_closing_animation_prompt(static_tsx_code, scene_data, scene_time_range):
    """为 Closing 场景创建动画 Prompt（改进版：更丰富的分层动画）"""
    scene_start_time = scene_time_range[0]
    duration = scene_time_range[1] - scene_time_range[0]
    
    prompt = f"""
You are adding ANIMATIONS to a CLOSING SCENE component.

**SCENE TIMING:**
- Scene starts at: {scene_start_time}s
- Duration: {duration}s
- FPS: 30

**ANIMATION REQUIREMENTS:**

1. **Import Remotion hooks**:
```tsx
import {{ useCurrentFrame, useVideoConfig, interpolate, Easing }} from 'remotion';
```

2. **Add animation logic inside component**:
```tsx
export const ComponentName: React.FC<SceneProps> = ({{ 
  sceneStartOffset = 0,
  narrations = []
}}) => {{
  const frame = useCurrentFrame();
  const {{ fps }} = useVideoConfig();
  
  // CRITICAL: In Sequence, frame starts from 0 (local frame number)
  const relativeTime = frame / fps;
  
  // absoluteTime is used for subtitle matching (absolute video time)
  const absoluteTime = sceneStartOffset + relativeTime;
  
  // Animation parameters - RICH LAYERED ANIMATIONS
  const titleDelay = 0.15;           // Title starts animating at 0.15s
  const titleDuration = 0.8;         // Title animation duration: 0.8s
  const subtitleDelay = 0.5;         // Subtitle starts after title (0.5s delay)
  const subtitleDuration = 0.7;       // Subtitle animation duration: 0.7s
  
  // Title animation: fade in + slide up + scale
  const titleProgress = interpolate(
    frame,
    [titleDelay * fps, (titleDelay + titleDuration) * fps],
    [0, 1],
    {{
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }}
  );
  
  const titleOpacity = titleProgress;
  const titleY = (1 - titleProgress) * 30;  // Slide up from 30px below
  const titleScale = 0.92 + 0.08 * titleProgress;  // Scale from 0.92 to 1.0
  
  // Subtitle animation: fade in + slide up (delayed)
  const subtitleProgress = interpolate(
    frame,
    [subtitleDelay * fps, (subtitleDelay + subtitleDuration) * fps],
    [0, 1],
    {{
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    }}
  );
  
  const subtitleOpacity = subtitleProgress;
  const subtitleY = (1 - subtitleProgress) * 20;  // Slide up from 20px below
  
  // Subtitle logic: find current narration based on absoluteTime
  const currentNarration = narrations.find(
    n => absoluteTime >= n.time_start && absoluteTime < n.time_end
  );
  
  return (
    <AbsoluteFill
      style={{{{
        ...originalAbsoluteFillStyle
      }}}}
    >
      {{/* Main Title - with rich animations */}}
      <div
        style={{{{...originalTitleStyle,
          opacity: titleOpacity,
          transform: `translateY(${{titleY}}px) scale(${{titleScale}})`,
          transition: 'none', // Disable CSS transitions
        }}}}
      >
        {{/* Title content */}}
      </div>
      
      {{/* Subtitle/Summary Text - with delayed animation */}}
      {{/* Only animate if subtitle exists in original code */}}
      <div
        style={{{{...originalSubtitleStyle,
          opacity: subtitleOpacity,
          transform: `translateY(${{subtitleY}}px)`,
          transition: 'none',
        }}}}
      >
        {{/* Subtitle content */}}
      </div>

      {{/* Narration Subtitles */}}
      {{currentNarration && (
        <div
          style={{{{
            position: 'absolute',
            bottom: 35,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            pointerEvents: 'none',
          }}}}
        >
          <div
            style={{{{
              background: 'rgba(0, 0, 0, 0.75)',
              padding: '12px 24px',
              borderRadius: 8,
              maxWidth: '90%',
              textAlign: 'center',
            }}}}
          >
            <span
              style={{{{
                color: '#ffffff',
                fontSize: 17,
                fontWeight: 500,
                lineHeight: 1.45,
                fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
              }}}}
            >
              {{currentNarration.text}}
            </span>
          </div>
        </div>
      )}}
    </AbsoluteFill>
  );
}};
```

3. **Key points**:
   - **CRITICAL**: `frame` in Sequence is LOCAL (starts from 0), NOT global frame number
   - Use `relativeTime = frame / fps` for animation timing
   - Use `absoluteTime = sceneStartOffset + relativeTime` for subtitle matching
   - **Title animation**: Fade in + slide up (30px) + scale (0.92→1.0) over 0.8s, starts at 0.15s
   - **Subtitle animation**: Fade in + slide up (20px) over 0.7s, starts at 0.5s (delayed after title)
   - Use `interpolate` with `Easing.out(Easing.cubic)` for smooth, elegant animations
   - **NO fade out** - keep visible until the end (opacity stays at 1 after animation completes)
   - Apply animations to EACH element separately (title and subtitle independently)
   - Add narration subtitles at bottom

**ORIGINAL STATIC CODE:**
```tsx
{static_tsx_code}
```

**YOUR TASK:**
1. Add Remotion imports (`useCurrentFrame`, `useVideoConfig`, `interpolate`, `Easing`)
2. Add animation logic at the beginning of the component
3. **Apply animations to TITLE and SUBTITLE separately** (not to the whole AbsoluteFill)
4. Title: opacity + translateY + scale animations
5. Subtitle: opacity + translateY animations (delayed after title)
6. Use `interpolate` with easing for smooth animations
7. Add narration subtitle UI at the bottom
8. Keep all other code unchanged (structure, colors, text, etc.)

**CRITICAL:**
- **NO FADE OUT** - content must stay visible until the end
- `frame` in Sequence is LOCAL (starts from 0)
- Use `relativeTime = frame / fps` for animations
- Use `absoluteTime = sceneStartOffset + relativeTime` for subtitles
- **Apply animations to individual elements** (title div, subtitle div), NOT to AbsoluteFill
- Title appears first, then subtitle follows with delay
- Use `interpolate` with `Easing.out(Easing.cubic)` for elegant easing
- DO NOT change the component structure or content
- If subtitle doesn't exist in original code, skip subtitle animation

Return ONLY the complete animated TSX code, no explanation.
"""
    
    return prompt


def create_stat_cards_animation_prompt(static_tsx_code, scene_data, scene_time_range):
    """为 Stat Cards 场景创建动画 Prompt"""
    scene_start_time = scene_time_range[0]
    duration = scene_time_range[1] - scene_time_range[0]
    
    content = scene_data.get('content', {})
    cards = content.get('cards', [])
    num_cards = len(cards)
    animations = scene_data.get('animations', [])
    
    # 生成动画配置的 JSON 字符串（用于 prompt）
    animations_json = json.dumps(animations, indent=2, ensure_ascii=False) if animations else "[]"
    
    prompt = f"""
You are adding ANIMATIONS to a STAT CARDS SCENE component.

**SCENE TIMING:**
- Scene starts at: {scene_start_time}s
- Duration: {duration}s
- Number of cards: {num_cards}
- FPS: 30

**ANIMATION CONFIGURATION:**
The scene has the following animations defined in the config:
```json
{animations_json}
```

**ANIMATION REQUIREMENTS:**

1. **Import Remotion hooks**:
```tsx
import React, {{ useMemo }} from 'react';
import {{ AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing }} from 'remotion';
```

2. **Add animations prop to SceneProps interface**:
```tsx
interface Animation {{
  id: string;
  type: 'entrance' | 'emphasis';
  effect: string;
  time_start: number;
  duration: number;
  target_data?: {{
    card_index?: number;
  }};
  style?: {{
    direction?: string;
    stagger_delay?: number;
    intensity?: number;
  }};
}}

interface SceneProps {{
  sceneStartOffset?: number;
  narrations?: Array<{{text: string; time_start: number; time_end: number}}>;
  animations?: Animation[];  // ADD THIS PROP
}}
```

3. **Add animation logic inside component**:
```tsx
export const ComponentName: React.FC<SceneProps> = ({{ 
  sceneStartOffset = 0,
  narrations = [],
  animations = []  // RECEIVE animations prop
}}) => {{
  const frame = useCurrentFrame();
  const {{ fps }} = useVideoConfig();
  
  // CRITICAL: In Sequence, frame starts from 0 (local frame number)
  const relativeTime = frame / fps;
  const absoluteTime = sceneStartOffset + relativeTime;
  
  // Extract entrance animation from config
  const entranceAnim = useMemo(() => {{
    return animations.find(a => a.type === 'entrance' && a.effect === 'fade_in');
  }}, [animations]);
  
  // Get animation parameters from config (or use defaults)
  const staggerDelay = entranceAnim?.style?.stagger_delay || 0.15;
  const entranceStartFrame = entranceAnim 
    ? (entranceAnim.time_start - sceneStartOffset) * fps 
    : 0;
  const entranceDurationFrames = entranceAnim 
    ? entranceAnim.duration * fps 
    : 0.5 * fps;
  
  // Extract emphasis animations
  const emphasisAnims = useMemo(() => {{
    return animations.filter(a => a.type === 'emphasis' && a.effect === 'pulse');
  }}, [animations]);
  
  // Function to calculate card entrance animation progress
  const getCardProgress = (index: number) => {{
    if (!entranceAnim) {{
      // Fallback: use default animation
      const cardDelay = 0.2;
      const cardInterval = 0.15;
      const cardAnimDuration = 0.5;
      const cardStartTime = cardDelay + index * cardInterval;
      return Math.max(0, Math.min(1, (relativeTime - cardStartTime) / cardAnimDuration));
    }}
    
    // Use config animation timing
    const cardStartFrame = entranceStartFrame + index * (staggerDelay * fps);
    return interpolate(
      frame,
      [cardStartFrame, cardStartFrame + entranceDurationFrames],
      [0, 1],
      {{
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
        easing: Easing.out(Easing.cubic),
      }}
    );
  }};
  
  // Function to calculate card emphasis/pulse effect
  const getCardEmphasis = (cardIndex: number) => {{
    const emphasisAnim = emphasisAnims.find(a => a.target_data?.card_index === cardIndex);
    if (!emphasisAnim) return 1;
    
    const animStartFrame = (emphasisAnim.time_start - sceneStartOffset) * fps;
    const animDuration = emphasisAnim.duration * fps;
    const isActive = frame >= animStartFrame && frame < animStartFrame + animDuration;
    
    if (!isActive) return 1;
    
    const intensity = emphasisAnim.style?.intensity || 0.1;
    const progress = (frame - animStartFrame) / animDuration;
    const pulse = Math.sin(progress * Math.PI * 8) * intensity + 1;
    return pulse;
  }};
  
  // Subtitle logic
  const currentNarration = narrations.find(
    n => absoluteTime >= n.time_start && absoluteTime < n.time_end
  );
  
  return (
    <AbsoluteFill>
      <div>
        {{cards.map((card, index) => {{
          const progress = getCardProgress(index);
          const opacity = progress;
          const scale = 0.8 + 0.2 * progress;
          const y = (1 - progress) * 30;
          
          return (
            <div
              key={{index}}
              style={{{{
                ...originalCardStyle,
                opacity: opacity,
                transform: `scale(${{scale}}) translateY(${{y}}px)`,
              }}}}
            >
              {{/* Card content */}}
            </div>
          );
        }})}}
      </div>

      {{/* Subtitles */}}
      {{currentNarration && (
        <div style={{{{ position: 'absolute', bottom: 35, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}}}>
          <div style={{{{ background: 'rgba(0, 0, 0, 0.75)', padding: '12px 24px', borderRadius: 8, maxWidth: '90%', textAlign: 'center' }}}}>
            <span style={{{{ color: '#ffffff', fontSize: 17, fontWeight: 500, lineHeight: 1.45 }}}}>
              {{currentNarration.text}}
            </span>
          </div>
        </div>
      )}}
    </AbsoluteFill>
  );
}};
```

4. **Key points**:
   - **CRITICAL**: `frame` in Sequence is LOCAL (starts from 0), NOT global frame number
   - **MUST receive `animations` prop** from parent component
   - **MUST use config animation timing** from `animations` array, not hardcoded values
   - Extract `entrance` animation to get `stagger_delay`, `time_start`, and `duration`
   - Extract `emphasis` animations with `effect: 'pulse'` for card highlighting
   - Use `interpolate` with easing for smooth entrance animations
   - Implement `getCardEmphasis()` to calculate pulse effect based on `target_data.card_index`
   - When emphasis is active, increase border width and add glowing shadow effect
   - Cards appear sequentially using config's `stagger_delay`
   - Each card: fades in + scales up + slides up from bottom
   - Emphasis cards pulse (scale oscillates) when mentioned in narration

**ORIGINAL STATIC CODE:**
```tsx
{static_tsx_code}
```

**YOUR TASK:**
1. **ADD `animations?: Animation[]` to SceneProps interface**
2. **RECEIVE `animations` prop in component parameters**
3. Add Remotion imports (`useCurrentFrame`, `useVideoConfig`, `interpolate`, `Easing`, `useMemo`)
4. Extract entrance animation from `animations` array using `useMemo`
5. Extract emphasis animations from `animations` array using `useMemo`
6. Use config animation timing (NOT hardcoded values):
   - `entranceAnim.time_start` for animation start
   - `entranceAnim.duration` for animation duration
   - `entranceAnim.style.stagger_delay` for card stagger delay
7. Implement `getCardEmphasis()` function to calculate pulse effect
8. Apply emphasis effects: border width + glowing shadow when pulse is active
9. Calculate relativeTime and absoluteTime correctly (frame is LOCAL in Sequence)
10. Modify each card's inline style to include opacity, scale, translateY, borderWidth, boxShadow
11. Add narration subtitle UI at the bottom
12. Keep all other code unchanged (structure, colors, content, etc.)

**CRITICAL:**
- **MUST use `animations` prop from config**, NOT hardcoded animation parameters
- `frame` in Sequence is LOCAL (starts from 0)
- Use `relativeTime = frame / fps` for animations
- Use `absoluteTime = sceneStartOffset + relativeTime` for subtitles
- Use `interpolate` with easing for smooth animations
- Implement emphasis/pulse effect when narration mentions a card
- DO NOT change the component structure or card content
- ONLY add animation logic and modify card styles
- Each card has independent animation timing (sequential appearance)
- Ensure all cards are fully visible after their animations complete

Return ONLY the complete animated TSX code, no explanation.
"""
    
    return prompt


def get_animation_prompt_for_scene_type(static_tsx_code, scene_data, scene_time_range):
    """根据场景类型选择对应的动画 Prompt"""
    scene_type = scene_data.get('type', '')
    
    if scene_type == 'opening':
        return create_opening_animation_prompt(static_tsx_code, scene_data, scene_time_range)
    elif scene_type == 'closing':
        return create_closing_animation_prompt(static_tsx_code, scene_data, scene_time_range)
    elif scene_type == 'stat_cards':
        return create_stat_cards_animation_prompt(static_tsx_code, scene_data, scene_time_range)
    else:
        raise ValueError(f"不支持的场景类型: {scene_type}")


def add_animation_to_component(static_file, scene_data, llm_client, output_file, verbose=False):
    """为单个静态组件添加动画"""
    scene_id = scene_data.get('id', 'unknown')
    scene_type = scene_data.get('type', 'unknown')
    scene_time_range = scene_data.get('time_range', [0, 3])
    
    if verbose:
        print(f"🎬 场景: {scene_id} (type: {scene_type})")
    
    try:
        # 读取静态组件代码
        with open(static_file, 'r', encoding='utf-8') as f:
            static_tsx_code = f.read()
        
        # 生成动画 prompt
        prompt = get_animation_prompt_for_scene_type(static_tsx_code, scene_data, scene_time_range)
        
        # 调用 LLM
        if verbose:
            print(f"   📡 调用 Claude API 添加动画...")
        
        response, usage = llm_client.call(prompt, temperature=0.7, max_tokens=settings.LLM_MAX_TOKENS)
        
        # 提取代码
        animated_tsx_code = response.strip()
        if '```tsx' in animated_tsx_code:
            animated_tsx_code = animated_tsx_code.split('```tsx')[1].split('```')[0].strip()
        elif '```typescript' in animated_tsx_code:
            animated_tsx_code = animated_tsx_code.split('```typescript')[1].split('```')[0].strip()
        elif '```' in animated_tsx_code:
            animated_tsx_code = animated_tsx_code.split('```')[1].split('```')[0].strip()
        animated_tsx_code = sanitize_tsx_for_browser(animated_tsx_code)
        
        # 保存文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(animated_tsx_code)
        
        if verbose:
            print(f"   ✅ 成功生成: {output_file}")
        
        # 语法校验
        if verbose:
            print(f"   🔍 验证语法...")
        is_valid, error_msg = validate_component_syntax(Path(output_file))
        if not is_valid:
            if verbose:
                print(f"   ❌ 语法验证失败: {error_msg}")
            return False
        if verbose:
            print(f"   ✅ 语法验证通过")
        return True
    
    except Exception as e:
        if verbose:
            print(f"   ❌ 添加动画失败: {str(e)}")
        return False


def add_animation_wrapper(scene_data, static_dir, animated_dir, llm_client, idx, total_scenes, video_meta, task_id=None, max_retries: int = 5):
    """包装函数用于并行执行，支持校验+重试"""
    scene_id = scene_data.get('id', f'scene_{idx}')
    scene_type = scene_data.get('type', 'unknown')
    dataset_name = extract_dataset_name(video_meta)
    scene_id_camel = ''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())
    if task_id:
        component_name = f"{dataset_name}_{scene_id_camel}_{task_id}Component"
    else:
        component_name = f"{dataset_name}_{scene_id_camel}Component"
    static_file = os.path.join(static_dir, f"{component_name}.tsx")
    animated_file = os.path.join(animated_dir, f"{component_name}Animated.tsx")
    if not os.path.exists(static_file):
        return (idx, scene_id, False, f"❌ {scene_type}: {scene_id} - 静态文件不存在")
    
    last_error = None
    start_time = time.time()
    attempt = 0
    while True:
        attempt += 1
        elapsed = time.time() - start_time
        try:
            success = add_animation_to_component(
                static_file, scene_data, llm_client, animated_file, verbose=(attempt > 1)
            )
            if success:
                retry_info = f" (重试 {attempt}次)" if attempt > 1 else ""
                return (idx, scene_id, True, f"✅ {scene_type}: {scene_id}{retry_info}")
            last_error = "添加动画失败（返回 False）"
        except Exception as e:
            last_error = str(e)
        should_retry, reason = should_retry_on_error(last_error, attempt, elapsed, max_retries)
        if should_retry:
            wait_time = calculate_retry_wait_time(last_error, attempt)
            print(f"   ⚠️  [{idx}/{total_scenes}] {scene_type}: {scene_id} - 第 {attempt} 次失败，{wait_time}秒后重试...")
            time.sleep(wait_time)
            continue
        print(f"   ❌ [{idx}/{total_scenes}] {scene_type}: {scene_id} - 停止重试: {reason}")
        break
    
    # 重试用尽：复制静态组件作为后备
    try:
        import shutil
        shutil.copy2(static_file, animated_file)
        return (idx, scene_id, True, f"⚠️  {scene_type}: {scene_id} - 已用静态组件作为后备")
    except Exception as e:
        return (idx, scene_id, False, f"❌ {scene_type}: {scene_id} - {last_error} (后备复制失败: {e})")


def main():
    default_config_path = os.getenv(
        "VIDEO_DEFAULT_CONFIG_PATH",
        "infographic_generation/generated_config_aligned.json",
    )
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='为其他场景添加动画（Opening/Closing/Stat Cards）')
    parser.add_argument('-w', '--workers', type=int, default=5, help='并行线程数（默认5）')
    parser.add_argument('--config', type=str,
                       default=default_config_path,
                       help='配置文件路径')
    parser.add_argument('--static-dir', type=str,
                       default=DEFAULT_COMPONENTS_INPUT_DIR,
                       help='静态组件目录（基础路径）')
    parser.add_argument('--animated-dir', type=str,
                       default=DEFAULT_ANIMATED_OUTPUT_DIR,
                       help='动画组件输出目录（基础路径）')
    parser.add_argument('--task-id', type=str, default=None,
                       help='任务ID（用于子目录隔离）')
    args = parser.parse_args()
    
    # 如果提供了 task_id，则使用子目录
    if args.task_id:
        static_dir = os.path.join(args.static_dir, args.task_id)
        animated_dir = os.path.join(args.animated_dir, args.task_id)
        print(f"📁 使用任务子目录")
        print(f"   静态输入: {static_dir}")
        print(f"   动画输出: {animated_dir}")
    else:
        static_dir = args.static_dir
        animated_dir = args.animated_dir
        print(f"📁 使用默认目录")
        print(f"   静态输入: {static_dir}")
        print(f"   动画输出: {animated_dir}")
    
    # 确保输出目录存在
    os.makedirs(animated_dir, exist_ok=True)
    
    start_time = time.time()
    
    # 读取配置文件
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    video_meta = config.get('meta', {})
    all_scenes = config.get('scenes', [])
    
    # 初始化 LLM 客户端
    print(f"🚀 初始化 LLM 客户端 (Claude Sonnet 4，并行模式，{args.workers} 线程)...")
    
    llm_client = LLMClient(
        api_base=API_BASE,
        api_key=API_KEY,
        model=DEFAULT_MODEL
    )
    
    # 过滤其他场景
    other_scenes = [s for s in all_scenes if s['type'] in ['opening', 'closing', 'stat_cards']]
    
    print(f"\n📊 视频标题: {video_meta.get('title', 'N/A')}")
    print(f"📊 共找到 {len(other_scenes)} 个其他场景")
    print(f"   - Opening: {len([s for s in other_scenes if s['type'] == 'opening'])}")
    print(f"   - Closing: {len([s for s in other_scenes if s['type'] == 'closing'])}")
    print(f"   - Stat Cards: {len([s for s in other_scenes if s['type'] == 'stat_cards'])}")
    print("="*70)
    
    if len(other_scenes) == 0:
        print("⚠️  未找到任何其他场景（opening/closing/stat_cards），退出。")
        return
    
    success_count = 0
    
    # 并行模式
    print(f"⚡ 使用并行模式添加动画（{args.workers} 个线程）...\n")
    results = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # 提交所有任务
        future_to_scene = {
            executor.submit(
                add_animation_wrapper,
                scene,
                static_dir,
                animated_dir,
                llm_client,
                idx,
                len(other_scenes),
                video_meta,
                args.task_id
            ): idx
            for idx, scene in enumerate(other_scenes, 1)
        }
        
        # 收集结果（按完成顺序）
        for future in as_completed(future_to_scene):
            idx, scene_id, success, message = future.result()
            results.append((idx, scene_id, success, message))
            print(f"[{idx}/{len(other_scenes)}] {message}")
            if success:
                success_count += 1
    
    # 按原始顺序排序
    results.sort(key=lambda x: x[0])
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*70)
    print("🎉 动画添加完成！")
    print(f"✅ 成功: {success_count}/{len(other_scenes)}")
    print(f"⏱️  总耗时: {elapsed:.1f}秒")
    print(f"📂 输出目录: {animated_dir}")
    print("="*70)


if __name__ == '__main__':
    main()
