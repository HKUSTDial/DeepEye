"""
使用 Claude API 生成其他场景的 TSX 组件（Opening, Closing, Stat Cards）

支持并行生成，专门处理非图表场景：
- opening: 开场场景（标题 + 副标题 + 渐变背景）
- closing: 结尾场景（感谢语 + 渐变背景）
- stat_cards: 数据卡片（2-4个关键指标）

使用方法：
  python "infographic_generation/generate_other_scenes.py" --config xxx.json --workers 5
"""

import json
import os
import sys
import argparse
import time
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


def create_opening_scene_prompt(scene_data, video_meta, component_name, scene_index=1, total_scenes=1):
    """创建 Opening 场景的 Prompt"""
    content = scene_data.get('content', {})
    title = content.get('title', 'Welcome')
    subtitle = content.get('subtitle', '')
    narration = scene_data.get('narration', [])
    narration_text = narration[0].get('text', '') if narration else ''
    
    # 背景色配置 - 统一使用纯色（与图表场景保持一致）
    # 优先从图表场景获取统一的背景色，如果没有则从当前场景读取
    background = content.get('background', {})
    if background.get('type') == 'gradient':
        bg_color = background.get('colors', ['#0f1419'])[0]
    elif background.get('type') == 'solid':
        bg_color = background.get('color', '#0f1419')
    else:
        # 如果没有 background 配置，尝试从 style 获取（向后兼容）
        style = content.get('style', {})
        bg_color = style.get('background_color', '#0f1419')
    
    # 文字颜色配置
    style = content.get('style', {})
    text_color = style.get('text_color', '#ffffff')
    subtitle_color = style.get('subtitle_color', '#e0e0e0')
    
    # 场景时间范围
    time_range = scene_data.get('time_range', [0, 3])
    duration = time_range[1] - time_range[0]
    
    prompt = f"""
You are creating an OPENING SCENE for a data video.

**VIDEO CONTEXT:**
- Video Title: "{video_meta.get('title', 'Data Insights')}"
- Scene {scene_index} of {total_scenes}
- Duration: {duration} seconds

**SCENE CONTENT:**
- Main Title: "{title}"
- Subtitle: "{subtitle}"
- Narration: "{narration_text}"

**DESIGN REQUIREMENTS:**

1. **Background**: 
   - Use solid background color (to match chart scenes)
   - Color: {bg_color}
   
2. **Layout**:
   - Centered title and subtitle
   - Title: Large, bold, eye-catching (font-size: 56-72px)
   - Subtitle: Smaller, secondary text (font-size: 24-32px)
   - Spacing: 20-30px between title and subtitle

3. **Colors**:
   - Title color: {text_color}
   - Subtitle color: {subtitle_color}
   
4. **Typography**:
   - Use modern sans-serif font (e.g., 'Inter', 'Helvetica', 'Arial')
   - Title: font-weight 700-900
   - Subtitle: font-weight 400-500

5. **NO ANIMATIONS** in this static version
   - Animations will be added later by a separate script
   - All elements should be at full opacity
   - All elements at final positions

6. **Subtitle/Narration Space**:
   - Reserve BOTTOM 80px for narration subtitles (will be added in animation phase)
   - Adjust content positioning to avoid overlap with subtitle area
   - Keep main content in upper area

**OUTPUT REQUIREMENTS:**

Generate a complete TSX component (React + TypeScript + Remotion):

```tsx
import React from 'react';
import {{ AbsoluteFill }} from 'remotion';

interface SceneProps {{
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{{text: string; time_start: number; time_end: number}}>; // Narration subtitles (will be used in animation version)
}}

export const [ComponentName]: React.FC<SceneProps> = ({{ sceneStartOffset = 0 }}) => {{
  return (
    <AbsoluteFill
      style={{{{
        background: '{bg_color}',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px',
      }}}}
    >
      {{/* Main Title */}}
      <div
        style={{{{
          fontSize: 64,
          fontWeight: 800,
          color: '{text_color}',
          textAlign: 'center',
          marginBottom: 24,
          maxWidth: '80%',
          lineHeight: 1.2,
        }}}}
      >
        {title}
      </div>

      {{/* Subtitle */}}
      <div
        style={{{{
          fontSize: 28,
          fontWeight: 400,
          color: '{subtitle_color}',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.5,
        }}}}
      >
        {subtitle}
      </div>
    </AbsoluteFill>
  );
}};
```

**CRITICAL**:
- Replace [ComponentName] with the actual component name
- Keep the structure clean and simple
- Ensure all styles are inline for easy animation later
- DO NOT add any animation logic (opacity transitions, transforms, etc.)
- All elements should be visible and at final positions

Return ONLY the complete TSX code, no explanation.
"""
    
    return prompt


def create_closing_scene_prompt(scene_data, video_meta, component_name, scene_index=1, total_scenes=1):
    """创建 Closing 场景的 Prompt"""
    content = scene_data.get('content', {})
    title = content.get('title', 'Thank You')
    narration = scene_data.get('narration', [])
    narration_text = ' '.join([n.get('text', '') for n in narration])
    
    # 背景色配置 - 统一使用纯色（与图表场景保持一致）
    style = content.get('style', {})
    background = style.get('background', {})
    if background.get('type') == 'gradient':
        bg_color = background.get('colors', ['#0f1419'])[0]
    elif background.get('type') == 'solid':
        bg_color = background.get('color', '#0f1419')
    else:
        # 如果没有 background 配置，尝试从 style 获取（向后兼容）
        bg_color = style.get('background_color', '#0f1419')
    
    # 文字颜色配置
    text_color = style.get('text_color', '#ffffff')
    subtitle_color = style.get('subtitle_color', '#e0e0e0')
    
    # 场景时间范围
    time_range = scene_data.get('time_range', [0, 3])
    duration = time_range[1] - time_range[0]
    
    prompt = f"""
You are creating a CLOSING SCENE for a data video.

**VIDEO CONTEXT:**
- Video Title: "{video_meta.get('title', 'Data Insights')}"
- Scene {scene_index} of {total_scenes}
- Duration: {duration} seconds

**SCENE CONTENT:**
- Main Title: "{title}"
- Narration: "{narration_text}"

**DESIGN REQUIREMENTS:**

1. **Background**: 
   - Use gradient background (often reversed from opening)
   - Colors: {bg_color}
   
2. **Layout**:
   - Centered title
   - Title: Large, bold (font-size: 56-72px)
   - Optional: Small tagline or summary text below title (font-size: 20-24px)

3. **Colors**:
   - Title color: {text_color}
   - Secondary text color: {subtitle_color}
   
4. **Typography**:
   - Use modern sans-serif font (e.g., 'Inter', 'Helvetica', 'Arial')
   - Title: font-weight 700-900
   - Secondary text: font-weight 400-500

5. **NO ANIMATIONS** in this static version
   - Animations will be added later by a separate script
   - All elements should be at full opacity
   - All elements at final positions

6. **Subtitle/Narration Space**:
   - Reserve BOTTOM 80px for narration subtitles (will be added in animation phase)
   - Adjust content positioning to avoid overlap with subtitle area
   - Keep main content in upper area

**OUTPUT REQUIREMENTS:**

Generate a complete TSX component (React + TypeScript + Remotion):

```tsx
import React from 'react';
import {{ AbsoluteFill }} from 'remotion';

interface SceneProps {{
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{{text: string; time_start: number; time_end: number}}>; // Narration subtitles (will be used in animation version)
}}

export const [ComponentName]: React.FC<SceneProps> = ({{ sceneStartOffset = 0 }}) => {{
  return (
    <AbsoluteFill
      style={{{{
        background: '{bg_color}',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 80px 80px 80px', // 底部80px padding for subtitles
      }}}}
    >
      {{/* Main Title */}}
      <div
        style={{{{
          fontSize: 64,
          fontWeight: 800,
          color: '{text_color}',
          textAlign: 'center',
          marginBottom: 20,
          maxWidth: '80%',
          lineHeight: 1.2,
        }}}}
      >
        {title}
      </div>

      {{/* Optional summary text */}}
      <div
        style={{{{
          fontSize: 22,
          fontWeight: 400,
          color: '{subtitle_color}',
          textAlign: 'center',
          maxWidth: '70%',
          lineHeight: 1.6,
          opacity: 0.9,
        }}}}
      >
        Data-driven insights for better decisions
      </div>
    </AbsoluteFill>
  );
}};
```

**CRITICAL**:
- Replace [ComponentName] with the actual component name
- Keep the structure clean and simple
- Ensure all styles are inline for easy animation later
- DO NOT add any animation logic
- All elements should be visible and at final positions

Return ONLY the complete TSX code, no explanation.
"""
    
    return prompt


def create_stat_cards_scene_prompt(scene_data, video_meta, component_name, scene_index=1, total_scenes=1):
    """创建 Stat Cards 场景的 Prompt"""
    content = scene_data.get('content', {})
    cards = content.get('cards', [])
    narration = scene_data.get('narration', [])
    narration_text = ' '.join([n.get('text', '') for n in narration])
    
    # 提取标题
    title = content.get('title', '')
    
    # 背景色配置 - 统一使用纯色（与图表场景保持一致）
    style = content.get('style', {})
    background = style.get('background', {})
    bg_color = background.get('colors', ['#0f1419'])[0] if background.get('type') == 'gradient' else '#0f1419'
    
    # 场景时间范围
    time_range = scene_data.get('time_range', [0, 4])
    duration = time_range[1] - time_range[0]
    
    # 构建卡片信息
    cards_info = []
    for i, card in enumerate(cards, 1):
        cards_info.append(f"Card {i}: {card.get('number', 'N/A')} - {card.get('label', 'Label')} (color: {card.get('color', '#5b8ff9')})")
    cards_str = '\n'.join(cards_info)
    
    # 生成卡片数据的JSON字符串
    cards_json = json.dumps(cards, indent=2, ensure_ascii=False)
    
    prompt = f"""
You are creating a STAT CARDS SCENE for a data video.

**VIDEO CONTEXT:**
- Video Title: "{video_meta.get('title', 'Data Insights')}"
- Scene {scene_index} of {total_scenes}
- Duration: {duration} seconds

**SCENE CONTENT:**
- Title: "{title}"  # 场景标题（如果提供）
- Number of Cards: {len(cards)}
- Cards Data:
{cards_str}
- Narration: "{narration_text}"

**DESIGN REQUIREMENTS:**

1. **Background**: 
   - Use gradient background
   - Colors: {bg_color}
   
2. **Layout**:
   - Cards arranged horizontally in a SINGLE ROW (flexbox row)
   - **CRITICAL: All cards MUST stay on ONE line, never wrap**
   - Use `flexWrap: 'nowrap'` to prevent wrapping
   - Use `flex: '1 1 0%'` for each card to ensure equal width distribution
   - Set `width: 0` on cards to allow flexbox to control width
   - Gap between cards: 20px (adjust based on number of cards)
   - Cards container: `width: '100%'`, `maxWidth: '1400px'`
   - Equal spacing between cards
   - Centered on screen
   - If title is provided, display it at the top (position: absolute, top: 80px)

3. **Card Design**:
   - Clean, modern card style
   - Border: 2px solid with card color
   - Background: Semi-transparent dark (#1a202c with 80% opacity)
   - Padding: 28px 20px (reduced to ensure cards fit in one row)
   - Border radius: 12px
   - Each card contains:
     * Large number (font-size: 52px, font-weight: 800)
     * Label below number (font-size: 15px, font-weight: 500, line-height: 1.3)
   - Label text should use `wordWrap: 'break-word'` and `overflowWrap: 'break-word'` to handle long text

4. **Colors**:
   - Number: Use card's color prop
   - Label: Light gray (#e0e0e0)
   - Border: Use card's color prop

5. **Typography**:
   - Use modern sans-serif font (e.g., 'Inter', 'Helvetica', 'Arial')
   - Number: font-weight 800
   - Label: font-weight 500

6. **NO ANIMATIONS** in this static version
   - Animations will be added later by a separate script
   - All cards should be at full opacity
   - All cards at final positions

7. **Subtitle Space**:
   - Reserve BOTTOM 130px for subtitles
   - Cards should be positioned in upper 590px area

**CARDS DATA:**
```json
{cards_json}
```

**OUTPUT REQUIREMENTS:**

Generate a complete TSX component (React + TypeScript + Remotion):

```tsx
import React from 'react';
import {{ AbsoluteFill }} from 'remotion';

interface StatCard {{
  number: string;
  label: string;
  color: string;
}}

interface SceneProps {{
  sceneStartOffset?: number; // Will be used later for animation timing
  narrations?: Array<{{text: string; time_start: number; time_end: number}}>; // Narration subtitles (will be used in animation version)
  title?: string; // Scene title (optional)
}}

export const [ComponentName]: React.FC<SceneProps> = ({{ sceneStartOffset = 0, title = "{title}" }}) => {{
  const cards: StatCard[] = {cards_json};

  return (
    <AbsoluteFill
      style={{{{
        background: '{bg_color}',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: "'Inter', 'Helvetica', 'Arial', sans-serif",
        padding: '0 60px 130px 60px', // Bottom padding for subtitles
      }}}}
    >
      {{/* Title - Display if provided */}}
      {{{{title && (
        <div
          style={{{{
            position: 'absolute',
            top: 80,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 10,
          }}}}
        >
          <h2
            style={{{{
              fontSize: 42,
              fontWeight: 700,
              color: '#ffffff',
              margin: 0,
              textAlign: 'center',
              letterSpacing: '0.5px',
            }}}}
          >
            {{{{title}}}}
          </h2>
        </div>
      )}}}}

      <div
        style={{{{
          display: 'flex',
          flexDirection: 'row',
          gap: 20,
          justifyContent: 'center',
          alignItems: 'center',
          width: '100%',
          maxWidth: '1400px',
          flexWrap: 'nowrap', // Prevent wrapping
          marginTop: title ? 60 : 0, // Add top margin if title exists
          padding: '0 40px',
          boxSizing: 'border-box',
        }}}}
      >
        {{{{cards.map((card, index) => (
          <div
            key={{{{index}}}}
            style={{{{
              background: 'rgba(26, 32, 44, 0.8)',
              border: `2px solid ${{card.color}}`,
              borderRadius: 12,
              padding: '28px 20px', // Reduced padding
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              flex: '1 1 0%', // Use flex for equal width distribution
              minWidth: 0, // Allow flex to shrink
              width: 0, // Let flexbox control width
              boxSizing: 'border-box',
            }}}}
          >
            {{/* Number */}}
            <div
              style={{{{
                fontSize: 52,
                fontWeight: 800,
                color: card.color,
                marginBottom: 12,
                lineHeight: 1,
              }}}}
            >
              {{card.number}}
            </div>

            {{/* Label */}}
            <div
              style={{{{
                fontSize: 15, // Reduced font size
                fontWeight: 500,
                color: '#e0e0e0',
                textAlign: 'center',
                lineHeight: 1.3, // Reduced line height
                wordWrap: 'break-word',
                overflowWrap: 'break-word',
                width: '100%',
                maxWidth: '100%',
              }}}}
            >
              {{card.label}}
            </div>
          </div>
        )))}}}}
      </div>
    </AbsoluteFill>
  );
}};
```

**CRITICAL**:
- Replace [ComponentName] with the actual component name
- **MUST include title in SceneProps interface and display it if provided**
- **MUST use flex layout with `flexWrap: 'nowrap'` to prevent card wrapping**
- **MUST use `flex: '1 1 0%'` and `width: 0` on cards for proper flex distribution**
- **MUST use `minWidth: 0` on cards to allow flexbox to shrink them if needed**
- Keep the structure clean and simple
- Ensure all styles are inline for easy animation later
- DO NOT add any animation logic
- All cards should be visible and at full opacity
- Reserve bottom 130px for subtitles

Return ONLY the complete TSX code, no explanation.
"""
    
    return prompt


def get_prompt_for_scene_type(scene_data, video_meta, component_name, scene_index, total_scenes):
    """根据场景类型选择对应的 Prompt 生成器"""
    scene_type = scene_data.get('type', '')
    
    if scene_type == 'opening':
        return create_opening_scene_prompt(scene_data, video_meta, component_name, scene_index, total_scenes)
    elif scene_type == 'closing':
        return create_closing_scene_prompt(scene_data, video_meta, component_name, scene_index, total_scenes)
    elif scene_type == 'stat_cards':
        return create_stat_cards_scene_prompt(scene_data, video_meta, component_name, scene_index, total_scenes)
    else:
        raise ValueError(f"不支持的场景类型: {scene_type}")


def generate_tsx_component(scene_data, video_meta, llm_client, output_file, verbose=False, scene_index=1, total_scenes=1):
    """生成单个 TSX 组件"""
    scene_id = scene_data.get('id', f'scene_{scene_index}')
    scene_type = scene_data.get('type', 'unknown')
    content = scene_data.get('content', {})
    title = content.get('title', 'Scene')
    
    # 生成组件名称（包含数据集名字）
    dataset_name = extract_dataset_name(video_meta)
    component_name = f"{dataset_name}_{''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())}Component"
    
    if verbose:
        print(f"🎬 场景 {scene_index}/{total_scenes}: {scene_id} (type: {scene_type})")
        print(f"   标题: {title}")
    
    try:
        # 生成 prompt
        prompt = get_prompt_for_scene_type(scene_data, video_meta, component_name, scene_index, total_scenes)
        
        # 调用 LLM
        if verbose:
            print(f"   📡 调用 Claude API...")
        
        response, usage = llm_client.call(prompt, temperature=0.7, max_tokens=settings.LLM_MAX_TOKENS)
        
        # 提取代码
        tsx_code = response.strip()
        if '```tsx' in tsx_code:
            tsx_code = tsx_code.split('```tsx')[1].split('```')[0].strip()
        elif '```typescript' in tsx_code:
            tsx_code = tsx_code.split('```typescript')[1].split('```')[0].strip()
        elif '```' in tsx_code:
            tsx_code = tsx_code.split('```')[1].split('```')[0].strip()
        
        # 强制替换组件名称（处理LLM可能不按指示的情况）
        # 查找 export const XXX: React.FC 并替换为正确的组件名
        import re
        tsx_code = re.sub(r'export const \w+:', f'export const {component_name}:', tsx_code)
        tsx_code = sanitize_tsx_for_browser(tsx_code)
        
        # 保存文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(tsx_code)
        
        if verbose:
            print(f"   ✅ 成功生成: {output_file}")
        
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
        import traceback
        error_detail = traceback.format_exc()
        print(f"\n❌ 生成失败 ({scene_id}):")
        print(f"   场景类型: {scene_type}")
        print(f"   错误: {str(e)}")
        print(f"   详细堆栈:\n{error_detail}")
        return False


def generate_single_scene_wrapper(scene, idx, total_scenes, video_meta, llm_client, output_dir, task_id=None, max_retries: int = 5):
    """包装函数用于并行执行，支持校验+重试"""
    scene_id = scene.get('id', f'scene_{idx}')
    scene_type = scene.get('type', 'unknown')
    content = scene.get('content', {})
    title = content.get('title', 'Scene')
    dataset_name = extract_dataset_name(video_meta)
    scene_id_camel = ''.join(word.capitalize() for word in scene_id.replace('_', ' ').split())
    if task_id:
        component_name = f"{dataset_name}_{scene_id_camel}_{task_id}Component"
    else:
        component_name = f"{dataset_name}_{scene_id_camel}Component"
    output_file = os.path.join(output_dir, f"{component_name}.tsx")
    
    last_error = None
    start_time = time.time()
    attempt = 0
    while True:
        attempt += 1
        elapsed = time.time() - start_time
        try:
            success = generate_tsx_component(
                scene, video_meta, llm_client, output_file,
                verbose=(attempt > 1), scene_index=idx, total_scenes=total_scenes
            )
            if success:
                retry_info = f" (重试 {attempt}次)" if attempt > 1 else ""
                return (idx, scene_id, True, f"✅ {scene_type}: {title}{retry_info}")
            last_error = "生成失败（返回 False）"
        except Exception as e:
            last_error = str(e)
        if attempt >= max_retries:
            should_retry, reason = False, f"已达到最大重试次数（{max_retries}次）"
        else:
            should_retry, reason = should_retry_on_error(last_error, attempt, elapsed, max_general_retries=max_retries)
        if should_retry:
            wait_time = calculate_retry_wait_time(last_error, attempt)
            print(f"   ⚠️  [{idx}/{total_scenes}] {scene_type}: {title} - 第 {attempt} 次失败，{wait_time}秒后重试...")
            time.sleep(wait_time)
            continue
        print(f"   ❌ [{idx}/{total_scenes}] {scene_type}: {title} - 停止重试: {reason}")
        break
    return (idx, scene_id, False, f"❌ {scene_type}: {title} - {last_error} (尝试 {attempt} 次后失败)")


def main():
    default_config_path = os.getenv(
        "VIDEO_DEFAULT_CONFIG_PATH",
        "infographic_generation/generated_config_aligned.json",
    )
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='生成其他场景的 TSX 组件（Opening/Closing/Stat Cards）')
    parser.add_argument('-w', '--workers', type=int, default=5, help='并行线程数（默认5）')
    parser.add_argument('--config', type=str, 
                       default=default_config_path,
                       help='配置文件路径')
    parser.add_argument('--output', type=str,
                       default=DEFAULT_COMPONENTS_OUTPUT_DIR,
                       help='输出目录（基础路径）')
    parser.add_argument('--task-id', type=str, default=None,
                       help='任务ID（用于创建子目录隔离组件）')
    args = parser.parse_args()
    
    # 如果提供了 task_id，则创建子目录
    if args.task_id:
        output_dir = os.path.join(args.output, args.task_id)
        print(f"📁 使用任务子目录: {output_dir}")
    else:
        output_dir = args.output
        print(f"📁 使用默认输出目录: {output_dir}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    start_time = time.time()
    
    # 读取配置文件
    with open(args.config, 'r', encoding='utf-8') as f:
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
    
    # 过滤其他场景（opening, closing, stat_cards）
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
    print(f"⚡ 使用并行模式生成（{args.workers} 个线程）...\n")
    results = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # 提交所有任务
        future_to_scene = {
            executor.submit(
                generate_single_scene_wrapper,
                scene,
                idx,
                len(other_scenes),
                video_meta,
                llm_client,
                output_dir,
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
    print("🎉 生成完成！")
    print(f"✅ 成功: {success_count}/{len(other_scenes)}")
    print(f"⏱️  总耗时: {elapsed:.1f}秒")
    print(f"📂 输出目录: {output_dir}")
    print("="*70)


if __name__ == '__main__':
    main()
