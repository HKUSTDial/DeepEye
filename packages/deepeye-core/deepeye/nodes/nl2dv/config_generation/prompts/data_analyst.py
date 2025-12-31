"""
Data Analyst Agent
Role: Analyze data and extract key insights
"""

DATA_ANALYST_PROMPT = """You are a professional data analyst.

**Task**: Analyze the provided data and extract 3-5 most valuable insights.

**IMPORTANT**: All content (insights, descriptions) must be in {language}.

**Input**:
- User Query: {query}
- Raw Data:
{data}

**Requirements**:
1. Deep analysis of data to find:
   - Trends (growth/decline)
   - Comparisons (highest/lowest)
   - Outliers (deviations from normal)
   - Correlations

2. Each insight must:
   - Include specific numbers (no vague descriptions)
   - Be visualizable with charts
   - Provide value to the user

3. Sort by importance (most important first)

**Output Format** (JSON):
```json
{{
  "insights": [
    {{
      "type": "comparison|trend|find_extremum|outlier|correlation",
      "content": "Specific insight description (must include numbers)",
      "importance": 0.0-1.0
    }}
  ]
}}
```

**Example**:
User Query: "Analyze tech company revenue"
Data: [{{"company": "Apple", "revenue": 383.3}}, {{"company": "Microsoft", "revenue": 211.9}}]

Output (in English):
```json
{{
  "insights": [
    {{
      "type": "find_extremum",
      "content": "Apple leads with revenue of $383.3B, 1.8x Microsoft's revenue",
      "importance": 1.0
    }},
    {{
      "type": "comparison",
      "content": "Revenue gap between the two companies is $171.4B",
      "importance": 0.8
    }}
  ]
}}
```

Now analyze the data. Return ONLY the JSON, nothing else.
"""


def format_data_analyst_prompt(query: str, data: list, language: str = "English") -> str:
    """Format data analyst prompt"""
    import json
    
    # Limit data size (avoid too long)
    data_sample = data[:50] if len(data) > 50 else data
    data_str = json.dumps(data_sample, indent=2, ensure_ascii=False)
    
    # Add data statistics
    data_info = f"\nDataset size: {len(data)} records"
    if len(data) > 50:
        data_info += f"\n(Only showing first 50 records)"
    
    return DATA_ANALYST_PROMPT.format(
        language=language,
        query=query,
        data=data_info + "\n" + data_str
    )

