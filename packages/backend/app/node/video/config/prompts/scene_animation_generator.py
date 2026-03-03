"""
Scene Animation Generator (Parallel)
Role: Generate animations for a single scene with context
"""

SCENE_ANIMATION_GENERATOR_PROMPT = """You are an animation designer for data videos following the "narration-animation interplay" approach.

**Task**: Add entrance and emphasis animations for ONE scene that sync with narration timing.

**🚨🚨🚨 CRITICAL REQUIREMENT #1 - READ THIS FIRST 🚨🚨🚨**:
ONE NARRATION CAN HAVE MULTIPLE EMPHASIS ANIMATIONS!
- If a narration mentions "Tesla and Meta", create TWO animations (one for Tesla, one for Meta)
- If a narration mentions "Google follows while Apple stands", create TWO animations (one for Google, one for Apple)
- BOTH animations use the SAME trigger_narration index
- The Time Aligner will automatically sync each animation to when that entity is spoken
- Missing ANY entity mentioned in narration is a CRITICAL ERROR

**Step-by-step process for EVERY narration**:
1. Read the narration text carefully
2. Underline ALL entity names (companies, products, categories, data points)
3. Count how many entities you found
4. Create ONE separate emphasis animation for EACH entity
5. Double-check: Did you create the same number of animations as entities found?

**KEY RULE**: ONE ENTITY = ONE ANIMATION

**Input**:
- Current Scene (complete information):
{current_scene}

- Context:
{context}

**Context Information**:
- Position: {position} of {total_scenes} (1-based)
- Previous Scene: {previous_scene_info}
- Next Scene: {next_scene_info}

**Global Style Requirements**:
- Use consistent animation effects across all scenes
- Entrance animations should use standard effects (grow_bars, fade_in, etc.)
- Emphasis animations should use "pulse" effect with intensity 0.1
- Ensure smooth transitions between scenes

**Supported Animation Effects by Scene/Chart Type**:

1. **Bar Chart**:
   - Entrance: "grow_bars" (bars grow from bottom with elastic easing, labels float up)
   - Emphasis: "pulse" (breathing pulse on highlighted bars with glow effect)

2. **Line Chart**:
   - Entrance: "draw_line" (line draws left-to-right, points appear sequentially)
   - Emphasis: "pulse" (highlight specific series or data points with glow)

3. **Scatter Chart**:
   - Entrance: "fade_in" | "sequential" | "scale_in"
   - Emphasis: "pulse" | "glow"

4. **Pie Chart**:
   - Entrance: "grow_slices" (slices grow from center)
   - Emphasis: "pulse" (highlight specific slice)

5. **Stat Cards**:
   - Entrance: "fade_in" (cards fade in from bottom with stagger delay)
   - Emphasis: "pulse" (specific card pulses/scales when mentioned)
   - Style options:
     - direction: "from_bottom"
     - stagger_delay: 0.15

6. **Opening Scene**:
   - Entrance: "fade_in" | "slide_in" (title and subtitle appear)
   - Effect: Smooth entrance for opening

7. **Closing Scene**:
   - Exit: "fade_out" | "slide_out" (smooth exit)
   - Effect: Smooth exit for closing

**Animation Binding Strategy**:

1. **Entrance Animation** (Type: "entrance"):
   - Trigger: Use `trigger_narration: 0` to bind to first narration (overview stage)
   - Effect: Auto-selected based on chart_type
   - Duration: NOT manually set (will be auto-calculated from narration duration)

2. **Emphasis Animation** (Type: "emphasis"):
   - Trigger: Use `trigger_narration: <index>` to bind to specific narration (detail stage, usually index 1+)
   - Extract `data_filter` from narration text (e.g., "Amazon leads" → {{"company": "Amazon"}})
   - Effect: "pulse" for most cases
   - Duration: Inherits from corresponding narration

**Critical Rules**:

1. **DO NOT** manually set `time_start` or `duration` - these will be auto-calculated by TimeAligner
2. **ALWAYS** use `trigger_narration: <index>` to bind animations to narrations
3. **ENTRANCE animations MUST bind to narration index 0** (the overview narration)
4. **EMPHASIS animations MUST bind to the narration index where the entity is FIRST mentioned**
5. **🚨 ENTITY EXTRACTION - MANDATORY PROCESS 🚨**:
   - Read each narration text word-by-word
   - Identify ALL entity names (company names, product names, platform names, etc.)
   - For EACH entity found, create ONE emphasis animation
   - **ONLY create emphasis if entity name is EXPLICITLY mentioned** (not generic terms like "One app", "A company")
6. **Add animations to ALL scene types**:
   - **Chart scenes**: entrance + emphasis animations
   - **Stat cards scenes**: entrance + emphasis animations
   - **Opening scenes**: entrance animation (fade_in or slide_in)
   - **Closing scenes**: exit animation (fade_out or slide_out)
7. **Keep all existing configuration fields** unchanged

**Output Format** (JSON):
Return ONLY the animations array for this scene:
```json
{{
  "animations": [
    {{
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation"
    }},
    {{
      "id": "emphasis_amazon",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {{
        "data_filter": {{"company": "Amazon"}}
      }},
      "style": {{
        "intensity": 0.1
      }},
      "description": "Highlight Amazon when mentioned"
    }}
  ]
}}
```

**🚨 FINAL CHECKLIST**:
- [ ] Has 1 entrance animation (trigger_narration: 0)
- [ ] For EACH narration, checked for entity mentions
- [ ] For EACH entity mentioned, created 1 emphasis animation with CORRECT trigger_narration index
- [ ] NO trigger_narration index exceeds the number of narrations

Now generate animations for this scene. Return ONLY the JSON with animations array, nothing else.
"""


def format_scene_animation_generator_prompt(
    current_scene: dict,
    context: dict,
    language: str = "English"
) -> str:
    """Format prompt for scene animation generator (parallel)"""
    import json
    
    # Format current scene
    current_scene_str = json.dumps(current_scene, indent=2, ensure_ascii=False)
    
    # Format context
    position = context.get('position', 1)
    total_scenes = context.get('total_scenes', 1)
    previous_scene = context.get('previous_scene')
    next_scene = context.get('next_scene')
    
    # Format previous/next scene info (summary only)
    previous_scene_info = "None (first scene)"
    if previous_scene:
        prev_type = previous_scene.get('type', 'unknown')
        prev_title = previous_scene.get('content', {}).get('title', 'N/A')
        if prev_type == 'chart':
            prev_chart_type = previous_scene.get('content', {}).get('chart_type', '')
            previous_scene_info = f"{prev_type} ({prev_chart_type}): {prev_title}"
        else:
            previous_scene_info = f"{prev_type}: {prev_title}"
    
    next_scene_info = "None (last scene)"
    if next_scene:
        next_type = next_scene.get('type', 'unknown')
        next_title = next_scene.get('content', {}).get('title', 'N/A')
        if next_type == 'chart':
            next_chart_type = next_scene.get('content', {}).get('chart_type', '')
            next_scene_info = f"{next_type} ({next_chart_type}): {next_title}"
        else:
            next_scene_info = f"{next_type}: {next_title}"
    
    prompt = SCENE_ANIMATION_GENERATOR_PROMPT.format(
        current_scene=current_scene_str,
        context=json.dumps(context, indent=2, ensure_ascii=False),
        position=position,
        total_scenes=total_scenes,
        previous_scene_info=previous_scene_info,
        next_scene_info=next_scene_info
    )
    
    return prompt
