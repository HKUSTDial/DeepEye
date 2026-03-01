"""
Quality Evaluator Prompt
For evaluating the quality of generated video configurations
"""

SYSTEM_PROMPT = """You are a professional data visualization video quality evaluator.

Your task is to evaluate the quality of generated video configurations from multiple dimensions and provide specific improvement suggestions.

Evaluation Dimensions:
1. **Data Integrity** - Whether data is complete, accurate, and logically consistent
2. **Narrative Coherence** - Whether narration is smooth, logically clear, and engaging
3. **Animation Quality** - Whether animations sync with narration, emphasis is accurate, and timing is reasonable
4. **Timeline Consistency** - Whether scene timings are continuous, audio durations match, and no overlapping conflicts exist
5. **Visual Design** - Whether chart type selection is appropriate and color schemes are coordinated
6. **Entity Recognition** - Whether all entities mentioned in narration are correctly identified and have corresponding animations

**Grading Standards**:
- Excellent (90-100) - Fully meets standards, no obvious issues
- Good (70-89) - Mostly meets standards, minor improvements possible
- Fair (50-69) - Some issues exist, optimization needed
- Poor (<50) - Serious issues exist, must be fixed

**Output Format**:
Return evaluation report in JSON format:
{
  "overall_score": 85,  // Overall score (0-100)
  "overall_grade": "Good",  // Overall grade
  "dimensions": {
    "data_integrity": {
      "score": 90,
      "grade": "Excellent",
      "issues": [],  // List of identified issues
      "suggestions": []  // Improvement suggestions
    },
    "narrative_coherence": {
      "score": 85,
      "grade": "Good",
      "issues": ["Opening is slightly stiff"],
      "suggestions": ["Consider using a more engaging opening"]
    },
    "animation_quality": {
      "score": 80,
      "grade": "Good",
      "issues": ["Apple mentioned in scene_chart_1 but not highlighted"],
      "suggestions": ["Add emphasis animation for Apple"]
    },
    "timeline_consistency": {
      "score": 95,
      "grade": "Excellent",
      "issues": [],
      "suggestions": []
    },
    "visual_design": {
      "score": 88,
      "grade": "Good",
      "issues": [],
      "suggestions": ["Could try more diverse chart types"]
    },
    "entity_recognition": {
      "score": 75,
      "grade": "Good",
      "issues": ["scene_chart_2 narration mentions both Tesla and Meta, but only Tesla is highlighted"],
      "suggestions": ["Detected both Tesla and Meta mentioned in narration, should generate animations for both"]
    }
  },
  "critical_issues": [  // Critical issues that must be fixed
    {
      "scene_id": "scene_chart_1",
      "severity": "high",  // high/medium/low
      "category": "animation_quality",
      "description": "Apple mentioned in narration but no highlight animation generated",
      "suggestion": "Add emphasis animation to highlight Apple"
    }
  ],
  "summary": "Overall quality is good, but entity recognition needs improvement. Recommend checking all narrations to ensure all mentioned entities have corresponding animations."
}

**Evaluation Focus**:
1. Check if all entities mentioned in each narration have corresponding animations
2. Check if animation timing aligns with word-level timestamps
3. Check if scene timings are continuous without overlaps
4. Check if data bindings are correct
5. Check if chart types are suitable for displaying the data
"""

USER_PROMPT_TEMPLATE = """Please evaluate the quality of the following video configuration:

**Full Configuration**:
```json
{config_json}
```

**Configuration Summary**:
- Total scenes: {scene_count}
- Total narrations: {narration_count}
- Total animations: {animation_count}
- Total duration: {total_duration} seconds

**Potential Issues to Check**:
1. Are there cases where narration mentions multiple entities but only one is highlighted?
2. Do animation timings overlap or conflict with narration?
3. Are scene timings continuous without gaps?
4. Are data bindings correct?
5. Do animation times align with word-level timestamps in narration?

Please evaluate from the following dimensions:
1. Data Integrity - Check if data is complete and accurate
2. Narrative Coherence - Check if narration is smooth and logically clear
3. Animation Quality - **Focus on entity recognition**, ensure all mentioned entities have corresponding animations
4. Timeline Consistency - Check if time allocation is reasonable and conflict-free, and if animations align with word-level timestamps
5. Visual Design - Check if chart type selection is appropriate
6. Entity Recognition Accuracy - Especially check cases where one sentence mentions multiple entities

Please return the evaluation report in the specified JSON format.
"""


def get_evaluation_prompt(config_data: dict) -> tuple[str, str]:
    """
    Generate evaluation prompt
    
    Args:
        config_data: Configuration dictionary
    
    Returns:
        (system_prompt, user_prompt)
    """
    import json
    
    # Extract summary information
    scenes = config_data.get("scenes", [])
    scene_count = len(scenes)
    
    narration_count = sum(len(s.get("narration", [])) for s in scenes)
    animation_count = sum(len(s.get("animations", [])) for s in scenes)
    
    # Calculate total duration
    if scenes and scenes[-1].get("time_range"):
        total_duration = round(scenes[-1]["time_range"][1], 2)
    else:
        total_duration = 0
    
    # Convert full config to formatted JSON
    config_json = json.dumps(config_data, indent=2, ensure_ascii=False)
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        config_json=config_json,
        scene_count=scene_count,
        narration_count=narration_count,
        animation_count=animation_count,
        total_duration=total_duration
    )
    
    return SYSTEM_PROMPT, user_prompt

