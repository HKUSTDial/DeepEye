"""
Opening/Closing Scene Generator
Role: Generate engaging opening and closing scenes based on actual generated content
"""

OPENING_CLOSING_GENERATOR_PROMPT = """You are a professional video scriptwriter specializing in data visualization videos.

**Task**: Generate compelling opening and closing scenes based on the actual scenes that have been generated.

**IMPORTANT**: All content (titles, narration text) must be in {language}.

**Input**:
- User Query: {query}
- Generated Scenes Summary:
{scenes_summary}
- Original Storyboard Reference:
  - Opening Title: {opening_title}
  - Opening Goal: {opening_goal}
  - Closing Title: {closing_title}
  - Closing Goal: {closing_goal}

**Your Task**:
Create natural, engaging opening and closing scenes that:
1. Match the actual content of the generated scenes
2. Are concise and professional
3. Preview (opening) or summarize (closing) the key insights

**Opening Scene Requirements**:
1. **Title**: SHORT and compelling (max 8-10 words)
   - Extract from the query or opening_title
   - Focus on the main topic
   - Example: "Flight Delay Analysis 2015" NOT "Analysis of flight delay statistics in 2015 including..."
2. **Subtitle**: Brief context (optional, 5-10 words)
   - Example: "Performance by Carrier and Destination"
3. **Narration**: 1 sentence (12-18 words) that:
   - Naturally introduces the topic
   - Previews what viewers will see
   - Is engaging and sets expectations
   - **Good examples**:
     - "Let's explore how flight delays vary across carriers and destinations in 2015."
     - "In 2015, flight delays showed distinct patterns across airlines and cities. Let's investigate."
   - **Bad examples** (too dry):
     - "Introduce the analysis of flight delay statistics in 2015."
     - "This video analyzes flight delays."

**Closing Scene Requirements**:
1. **Title**: "Thank You" or brief message (max 5 words)
2. **Narration**: 1 sentence (15-20 words) that:
   - Summarizes the KEY findings from actual scenes
   - Provides a natural conclusion
   - References specific insights discovered
   - **Good examples**:
     - "Our analysis reveals MQ carrier faces highest delays while Boston demonstrates best performance overall."
     - "The data shows clear variations: San Francisco experiences most delays, carriers differ significantly in performance."
   - **Bad examples** (too vague):
     - "Thank you for watching this analysis."
     - "We have completed the analysis of flight delays."

**Output Format** (JSON):
```json
{{
  "opening": {{
    "id": "scene_1",
    "type": "opening",
    "content": {{
      "title": "Flight Delay Analysis 2015",
      "subtitle": "Performance by Carrier and Destination",
      "background": {{
        "type": "gradient",
        "colors": ["#0f1419", "#1a2332"]
      }},
      "style": {{
        "text_color": "#ffffff",
        "subtitle_color": "#e0e0e0"
      }}
    }},
    "narration": [
      {{"text": "Let's explore how flight delays vary across carriers and destinations in 2015."}}
    ]
  }},
  "closing": {{
    "id": "scene_closing",
    "type": "closing",
    "content": {{
      "title": "Thank You",
      "subtitle": "Key Insights Summary",
      "background": {{
        "type": "gradient",
        "colors": ["#1a2332", "#0f1419"]
      }},
      "style": {{
        "text_color": "#ffffff",
        "subtitle_color": "#e0e0e0",
        "background": {{
          "type": "solid",
          "color": "#0f1419"
        }}
      }}
    }},
    "narration": [
      {{"text": "Our analysis reveals MQ carrier faces highest delays while Boston demonstrates best performance overall."}}
    ]
  }}
}}
```

**Critical Rules**:
1. ✅ Opening title MUST be SHORT (8-10 words max, NOT the entire query)
2. ✅ Opening narration MUST preview the content naturally (12-18 words)
3. ✅ Closing narration MUST reference SPECIFIC findings from the scenes (15-20 words)
4. ✅ Both narrations must be engaging, NOT dry task descriptions
5. ✅ Use the scenes_summary to understand what was actually generated
6. ✅ Match the language: {language}
7. ✅ Keep background colors consistent: "#0f1419" and "#1a2332"

**Examples**:

Example 1 - Flight Delays:
Scenes: Carrier comparison, City delays, Overall stats
Opening narration: "In 2015, flight delays varied significantly across carriers and destinations. Let's uncover the patterns."
Closing narration: "Key findings: MQ carrier shows highest delays, San Francisco faces most issues, while Boston performs best."

Example 2 - Sales Analysis:
Scenes: Regional sales, Product performance, Quarterly trends
Opening narration: "Sales performance in 2024 reveals interesting patterns across regions and products. Let's dive in."
Closing narration: "Our analysis shows North region leads with 45% growth, Product A dominates across all quarters."

Now generate the opening and closing scenes. Return ONLY the JSON, nothing else.
"""


def format_opening_closing_generator_prompt(
    query: str,
    scenes_summary: list,
    opening_title: str,
    opening_goal: str,
    closing_title: str,
    closing_goal: str,
    language: str = "English"
) -> str:
    """Format prompt for opening/closing generator"""
    import json
    
    # Format scenes summary
    scenes_summary_str = json.dumps(scenes_summary, indent=2, ensure_ascii=False)
    
    prompt = OPENING_CLOSING_GENERATOR_PROMPT.format(
        language=language,
        query=query,
        scenes_summary=scenes_summary_str,
        opening_title=opening_title or "Data Analysis",
        opening_goal=opening_goal or "Introduce the analysis",
        closing_title=closing_title or "Thank You",
        closing_goal=closing_goal or "Summarize key findings"
    )
    
    return prompt

