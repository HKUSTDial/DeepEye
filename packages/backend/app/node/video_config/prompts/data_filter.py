"""
Data Filter Agent
Role: Filter and transform data based on sub-query requirements
"""

DATA_FILTER_PROMPT = """You are a data filtering specialist.

**Task**: Filter and prepare a focused dataset for a specific sub-query analysis.

**IMPORTANT**: All content must be in {language}.

**Input**:
- Sub-Query: {sub_query}
- Required Fields: {required_fields}
- Filter Criteria: {filter_criteria}
- Full Dataset Sample (first 20 records):
{data_sample}
- Dataset Size: {total_records} records

**Requirements**:
1. Identify which records from the full dataset are relevant to this sub-query
2. Apply filter_criteria if provided
3. Select only the required_fields (plus any fields needed for filtering)
4. Limit the result to a reasonable size (20-30 records max) for efficient processing
   - If filtering results in more records, select the most relevant ones
   - For comparisons: include top/bottom items
   - For trends: include all time points if reasonable, or sample evenly
   - For part_to_whole: include all categories or top N + "Others"

**Output Format** (JSON):
```json
{{
  "filtered_data": [
    {{"field1": "value1", "field2": "value2"}},
    {{"field1": "value2", "field2": "value3"}}
  ],
  "filter_applied": "Description of what filtering was applied",
  "record_count": 25
}}
```

**Examples**:

Example 1 - Filter by category:
Sub-Query: "Compare sales performance across different regions"
Required Fields: ["region", "sales"]
Filter Criteria: {{}}
Data Sample: [{{"region": "North", "sales": 1000, "product": "A"}}, {{"region": "South", "sales": 800, "product": "B"}}, ...]

Output:
```json
{{
  "filtered_data": [
    {{"region": "North", "sales": 1000}},
    {{"region": "South", "sales": 800}},
    {{"region": "East", "sales": 1200}},
    {{"region": "West", "sales": 950}}
  ],
  "filter_applied": "Selected all unique regions with aggregated sales data",
  "record_count": 4
}}
```

Example 2 - Filter with criteria:
Sub-Query: "Analyze high-value products"
Required Fields: ["product_name", "revenue"]
Filter Criteria: {{"revenue": "> 1000"}}
Data Sample: [{{"product_name": "A", "revenue": 500}}, {{"product_name": "B", "revenue": 1500}}, ...]

Output:
```json
{{
  "filtered_data": [
    {{"product_name": "B", "revenue": 1500}},
    {{"product_name": "C", "revenue": 2000}},
    {{"product_name": "D", "revenue": 1200}}
  ],
  "filter_applied": "Filtered products with revenue > 1000, selected top 3",
  "record_count": 3
}}
```

**Important Notes**:
- Only include fields specified in required_fields (plus any needed for filtering)
- Limit to 20-30 records maximum for efficiency
- If filter_criteria is empty, select the most relevant records
- For aggregation needs (e.g., sum by region), include aggregated data
- Always return valid JSON with filtered_data array

Now filter the data. Return ONLY the JSON, nothing else.
"""


def format_data_filter_prompt(
    sub_query: str,
    required_fields: list,
    filter_criteria: dict,
    data_sample: list,
    total_records: int,
    language: str = "English"
) -> str:
    """Format data filter prompt"""
    import json
    
    # Limit sample size
    sample = data_sample[:20] if len(data_sample) > 20 else data_sample
    data_str = json.dumps(sample, indent=2, ensure_ascii=False)
    
    return DATA_FILTER_PROMPT.format(
        language=language,
        sub_query=sub_query,
        required_fields=json.dumps(required_fields, ensure_ascii=False),
        filter_criteria=json.dumps(filter_criteria, ensure_ascii=False),
        data_sample=data_str,
        total_records=total_records
    )

