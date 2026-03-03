"""Prompts for Dashboard Designer

This module contains all LLM prompts used by the DashboardDesigner class.
"""

import json
from typing import Dict, Any


def build_layout_design_prompt(question: str, data_schema: Dict[str, Any]) -> str:
    """Build prompt for designing dashboard layout.
    
    Args:
        question: User's question
        data_schema: Data schema dictionary
    
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a professional dashboard designer. Please design an appropriate dashboard layout structure based on the user's question and data schema.

User Question: {question}

Data Schema:
{json.dumps(data_schema, ensure_ascii=False, indent=2)}

Please design a reasonable layout structure considering the following factors:
1. Choose an appropriate layout type based on the question type (grid, flex, tabs, etc.)
2. Determine a reasonable number of rows and columns
3. Consider the arrangement order and priority of components
4. Ensure the layout is aesthetically pleasing and easy to understand

Please return the layout configuration in JSON format as follows:
{{
    "type": "grid",  // Layout type: grid, flex, tabs
    "rows": 2,       // Number of rows
    "cols": 2,       // Number of columns
    "components": [] // Component placeholder info, can be empty, will be filled later
}}

Return ONLY the JSON, no additional text."""
    
    return prompt


def build_charts_design_prompt(question: str, data_schema: Dict[str, Any]) -> str:
    """Build prompt for designing dashboard charts.
    
    Args:
        question: User's question
        data_schema: Data schema dictionary
    
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a professional data visualization expert. Please design appropriate chart configurations based on the user's question and data schema.

User Question: {question}

Data Schema:
{json.dumps(data_schema, ensure_ascii=False, indent=2)}

Please design suitable charts to answer the user's question, considering the following factors:
1. Choose appropriate chart types based on the question (bar, line, pie, scatter, heatmap, etc.)
2. Select appropriate fields for the x-axis and y-axis
3. Set meaningful titles for each chart
4. Ensure charts effectively display data insights
5. Recommend designing 2-5 charts

Chart Type Descriptions:
- bar: Bar chart, suitable for comparing categorical data
- line: Line chart, suitable for showing trends
- pie: Pie chart, suitable for showing proportions
- scatter: Scatter plot, suitable for showing correlations
- heatmap: Heat map, suitable for displaying matrix data

Please return the chart configurations in JSON array format as follows:
[
    {{
        "type": "bar",           // Chart type
        "title": "Sales Analysis",    // Chart title
        "x_axis": "category",    // X-axis field name
        "y_axis": "sales",       // Y-axis field name
        "data_source": "table1", // Data source table name
        "description": "Display sales by category"  // Chart description
    }},
    ...
]

Return ONLY the JSON array, no additional text."""
    
    return prompt


def build_filters_design_prompt(data_schema: Dict[str, Any]) -> str:
    """Build prompt for designing dashboard filters.
    
    Args:
        data_schema: Data schema dictionary
    
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are a professional dashboard designer. Please design appropriate filter configurations based on the data schema.

Data Schema:
{json.dumps(data_schema, ensure_ascii=False, indent=2)}

Please design suitable filters considering the following factors:
1. Create dropdown select filters for categorical fields
2. Create range filters for numeric fields
3. Create date range filters for temporal fields
4. Select the 2-4 most important fields as filters
5. Ensure filters help users better explore the data

Filter Type Descriptions:
- select: Dropdown select box (for categorical fields)
- range: Range slider (for numeric fields)
- date_range: Date range picker (for temporal fields)
- multiselect: Multi-select dropdown (for categorical fields)

Please return the filter configurations in JSON array format as follows:
[
    {{
        "field": "category",      // Field name
        "type": "select",         // Filter type
        "data_source": "table1",  // Data source table name
        "label": "Category",          // Filter label
        "description": "Filter data by category"  // Filter description
    }},
    ...
]

Return ONLY the JSON array, no additional text."""
    
    return prompt

