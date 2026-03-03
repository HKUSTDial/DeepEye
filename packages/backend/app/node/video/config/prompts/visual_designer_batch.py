"""
Visual Designer Batch Agent
Role: Generate visualization configurations for multiple scenes at once
Used for ablation study: w/o Decomposition
"""

VISUAL_DESIGNER_BATCH_PROMPT = """You are a professional data visualization designer specializing in chart configuration.

**Task**: Generate visualization configurations for MULTIPLE scenes at once, based on the original query and transformed data for each scene.

**Input**:
- Original User Query: {query}
- Scenes with Transformed Data:
{scenes_data}

Each scene contains:
- scene_id: Unique identifier
- description: What this scene analyzes
- analysis_type: Type of analysis (comparison, trend, distribution, etc.)
- transformed_data: The processed data ready for visualization

**Your Task**:
For EACH scene, create a complete visualization configuration that effectively visualizes the provided data.

**Chart Selection**:
- comparison/magnitude → bar_chart (≥2 data points)
- trend/change_over_time → line_chart (≥3 time points)
- part_to_whole/proportion → pie_chart (≥2 categories)
- correlation/distribution → scatter_chart (≥3 data points)
- 2D distribution → heatmap (≥4 data points)

**Data Usage**:
- Use ONLY the provided transformed_data values - do not generate or estimate
- All numbers in your "data" array must match the provided data exactly
- Convert wide format to long format for bar_chart as needed

**DO NOT** write narration text. Instead, provide a brief "insight_summary" for each scene.

**Output Format** (JSON):
```json
{{
  "scenes": [
    {{
      "id": "scene_1",
      "type": "chart",
      "content": {{
        "chart_type": "bar_chart",
        "title": "Short, descriptive title",
        "data": [...],
        "data_binding": {{
          "x_axis": {{"field": "category", "label": "Category"}},
          "y_axis": {{"field": "value", "label": "Value"}}
        }},
        "style": {{
          "background_color": "#0f1419",
          "container_background": "#0f1419",
          "bar_color": "#5b8ff9",
          "text_color": "#e8eaed",
          "grid_color": "#2a3f5f",
          "axis_color": "#8c98a4"
        }},
        "layout": {{
          "margin": {{"top": 80, "right": 60, "bottom": 100, "left": 100}},
          "chart_area": {{"width": 1120, "height": 540}}
        }}
      }},
      "insight_summary": "Brief summary of what this chart shows (1-2 sentences)"
    }}
  ]
}}
```

**Requirements**:
- Generate visualization for ALL provided scenes
- Use exact data values from transformed_data
- Each scene must have complete configuration (chart_type, data, data_binding, style, layout)
- Use consistent background colors: "#0f1419"
- insight_summary should describe the KEY finding (1-2 sentences)
- DO NOT include "narration" or timing fields

Now generate visualization configurations for ALL scenes. Return ONLY the JSON, nothing else.
"""


def format_visual_designer_batch_prompt(
    query: str,
    scenes_data: list,
    language: str = "English"
) -> str:
    """Format prompt for batch visual designer (w/o Decomposition)
    
    Args:
        query: Original user query
        scenes_data: List of dicts, each containing:
            - scene_id: str
            - description: str
            - analysis_type: str
            - transformed_data: list of dicts (the processed data)
        language: Output language
    """
    import json
    
    # Format scenes data
    scenes_str = ""
    for i, scene in enumerate(scenes_data, 1):
        scene_id = scene.get('scene_id', f'scene_{i}')
        description = scene.get('description', 'N/A')
        analysis_type = scene.get('analysis_type', 'comparison')
        transformed_data = scene.get('transformed_data', [])
        
        # Limit data display (first 30 records per scene)
        data_display = transformed_data[:30] if len(transformed_data) > 30 else transformed_data
        data_str = json.dumps(data_display, indent=2, ensure_ascii=False)
        if len(transformed_data) > 30:
            data_str += f"\n... ({len(transformed_data)} total records, showing first 30)"
        
        scenes_str += f"""
Scene {i}:
- scene_id: {scene_id}
- description: {description}
- analysis_type: {analysis_type}
- transformed_data:
{data_str}
"""
    
    prompt = VISUAL_DESIGNER_BATCH_PROMPT.format(
        language=language,
        query=query,
        scenes_data=scenes_str
    )
    
    return prompt
