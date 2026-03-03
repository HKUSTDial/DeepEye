"""
Data Transform Planner Direct Agent
Role: Analyze original query directly and determine what data transformations are needed for multiple scenes
Used for ablation study: w/o Decomposition
"""

DATA_TRANSFORM_PLANNER_DIRECT_PROMPT = """You are a data transformation planner.

**Task**: Analyze the ORIGINAL user query and determine what data transformations are needed to create multiple visualization scenes. Unlike the normal flow, you are working DIRECTLY from the original query without any prior scene decomposition.

**IMPORTANT**: All content must be in {language}.

**Input**:
- Original User Query: {query}
- Dataset Metadata:
{metadata}

**🎯 CRITICAL - Your Responsibility**:
1. **Analyze the original query** to understand what analyses are needed
2. **Determine how many distinct analysis perspectives** are needed to answer the query comprehensively (you decide the number)
3. **For each analysis perspective**, determine the appropriate data transformation

**Key Differences from Normal Flow**:
- ❌ NO scene plans provided - you must identify what analyses are needed from the query
- ✅ Work directly from the original query
- ✅ Generate transformation plans for as many scenes as needed to comprehensively answer the query
- ✅ Each scene should represent a distinct analysis angle

**Analysis Perspective Guidelines**:
- **Completeness**: Cover the main aspects mentioned in the query
- **Non-redundancy**: Avoid scenes that analyze the same data from nearly identical angles

**Transformation Types** (same as normal flow):
- **group_by_aggregate**: Group by categorical field(s), aggregate numerical fields (for comparisons, distributions)
- **time_series_aggregate**: Group by time field, aggregate over time periods (for trends)
- **filter_and_select**: Filter records and select specific fields (for specific analysis)
- **top_n**: Select top/bottom N records by a field (for find_extremum)
- **correlation_data**: Prepare data pairs for correlation analysis (for correlation)
- **sample_representative**: Sample representative records (for outlier detection or general analysis)

**🚨 CRITICAL CONSTRAINT - Use Only Existing Fields**:
- You can ONLY use fields that exist in the dataset metadata provided above
- DO NOT create, derive, or reference new fields that don't exist in the data
- Check the metadata carefully before using any field

**Filter Guidelines**:
- Extract scope filters from the query (location, category, time range)
- Add quality filters only if necessary (e.g., exclude nulls for aggregation)
- Keep filters minimal - only what's necessary
- Use actual values from metadata/sample data, NOT placeholders

**Output Format** (JSON):
```json
{{
  "scenes": [
    {{
      "scene_id": "scene_1",
      "description": "Brief description of what this scene analyzes",
      "analysis_type": "comparison|trend|distribution|correlation|find_extremum|summary",
      "transformation_type": "group_by_aggregate|time_series_aggregate|filter_and_select|top_n|correlation_data|sample_representative",
      "group_by_fields": ["field1"],
      "aggregate_fields": {{
        "field2": "avg",
        "field3": "sum"
      }},
      "time_field": "date",
      "time_grouping": "month",
      "x_field": "field1",
      "y_field": "field2",
      "derived_fields": {{
        "new_field": "field1 / field2"
      }},
      "filter": {{
        "field": "value",
        "field2": "not null"
      }},
      "select_fields": ["field1", "field2"],
      "sort_by": "avg_field2",
      "sort_order": "desc",
      "limit": 10,
      "sample_size": 20,
      "required_fields": ["field1", "field2"]
    }}
  ]
}}
```

**Example**:

Query: "Compare flight delays across carriers and destinations in 2015"

Output:
```json
{{
  "scenes": [
    {{
      "scene_id": "scene_1",
      "description": "Compare average delay performance across different carriers",
      "analysis_type": "comparison",
      "transformation_type": "group_by_aggregate",
      "group_by_fields": ["carrier"],
      "aggregate_fields": {{
        "depdelay": "avg",
        "arrdelay": "avg"
      }},
      "filter": {{
        "depdelay": "not null",
        "arrdelay": "not null"
      }},
      "sort_by": "avg_depdelay",
      "sort_order": "desc",
      "required_fields": ["carrier", "depdelay", "arrdelay"]
    }},
    {{
      "scene_id": "scene_2",
      "description": "Compare average delay performance across destination cities",
      "analysis_type": "distribution",
      "transformation_type": "group_by_aggregate",
      "group_by_fields": ["destcity"],
      "aggregate_fields": {{
        "arrdelay": "avg"
      }},
      "filter": {{
        "arrdelay": "not null",
        "destcity": "not null"
      }},
      "sort_by": "avg_arrdelay",
      "sort_order": "desc",
      "limit": 10,
      "required_fields": ["destcity", "arrdelay"]
    }}
  ]
}}
```

**Critical Rules**:
1. ✅ Generate as many scenes as needed to comprehensively answer the query (you decide the number)
2. ✅ Each scene should have a distinct analysis perspective
3. ✅ Use only fields that exist in the metadata
4. ✅ Include required_fields for each scene
5. ✅ Keep filters minimal and necessary
6. ✅ Use actual values, not placeholders
7. ❌ Do NOT create derived fields that don't exist

Now analyze the query and generate transformation plans for multiple scenes. Return ONLY the JSON, nothing else.
"""


def format_data_transform_planner_direct_prompt(
    query: str,
    metadata: dict,
    language: str = "English"
) -> str:
    """Format prompt for direct data transform planner (w/o Decomposition)
    
    Args:
        query: Original user query
        metadata: Dataset metadata (same as normal flow)
        language: Output language
    
    Note: Only metadata is passed, no sample data (consistent with normal flow)
    """
    import json
    
    # Format metadata (same as normal flow)
    metadata_str = json.dumps(metadata, indent=2, ensure_ascii=False)
    
    prompt = DATA_TRANSFORM_PLANNER_DIRECT_PROMPT.format(
        language=language,
        query=query,
        metadata=metadata_str
    )
    
    return prompt
