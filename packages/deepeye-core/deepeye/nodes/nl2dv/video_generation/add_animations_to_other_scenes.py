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
    """为 Closing 场景创建动画 Prompt"""
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
  const relativeTime = frame / fps;
  
  // absoluteTime is used for subtitle matching (absolute video time)
  const absoluteTime = sceneStartOffset + relativeTime;
  
  // Animation parameters - ONLY fade in, NO fade out (keep visible until end)
  const fadeInDelay = 0.2;     // Content fades in after 0.2s
  const fadeInDuration = 0.6;  // Fade in over 0.6s
  
  // Calculate opacity - ONLY fade in, then stay at 1
  let opacity = 1;
  
  if (relativeTime < fadeInDelay) {{
    opacity = 0;
  }} else if (relativeTime < fadeInDelay + fadeInDuration) {{
    const progress = (relativeTime - fadeInDelay) / fadeInDuration;
    opacity = progress;
  }} else {{
    opacity = 1; // Keep fully visible until the end
  }}
  
  // Scale animation (slight zoom during fade in)
  const scaleProgress = Math.max(0, Math.min(1, (relativeTime - fadeInDelay) / fadeInDuration));
  const scale = 0.95 + 0.05 * scaleProgress;  // Scale from 0.95 to 1.0
  
  // Subtitle logic: find current narration based on absoluteTime
  const currentNarration = narrations.find(
    n => absoluteTime >= n.time_start && absoluteTime < n.time_end
  );
  
  return (
    <AbsoluteFill
      style={{{{
        ...originalAbsoluteFillStyle,
        opacity: opacity,
        transform: `scale(${{scale}})`,
      }}}}
    >
      {{/* Original content */}}
      <OriginalContent />

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
   - Fade in during first 0.8s
   - **NO fade out** - keep visible until the end (opacity stays at 1)
   - Slight scale effect (0.95 → 1.0) during fade in
   - Add narration subtitles at bottom

**ORIGINAL STATIC CODE:**
```tsx
{static_tsx_code}
```

**YOUR TASK:**
1. Add Remotion imports (`useCurrentFrame`, `useVideoConfig`)
2. Add animation logic at the beginning of the component
3. Apply opacity and scale animations directly to AbsoluteFill
4. Add narration subtitle UI at the bottom
5. Keep all other code unchanged (structure, colors, text, etc.)

**CRITICAL:**
- **NO FADE OUT** - content must stay visible until the end
- `frame` in Sequence is LOCAL (starts from 0)
- Use `relativeTime = frame / fps` for animations
- Use `absoluteTime = sceneStartOffset + relativeTime` for subtitles
- DO NOT change the component structure or content

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
        
        response = llm_client.call(prompt, temperature=0.7, max_tokens=6000)
        
        # 提取代码
        animated_tsx_code = response.strip()
        if '```tsx' in animated_tsx_code:
            animated_tsx_code = animated_tsx_code.split('```tsx')[1].split('```')[0].strip()
        elif '```typescript' in animated_tsx_code:
            animated_tsx_code = animated_tsx_code.split('```typescript')[1].split('```')[0].strip()
        elif '```' in animated_tsx_code:
            animated_tsx_code = animated_tsx_code.split('```')[1].split('```')[0].strip()
        
        # 保存文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(animated_tsx_code)
        
        if verbose:
            print(f"   ✅ 成功生成: {output_file}")
        
        return True
    
    except Exception as e:
        if verbose:
            print(f"   ❌ 添加动画失败: {str(e)}")
        return False


def add_animation_wrapper(scene_data, static_dir, animated_dir, llm_client, idx, total_scenes, video_meta):
    """包装函数用于并行执行"""
    scene_id = scene_data.get('id', f'scene_{idx}')
    scene_type = scene_data.get('type', 'unknown')

    # 构建文件名（包含数据集名字）
    dataset_name = extract_dataset_name(video_meta)
    component_name = f"{dataset_name}_{''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())}Component"
    static_file = os.path.join(static_dir, f"{component_name}.tsx")
    animated_file = os.path.join(animated_dir, f"{component_name}Animated.tsx")
    
    # 检查静态文件是否存在
    if not os.path.exists(static_file):
        return (idx, scene_id, False, f"❌ {scene_type}: {scene_id} - 静态文件不存在")
    
    try:
        success = add_animation_to_component(
            static_file,
            scene_data,
            llm_client,
            animated_file,
            verbose=False
        )
        
        if success:
            return (idx, scene_id, True, f"✅ {scene_type}: {scene_id}")
        else:
            return (idx, scene_id, False, f"❌ {scene_type}: {scene_id} - 添加动画失败")
    
    except Exception as e:
        return (idx, scene_id, False, f"❌ {scene_type}: {scene_id} - {str(e)}")


def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='为其他场景添加动画（Opening/Closing/Stat Cards）')
    parser.add_argument('-w', '--workers', type=int, default=5, help='并行线程数（默认5）')
    parser.add_argument('--config', type=str,
                       default='infographic_generation/generated_20251216_045823_aligned_flight.json',
                       help='配置文件路径')
    parser.add_argument('--static-dir', type=str,
                       default='infographic_generation/output/claude_tsx_components',
                       help='静态组件目录')
    parser.add_argument('--animated-dir', type=str,
                       default='infographic_generation/output/claude_tsx_animated',
                       help='动画组件输出目录（默认输出到claude_tsx_animated）')
    args = parser.parse_args()
    
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
        api_base="https://newapi.deepwisdom.ai",
        api_key="sk-Rq3hmLp1zTqnvUMow4sninyeuGk8rlE2xnIihASNWkeEfiPv",
        model="claude-sonnet-4-20250514"
    )
    
    # 过滤其他场景
    other_scenes = [s for s in all_scenes if s['type'] in ['opening', 'closing', 'stat_cards']]
    
    # 创建输出目录
    os.makedirs(args.animated_dir, exist_ok=True)
    
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
                args.static_dir,
                args.animated_dir,
                llm_client,
                idx,
                len(other_scenes),
                video_meta
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
    print(f"📂 输出目录: {args.animated_dir}")
    print("="*70)


if __name__ == '__main__':
    main()

