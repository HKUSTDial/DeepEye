"""Chart Generation Prompts

Chart generation prompts migrated from autoVASystem.
"""

# Highlight block generation
HIGHLIGHT_DESIGN_PROMPT = """
You are a Visualization Design Expert. Based on the following extracted analytical intents and the provided dataset schema, generate zero or more highlight design suggestions.

Highlights are concise numerical or categorical summaries (such as "Total Revenue: $1.2M", "Top Region: APAC") shown as **highlight cards** on the dashboard. They should draw attention to **noteworthy, relevant, and interpretable** data signals, such as key aggregates, top performers, or anomalies. If **no meaningful highlight** can be generated based on the user's goals and data characteristics, **return null**.

## Design Guidelines:
- Only include highlights that **directly support** the extracted intents. Do not generate generic statistics.
- Highlights should focus on **overall patterns** (e.g., total count, average over all entries) rather than narrow subgroups.
- Use highlights **sparingly and purposefully**. Too many highlights reduce their effectiveness.
- Base highlight design on **actual insight potential**, not just what fields exist.
- All fields used in expressions **must exactly match** the column names listed in the `Data` section. Do **not** create new field names or aliases.

For each highlight design, include:

HIGHLIGHT_ID: A unique identifier for the highlight (e.g., HIGHLIGHT_1)
- HIGHLIGHT_TITLE: A short title for the highlight (e.g., Total Unique Products)
- HIGHLIGHT_PURPOSE: What this highlight helps achieve
- HIGHLIGHT_TYPE: The type of aggregation to apply (must be one of: nunique, sum, mean, count, max, min, mode)
- HIGHLIGHT_EXPRESSION: A simple expression to aggregate. This can be either: A single field name (e.g., sales); or A valid arithmetic expression involving multiple fields (e.g., revenue * quantity, (revenue - cost) / revenue)

Rules for HIGHLIGHT_EXPRESSION:
- Only use field names and basic arithmetic operators: +, -, *, /, and parentheses ()
- Do NOT use any aggregation functions like sum(), count(), mean(), etc.
- Do NOT rename fields or invent new ones

Here is an example:

Original Goal: I want to understand how our total sales changed over the last quarter and which products performed best.
Data: order_date, total_sales, region, product_name, units_sold
Dashboard Topic: product_name (focusing on product performance analysis)
Dashboard Title: Product Performance Analysis Dashboard

Extracted Intents:
INTENT_ID: 1
- INTENT: The user wants to analyze sales trends over time.
- FOCUS: Revenue over recent months
- VARIABLES: order_date, total_sales

INTENT_ID: 2
- INTENT: The user wants to compare product-level sales.
- FOCUS: Revenue trends by product
- VARIABLES: product_name, total_sales, order_date

INTENT_ID: 3
- INTENT: The user wants to identify top-performing products.
- FOCUS: Ranking of products by sales volume
- VARIABLES: product_name, units_sold

Highlight Design:

HIGHLIGHT_ID: highlight_1
- HIGHLIGHT_TITLE: Total Unique Products
- HIGHLIGHT_PURPOSE: To show the total number of unique products
- HIGHLIGHT_TYPE: nunique
- HIGHLIGHT_EXPRESSION: product_name

HIGHLIGHT_ID: highlight_2
- HIGHLIGHT_TITLE: Total Revenue
- HIGHLIGHT_PURPOSE: To show the total revenue
- HIGHLIGHT_TYPE: sum
- HIGHLIGHT_EXPRESSION: unit_price * quantity

****************************************************
Now, analyze the following user goal and dataset, generate at least 4 highlight designs:

Original Goal: {QUESTION}
Data: {DATA_SOURCE_SCHEMA}
Data Summary: {DATA_SUMMARY}
Data Analysis Result: {DATA_ANALYSIS_RESULT}
INSIGHTS: {INSIGHTS}

Highlight Design:
"""

HIGHLIGHT_CONFIG_PROMPT = """
Based on the given chart design plan, please generate specific chart configurations.

Data Source Schema:
{DATA_SOURCE_SCHEMA}

Chart Design Plan:
{HIGHLIGHT_DESIGN}

Please refer to the following configuration template to generate detailed configurations for each chart. The configuration must follow JSON format and include necessary data processing steps:
```json
[
    {{
        # Highlight block, Only one key number will be highlighted
        "id": "<block_id>",  # Example: "highlight_1"
        "blockType": "highlight",
        "blockContent": {{
            "title": "<highlight_title>",
            "type": "<highlight_type>",  # Supported: "nunique", "sum", "mean", "count", "max", "min", "mode" (For CATEGORICAL or TEMPORAL, only "nunique" is supported; For NUMERICAL, only "sum", "mean", "count", "max", "min", "mode" are supported)
            "expression": "<expression>", # A simple expression to aggregate. This can be either: A single field name (e.g., sales); or A valid arithmetic expression involving multiple fields, do not use any aggregation functions like sum(), count(), mean(), etc. (e.g., revenue * quantity, (revenue - cost) / revenue)
            "unit": "<unit>"  # Use string to represent the unit of the data field, if no unit, use empty string "".
        }}
    }},
    {{
        "id": "<block_id>",  
        "blockType": "highlight",
        "blockContent": ...
    }}
]
```

Requirements:
1. Configuration must strictly follow the template structure
2. All field names must come from the data source schema
3. Return format must be a valid JSON array and use ````json``` to wrap the json object.
4. At least generate 4 highlight block.
    
Please generate the configuration, and output should use ````json``` to wrap the json object.
"""

# Dashboard design prompts
DASHBOARD_DESIGN_PROMPT = """
You are a Dashboard Design Expert. Based on the following insights and chart designs, generate a comprehensive dashboard design focusing on filter components and view interactions.

Your goal is to design an interactive dashboard that enhances data exploration through:
1. Filter components that allow users to control data views, the filter will be applied to the whole dashboard.
   IMPORTANT: If the data schema contains 'dimension', 'name', and 'value' columns, it means the data is in Long Format. 
   In this case, to filter a specific metric (e.g., "monthly_revenue"), set the FILTER'S FIELD to the metric name (e.g., "monthly_revenue"). 
   The system will automatically filter the 'name' column within that dimension.
2. Inter-chart interactions that enable data discovery through highlighting and cross-filtering

For each filter component design, include:
FILTER_ID: A unique identifier for the filter (e.g., filter_1)
- FILTER_PURPOSE: What this filter helps control
- FILTER_DESCRIPTION: A short natural language explanation of the filter design
- LABEL: Display label for the filter
- CONTROL_TYPE: The type of control (select, multiselect, slider, range, checkbox, radio)
- FIELD: The data field this filter controls (Use the dimension name if data is in Long Format)
- OPERATOR: How the filter operates (equals, not_equals, between, one_of, not_in)
- RANGE_CONFIG: For slider/range controls, specify min/max/step values in one line

For each interaction design which is only on the view block, include:
INTERACTION_ID: A unique identifier for the view interaction (e.g., interact_1)
- INTERACTION_PURPOSE: What this interaction helps achieve
- INTERACTION_DESCRIPTION: A short natural language explanation of the interaction
- SOURCE_VIEW: The source chart and field that triggers the interaction, it must contain in the chart designs
- SOURCE_LAYER: The source layer and field that triggers the interaction, it must contain in the chart designs
- SOURCE_FIELD: The source field that triggers the interaction, it must contain in the chart designs
- TARGET_VIEW: The target chart and field that receives the interaction
- TARGET_LAYER: The target layer and field that receives the interaction
- TARGET_FIELD: The target field that receives the interaction
- TYPE: The type of interaction (highlight, cross-filter)
- DETAIL: Specific configuration for the interaction type in one line

****************************************************
Now, analyze the following insights and chart designs:

Insights: {INSIGHTS}
Data Source Schema: {DATA_SOURCE_SCHEMA}
Chart Designs: {CHART_DESIGNS}

Please generate a comprehensive dashboard design focusing on filter components and interactions:
Filter Design:
Please fill in the filter design here.

Interaction Design:
Please fill in the interaction design here.
"""

DASHBOARD_INTERACT_CONFIG_PROMPT = """
You are a Dashboard Design Expert. Based on the following dashboard design and data source schema, generate a comprehensive dashboard configuration that includes both filter blocks and interaction edges.

Dashboard Design:
{DASHBOARD_DESIGN}

Data Source Schema:
{DATA_SOURCE_SCHEMA}

Chart Configs:
{CHART_CONFIGS}

Please generate a dashboard configuration that follows this JSON schema, only fill filter block and interaction edges, ignore the chart config:
```json
{{
    "blocks": [
        {{
            "id": "<filter_id>",
            "blockType": "filter",
            "blockContent": {{
                "controlType": "<control_type>",  # select, multiselect, slider, range, checkbox, radio
                "field": "<field_name>", # If Long Format (dimension/name/value), use the specific dimension value as field name
                "label": "<display_label>",
                "operator": "<operator>",  # equals, not_equals, between, one_of, not_in
                "range": {{  # Required for slider/range controls
                    "min": <number>,
                    "max": <number>,
                    "step": <number>
                }}
            }}
        }}
    ],
    "interactionEdges": [
        {{
            "source": {{
                "block": "<source_block_id>",
                "layer": "<source_layer_id>",
                "field": "<source_field>"
            }},
            "target": {{
                "block": "<target_block_id>",
                "layer": "<target_layer_id>", 
                "field": "<target_field>"
            }},
            "interaction": {{
                "type": "<interaction_type>",  # highlight, cross-filter
                "detail": {{
                    # For highlight:
                    "color": "<color_hex>",
                    "opacity": {{
                        "active": <number>,
                        "inactive": <number>
                    }}
                    # For cross-filter:
                    # "type": "showDetail"
                }}
            }}
        }}
    ]
}}
```

Requirements:
1. The configuration must strictly follow the schema structure
2. All interaction source block must contain in the chart designs
3. Filter blocks must match the filter design specifications
4. Interaction edges must match the interaction design specifications
5. Return format must be a valid JSON object wrapped in ```json```

Please generate the configuration, and output should use ```json``` to wrap the json object.
"""

# Dashboard Name and Description Generation Prompt
DASHBOARD_NAME_DESCRIPTION_PROMPT = """
You are a Dashboard Naming Expert. Based on the user's question and dataset information, generate a concise dashboard name and a catchy, short subtitle.

User Question: {QUESTION}
Dataset Schema: {DATA_SOURCE_SCHEMA}
Dataset Summary: {DATA_SUMMARY}

Please generate:
1. DASHBOARD_NAME: A professional, concise title (2-5 words, Title Case).
2. DASHBOARD_DESCRIPTION: A short, engaging subtitle (5-12 words). It should summarize the key insight or value proposition. Avoid generic phrases like "This dashboard shows...".

Output format:
DASHBOARD_NAME: <name>
DASHBOARD_DESCRIPTION: <description>
"""

# LIDA Lite: Goal Generation Prompt
LIDA_LITE_GOAL_PROMPT = """
You are a Data Visualization Expert. Given a dataset summary and a user question, generate {N} visualization goals that help answer the question or explore the data.

Dataset Summary:
{SUMMARY}

User Question:
{QUESTION}

## Goal Requirements:
- Each goal should be a specific question that can be answered with a single visualization.
- Ensure the goals are diverse and cover different aspects of the data (trends, distributions, correlations, etc.). DO NOT repeat the same insight with different chart types.
- Goals must be relevant to the user question if provided.
- Each goal should focus on a distinct set of columns or a distinct data question to ensure variety in the final dashboard.

For each goal, provide:
1. question: A clear question the visualization answers (e.g., "What is the total revenue trend by month?").
2. visualization: The type of chart recommended (e.g., bar, line, pie, scatter, heatmap).
3. rationale: Why this visualization is useful and what insight it provides.

Return the goals as a JSON array of objects with 'question', 'visualization', and 'rationale' keys. Wrap the JSON in ```json```.
"""

# LIDA Lite: Visualization (ECharts) Generation Prompt
LIDA_LITE_VISUALIZE_PROMPT = """
You are an ECharts Expert. Given a dataset summary and a visualization goal, generate Python code that uses the `pyecharts` library to create a visualization.

Dataset Summary:
{SUMMARY}

Visualization Goal:
{GOAL}

## Requirements:
- The code must define a function `plot(data: pd.DataFrame)` that returns a `pyecharts.charts.Base` object (e.g., Bar, Line, Pie, Scatter, HeatMap).
- **CRITICAL**: The `plot` function MUST return a pyecharts chart object, NOT a dictionary.
- **DIVERSITY**: Ensure each chart you generate uses different aspects of the data. DO NOT generate multiple charts that show the same information with slightly different titles.
- **CHART SELECTION**: Choose the most appropriate chart type for the data (e.g., Line for time series, Bar for categories, Scatter for correlation).
- **STYLING**: Use professional colors and labels. Set a unique and descriptive title for each chart.
- Ensure the code is robust and handles the data types specified in the summary.
- The output should only be the Python code, wrapped in ```python```.
- Use the data provided in the `data` parameter. Do not load external files.
- Ensure column names match the summary exactly.
- Include necessary imports from `pyecharts.charts` and `pyecharts import options as opts`.

Example structure:
```python
import pandas as pd
from pyecharts.charts import Bar
from pyecharts import options as opts

def plot(data: pd.DataFrame):
    # Process data if needed (e.g., groupby, aggregation)
    # The 'data' passed to plot is a pandas DataFrame.
    
    # 1. Prepare data
    agg_data = data.groupby('category')['value'].sum().reset_index()
    x_data = agg_data['category'].tolist()
    y_data = agg_data['value'].tolist()
    
    # 2. Create chart object
    chart = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis("Label", y_data)
        .set_global_opts(title_opts=opts.TitleOpts(title="Chart Title"))
    )
    return chart
```
"""


