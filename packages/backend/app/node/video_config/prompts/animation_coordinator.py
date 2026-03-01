"""
Animation Coordinator Agent
Role: Add appropriate animations to each scene based on TTS-aligned narration timing
"""

ANIMATION_COORDINATOR_PROMPT = """You are an animation designer for data videos following the "narration-animation interplay" approach.

**Task**: Add entrance and emphasis animations that sync with narration timing.

**🚨🚨🚨 CRITICAL REQUIREMENT #1 - READ THIS FIRST 🚨🚨🚨**:
ONE NARRATION CAN HAVE MULTIPLE EMPHASIS ANIMATIONS!
- If a narration mentions "Tesla and Meta", create TWO animations (one for Tesla, one for Meta)
- If a narration mentions "Google follows while Apple stands", create TWO animations (one for Google, one for Apple)
- BOTH animations use the SAME trigger_narration index
- The Time Aligner will automatically sync each animation to when that entity is spoken
- Missing ANY entity mentioned in narration is a CRITICAL ERROR that will be flagged in quality evaluation

**Step-by-step process for EVERY narration**:
1. Read the narration text carefully
2. Underline ALL entity names (companies, products, categories, data points)
3. Count how many entities you found
4. Create ONE separate emphasis animation for EACH entity
5. Double-check: Did you create the same number of animations as entities found?

**KEY RULE**: ONE ENTITY = ONE ANIMATION
Example: "Tesla grew 18.8% while Meta reached 16.3%"
→ Tesla is an entity → Create emphasis_tesla (trigger_narration: X)
→ Meta is an entity → Create emphasis_meta (trigger_narration: X, same index!)
→ Result: TWO animations with the SAME trigger_narration index
→ The Time Aligner will automatically sync each to when that entity is spoken

**Input Configuration** (already aligned with TTS audio timestamps):
{config}

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
   - Exit: "fade_out" | "scale_out"

4. **Pie Chart**:
   - Entrance: "grow_slices" (slices grow from center)
   - Emphasis: "pulse" (highlight specific slice)

5. **Stat Cards**:
   - Entrance: "fade_in" (cards fade in from bottom with stagger delay)
   - Emphasis: "pulse" (specific card pulses/scales when mentioned)
   - Style options:
     - direction: "from_bottom" (slide up effect)
     - stagger_delay: 0.15 (delay between cards, in seconds)
   - **🚨 CRITICAL**: Animation duration MUST be shorter than scene duration
     - If scene duration is 3 seconds, animation duration should be ≤ 2.5 seconds
     - Calculate: animation_duration = scene_duration - 0.5 (leave buffer for smooth transition)

**Animation Binding Strategy** (following Data Player paper):

1. **Entrance Animation** (Type: "entrance"):
   - Trigger: Use `trigger_narration: 0` to bind to first narration (overview stage)
   - Effect: Auto-selected based on chart_type
   - Duration: NOT manually set (will be auto-calculated from narration duration)
   - The TimeAligner will automatically set time_start and duration
   - **Important**: Entrance animations should bind to the overview narration (index 0), NOT to detail narrations

2. **Emphasis Animation** (Type: "emphasis"):
   - Trigger: Use `trigger_narration: <index>` to bind to specific narration (detail stage, usually index 1+)
   - Extract `data_filter` from narration text (e.g., "Amazon leads" → {{"company": "Amazon"}})
   - Effect: "pulse" for most cases
   - Duration: Inherits from corresponding narration
   - **Important**: Emphasis animations should bind to detail narrations (index 1+), NOT to overview narration (index 0)
   
   - **🚨 MULTIPLE ENTITIES = MULTIPLE ANIMATIONS (COMMON MISTAKES)**:
     
     ❌ WRONG Example 1:
     Narration: "Tesla and Meta are mentioned"
     → Only creates: emphasis_tesla
     ✅ CORRECT: Create TWO animations (emphasis_tesla AND emphasis_meta)
     
     ❌ WRONG Example 2:
     Narration: "Google follows with 307.4 billion, while Apple stands at 394.3 billion"
     → Only creates: emphasis_google
     ✅ CORRECT: Create TWO animations:
         {{"id": "emphasis_google", "trigger_narration": 2, "data_filter": {{"company": "Google"}}}}
         {{"id": "emphasis_apple", "trigger_narration": 2, "data_filter": {{"company": "Apple"}}}}
     
     ❌ WRONG Example 3:
     Narration: "Amazon leads, followed by Google and Apple"
     → Only creates: emphasis_amazon
     ✅ CORRECT: Create THREE animations (emphasis_amazon, emphasis_google, emphasis_apple)
     
     **Key Point**: All animations for the same narration use the SAME trigger_narration index.
     The Time Aligner will automatically sync each animation to when that specific entity is spoken.

**Output Format**:

For each chart scene, add animations like this (NO time_start or duration fields):

**Example 1: Chart with overview + 2 details**
```json
{{
  "narration": [
    {{"text": "Let's look at the sales comparison"}},
    {{"text": "TikTok leads with 850 sales"}},
    {{"text": "Twitter shows the lowest at 180"}}
  ],
  "animations": [
    {{
      "id": "entrance_anim",
      "type": "entrance",
      "effect": "grow_bars",
      "trigger_narration": 0,
      "description": "Chart entrance animation synced with overview"
    }},
    {{
      "id": "emphasis_tiktok",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 1,
      "target_data": {{
        "data_filter": {{"platform": "TikTok"}}
      }},
      "style": {{
        "intensity": 0.1
      }},
      "description": "Highlight TikTok when mentioned in detail"
    }},
    {{
      "id": "emphasis_twitter",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 2,
      "target_data": {{
        "data_filter": {{"platform": "Twitter"}}
      }},
      "style": {{
        "intensity": 0.1
      }},
      "description": "Highlight Twitter when mentioned"
    }}
  ]
}}
```

**Example 2: Multiple entities in ONE narration (create SEPARATE animations for EACH entity)**
```json
{{
  "narration": [
    {{"text": "Let's examine the revenue figures"}},
    {{"text": "Amazon leads with 574.8 billion dollars"}},
    {{"text": "Google follows with 307.4 billion dollars, while Apple stands at 394.3 billion"}}
  ],
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
    }},
    {{
      "id": "emphasis_google",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 2,
      "target_data": {{
        "data_filter": {{"company": "Google"}}
      }},
      "style": {{
        "intensity": 0.1
      }},
      "description": "Highlight Google (first entity in narration 2)"
    }},
    {{
      "id": "emphasis_apple",
      "type": "emphasis",
      "effect": "pulse",
      "trigger_narration": 2,
      "target_data": {{
        "data_filter": {{"company": "Apple"}}
      }},
      "style": {{
        "intensity": 0.1
      }},
      "description": "Highlight Apple (second entity in narration 2)"
    }}
  ]
}}
```
**Note**: In this example, narration 2 mentions TWO entities (Google and Apple). The Time Aligner will automatically use word-level timestamps to start the Google animation when "Google" is spoken (around 0.05s), and the Apple animation when "Apple" is spoken (around 4.4s). Both animations will have the same trigger_narration index (2), but different time_start values after alignment.

**Critical Rules**:

1. **DO NOT** manually set `time_start` or `duration` - these will be auto-calculated by TimeAligner
2. **ALWAYS** use `trigger_narration: <index>` to bind animations to narrations
3. **ENTRANCE animations MUST bind to narration index 0** (the overview narration)
4. **EMPHASIS animations MUST bind to the narration index where the entity is FIRST mentioned**:
   - If Narration 0 mentions "Amazon leads...", create emphasis animation with trigger_narration: 0
   - If Narration 1 mentions "Apple follows...", create emphasis animation with trigger_narration: 1
   - **CRITICAL**: The trigger_narration index MUST match the narration index where the entity is mentioned

5. **🚨 ENTITY EXTRACTION - MANDATORY PROCESS 🚨**:
   Before creating animations, you MUST follow this checklist for EVERY narration (including index 0):
   
   **Checklist for Each Narration:**
   a) Read the narration text word-by-word
   b) Identify ALL entity names (company names, product names, platform names, category names, etc.)
   c) Check the scene's data to find the correct field name (e.g., "company", "platform", "product")
   d) For EACH entity found, create ONE emphasis animation with:
      - trigger_narration: <index of THIS narration>
      - data_filter: {{"<field_name>": "<entity_name>"}}
   
   **🚨 CRITICAL - MATCHING RULE 🚨**:
   - If Narration 0 says "Amazon leads...", create emphasis with trigger_narration: 0, data_filter: {{"company": "Amazon"}}
   - If Narration 1 says "Apple follows...", create emphasis with trigger_narration: 1, data_filter: {{"company": "Apple"}}
   - **DO NOT** create emphasis for "Amazon" with trigger_narration: 1 if Narration 1 says "Apple"!
   - **DO NOT** create emphasis with trigger_narration index that exceeds the number of narrations!
   
   **🚨 CRITICAL - ENTITY NAME MUST BE EXPLICITLY MENTIONED 🚨**:
   - **ONLY create emphasis animation if the entity name is EXPLICITLY mentioned in the narration text**
   - **DO NOT** create emphasis animation just because:
     * The scene has only one data point
     * The narration mentions a value (e.g., "4.8 rating") but not the entity name
     * The narration uses generic terms like "One app", "An app", "A company", "The app" instead of specific names
     * You assume the narration is talking about a specific entity without explicit mention
     * The data matches the values mentioned in narration (e.g., "One app has 215,644 reviews" matches "App C" in data)
   
   **Examples of CORRECT behavior**:
   - "Amazon leads" → Entity "Amazon" is mentioned → ✅ Create animation
   - "Tesla的增长率为18.8%" → Entity "Tesla" is mentioned → ✅ Create animation
   - "A high rating of 4.8 is possible" → NO entity name mentioned → ❌ DO NOT create animation (even if data has only one app)
   - "The app has a rating of 4.8" → NO entity name mentioned → ❌ DO NOT create animation
   - "One app has 215,644 reviews" → NO entity name mentioned (uses generic "One app") → ❌ DO NOT create animation (even if data shows "App C" has these values)
   - "An app with 50 million installs" → NO entity name mentioned (uses generic "An app") → ❌ DO NOT create animation
   - "App E achieves 4.8 rating" → Entity "App E" is mentioned → ✅ Create animation
   
   **Examples**:
   - "Amazon leads" → 1 entity → 1 animation → {{"company": "Amazon"}}
   - "Tesla的增长率为18.8%" → 1 entity → 1 animation → {{"company": "Tesla"}}
   - "Tesla and Meta are mentioned" → 2 entities → 2 animations → {{"company": "Tesla"}}, {{"company": "Meta"}}
   - "Google follows with X, while Apple stands at Y" → 2 entities → 2 animations → {{"company": "Google"}}, {{"company": "Apple"}}
   - "TikTok leads with 850, ahead of Instagram at 620" → 2 entities → 2 animations → {{"platform": "TikTok"}}, {{"platform": "Instagram"}}
   
   **Common Field Names** (check the actual data to confirm):
   - company, platform, product, category, region, country, name, etc.

6. **Add animations to "chart" and "stat_cards" scenes** (skip opening/closing unless specifically needed)
7. **For stat_cards scenes**:
   - Add entrance animation with target="cards", effect="fade_in"
   - Add emphasis animation with target="card", effect="pulse", and target_data.card_index
8. **Keep all existing configuration fields** unchanged

**Example Analysis**:

**Example 1: Chart Scene with overview + details**
- Narration 0 (Overview): "Let's examine the revenue comparison"
  → Entrance animation: trigger_narration: 0, effect: "grow_bars"
  → NO emphasis animation (no specific entity mentioned)
  
- Narration 1 (Detail): "Amazon leads with 574.8 billion dollars"
  → Emphasis animation: trigger_narration: 1, data_filter: {{"company": "Amazon"}}
  
- Narration 2 (Detail): "Microsoft follows with 211.9 billion"
  → Emphasis animation: trigger_narration: 2, data_filter: {{"company": "Microsoft"}}

**Example 2: Chart Scene where Narration 0 mentions specific entity**
- Narration 0: "Amazon leads the revenue charts in 2024, generating $620.1 billion"
  → Entrance animation: trigger_narration: 0, effect: "grow_bars"
  → Emphasis animation: trigger_narration: 0, data_filter: {{"company": "Amazon"}}
  → **CRITICAL**: Since "Amazon" is mentioned in Narration 0, the emphasis animation MUST use trigger_narration: 0

**Example 3: Chart Scene with only value mention (NO entity name) - DO NOT create emphasis**
- Scene has 1 data point: {{"app": "App E", "rating": 4.8}}
- Narration 0: "A high rating of 4.8 is possible with a smaller user base."
  → Entrance animation: trigger_narration: 0, effect: "grow_bars"
  → **NO emphasis animation** → ❌ DO NOT create emphasis for "App E" because "App E" is NOT mentioned in the narration
  → **Reason**: The narration only mentions the value "4.8" but does NOT mention the entity name "App E"

**Example 4: Chart Scene with generic reference (NO specific entity name) - DO NOT create emphasis**
- Scene has multiple data points including {{"app": "App C", "reviews": 215644, "installs": 50000000}}
- Narration 2: "One app has 215,644 reviews and 50 million installs, showing this trend clearly."
  → Entrance animation: trigger_narration: 0, effect: "fade_in"
  → **NO emphasis animation for "App C"** → ❌ DO NOT create emphasis because "App C" is NOT mentioned in the narration
  → **Reason**: The narration uses generic term "One app" instead of the specific entity name "App C"
  → **Even though** the data shows "App C" matches these values, the narration does NOT explicitly mention "App C"
  → **Correct behavior**: Skip emphasis animation, or if you want to highlight, the narration should say "App C has 215,644 reviews..." instead
  
- Narration 1: "Apple follows with $385.6 billion, significantly behind Amazon"
  → Emphasis animation: trigger_narration: 1, data_filter: {{"company": "Apple"}}
  → **CRITICAL**: Since "Apple" is mentioned in Narration 1, the emphasis animation MUST use trigger_narration: 1
  → **Note**: Even though "Amazon" is also mentioned in Narration 1, DO NOT create another emphasis for Amazon with trigger_narration: 1, because Amazon was already highlighted in Narration 0

**Stat Cards Scene:**
If scene has 3 cards and narration mentions "增长率达到16.3%":
```json
{{
  "animations": [
    {{
      "id": "cards_entrance",
      "type": "entrance",
      "effect": "fade_in",
      "target": "cards",
      "trigger_narration": 0,
      "style": {{
        "direction": "from_bottom",
        "stagger_delay": 0.15
      }},
      "description": "Cards fade in from bottom with stagger"
    }},
    {{
      "id": "emphasize_growth_card",
      "type": "emphasis",
      "effect": "pulse",
      "target": "card",
      "trigger_narration": 0,
      "target_data": {{
        "card_index": 0
      }},
      "style": {{
        "intensity": 0.7
      }},
      "description": "Highlight growth rate card"
    }}
  ]
}}
```

---

**🚨 FINAL CHECKLIST BEFORE SUBMITTING YOUR RESPONSE 🚨**

Before you return the JSON, you MUST verify:

✅ **For EACH chart scene**:
   - [ ] Has 1 entrance animation (trigger_narration: 0)
   - [ ] For EACH narration (including index 0), you have checked for entity mentions
   - [ ] For EACH entity mentioned in EACH narration, you have created 1 emphasis animation with the CORRECT trigger_narration index

✅ **Entity Coverage Check**:
   Go through each narration one-by-one:
   - Narration 0: "..." → Entities: [___] → Animations created: [___] with trigger_narration: 0
   - Narration 1: "..." → Entities: [___] → Animations created: [___] with trigger_narration: 1
   - Narration 2: "..." → Entities: [___] → Animations created: [___] with trigger_narration: 2
   
   **CRITICAL VERIFICATION**:
   - For each emphasis animation, verify that the data_filter entity is actually mentioned in the narration at trigger_narration index
   - Verify that NO trigger_narration index exceeds the number of narrations (if you have 2 narrations, indices are 0 and 1, NOT 2!)

✅ **Common Mistakes to Avoid**:
   - [ ] Did you miss any entity in sentences with "and", "while", "whereas"?
   - [ ] Did you miss entities mentioned without explicit numbers (e.g., "Tesla's workforce")?
   - [ ] Did you check ALL narrations (including index 0)?
   - [ ] Did you match the trigger_narration index to the narration where the entity is mentioned?
   - [ ] Did you create trigger_narration index that exceeds the number of narrations?

If you answered "YES" to all checks above, proceed to return the complete JSON configuration.

---

Now add animations to the configuration. Return ONLY the complete JSON.
"""


def format_animation_coordinator_prompt(config: dict) -> str:
    """格式化动画编排提示词"""
    import json
    return ANIMATION_COORDINATOR_PROMPT.format(
        config=json.dumps(config, indent=2, ensure_ascii=False)
    )

