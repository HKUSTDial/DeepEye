# pipeline.py
import json
import logging
import re
import os
import io
from pathlib import Path
from typing import Any
from collections.abc import Callable
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict
from jinja2 import Template
from openai import OpenAI
from app.core.config import settings
from .utils import (
    build_report_chart_placeholder_html,
    execute_python_code,
    render_plotly_figure_for_report,
)

logger = logging.getLogger(__name__)

# --- Dependency Check (Storyteller) ---
try:
    from .DatasetContextGenerator import DatasetContextGenerator

    HAS_CONTEXT_GEN = True
except ImportError:
    HAS_CONTEXT_GEN = False
    logger.warning("Storyteller library not found. Using simple metadata generation mode.")


class AutoReportPipeline:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        resolved_model = (model_name or settings.LLM_MODEL or "").strip()
        if not resolved_model:
            raise ValueError("LLM_MODEL is required for report generation")
        self.model_name = resolved_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.progress_callback = progress_callback

        if HAS_CONTEXT_GEN:
            self.ds_generator = DatasetContextGenerator(
                api_key=api_key,
                base_url=base_url,
                model_name=resolved_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    def _emit(self, message: str) -> None:
        text = str(message).strip()
        if not text:
            return
        logger.info(text)
        if self.progress_callback:
            self.progress_callback(text)

    # --- Helper: LLM Call Wrapper ---
    def _call_llm(self, prompt: str, json_mode=False) -> str:
        messages = [{"role": "system",
                     "content": "You are a Senior Data Analyst expert in Python and Plotly. You must output everything in English."},
                    {"role": "user", "content": prompt}]
        request_params: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "response_format": {"type": "json_object"} if json_mode else None,
            "temperature": self.temperature,
        }
        if self.max_tokens and self.max_tokens > 0:
            request_params["max_tokens"] = self.max_tokens
        response = self.client.chat.completions.create(**request_params)
        return response.choices[0].message.content

    def _extract_code(self, text: str) -> str:
        match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1)
        return text.replace("```python", "").replace("```", "").strip()

    # --- Step 1: Generate Data Context (Multi-Table Support) ---
    def generate_multi_table_context(self, dfs: Dict[str, pd.DataFrame]) -> str:
        self._emit("🔍 [1/7] Generating dataset context...")
        full_context_str = ""

        for name, df in dfs.items():
            self._emit(f"   -> Analyzing table: {name}")
            if HAS_CONTEXT_GEN:
                ctx = self.ds_generator.generate_context(
                    data=df,
                    dataset_name=name,
                    dataset_description=f"Table: {name}",
                    n_samples=5
                )
                info = json.dumps(ctx.get('fields_info', {}), indent=2)
                desc = ctx.get('dataset_description', '')
            else:
                buffer = io.StringIO()
                df.info(buf=buffer)
                info = buffer.getvalue()
                desc = "No description."

            full_context_str += f"\n\n=== TABLE: '{name}' ===\n[Description]: {desc}\n[Structure]:\n{info}"

        return full_context_str

    # --- Step 2: Deep Mining (EDA) ---
        # --- Step 2: Deep Mining (EDA) ---
    def perform_deep_analysis(self, dfs: Dict[str, pd.DataFrame], context_str: str,query: str) -> str:
        self._emit("🕵️ [2/7] Performing deep exploratory analysis (EDA)...")

        # 1. 构建更清晰的 Prompt，强制要求遍历和打印
        # 新增：加入 User Query 上下文
        prompt = f"""
                You are a senior data scientist. 
                I have loaded **multiple datasets** into a Python dictionary named `dfs`.
                The keys (table names) are: {list(dfs.keys())}

        [Datasets Metadata]:
        {context_str}

        [User Interest]: "{query}"

        [Goal]: Write a Python script to perform Exploratory Data Analysis (EDA). 
        **PRIORITY**: Focus on columns/tables relevant to the [User Interest], but also provide a general overview.

        [CRITICAL INSTRUCTIONS]:
        1. **Iterate**: You MUST iterate through the dictionary: `for name, df in dfs.items():`
        2. **Print Header**: Inside the loop, print the table name: `print(f"\\n### Analyzing Table: {{name}} ###")`
        3. **Basic Stats**: 
           - Print shape and columns.
        4. **Targeted Analysis (Based on Query)**:
           - Identify columns related to the user's query (e.g., if query mentions "sales", look for 'revenue', 'amount', 'profit').
           - For these relevant columns, print detailed stats (mean, sum, trend if date exists).
           - If User Interest is specific (e.g. "Product X"), filter data and print stats for that specific subset.
        5. **General Analysis**:
           - Missing Values: `print(df.isnull().sum()[df.isnull().sum() > 0])`
           - Numeric: Print correlation matrix for numeric cols.
           - Categorical: Print top 3 frequent values.

        [Constraint]:
        - **USE `print()` FOR EVERYTHING**. If you don't print, I see nothing.
        - **Robustness**: If a specific column doesn't exist, do not crash; just print a message or skip.
        - Return ONLY the Python code.
         -"dfs" Should be used in read-only mode,you can't define it.
        """
        # 2. 调用 LLM 生成代码
        code = self._extract_code(self._call_llm(prompt))

        # 3. 执行代码
        result = execute_python_code(code, dfs)

        # 4. 结果处理与调试信息
        if result['success']:
            if not result['text'].strip():
                self._emit("   ⚠️ Mining executed but produced NO OUTPUT. Check Prompt Logic.")
                return "No analysis output generated."

            #print("   ✅ Mining successful. Output preview:")
            #print(result['text'][:300] + "...\n(Truncated)")
            return result['text']
        else:
            self._emit(f"   ⚠️ Mining failed: {result['error']}")
            # 兜底返回基础信息
            fallback = []
            for k, v in dfs.items():
                fallback.append(f"Table '{k}': {v.shape[0]} rows, columns: {list(v.columns)}")
            return "\n".join(fallback)

    # --- Step 3: Dynamic KPIs ---
        # --- Step 3: Dynamic KPIs (Fixing "All arrays must be of the same length" error) ---
        # --- Step 3: Dynamic KPIs (Fixing "All arrays must be of the same length" error) ---
    def generate_kpis(self, dfs: Dict[str, pd.DataFrame], context_str: str,query: str) -> List[Dict]:
        self._emit("📊 [3/7] Calculating key business indicators (KPI)...")
        #print(context_str)
        #print(list(dfs.keys()))
        prompt = f"""
                [Datasets Metadata]:
                {context_str}

                [User Interest]: "{query}"

                [Task]:
                1. Identify the main table containing metric data relevant to the [User Interest].
                2. Write Python code to calculate 4 Key Performance Indicators (KPIs).

                **PRIORITY INSTRUCTION**: The KPIs MUST be directly relevant to the user's query.
                   - **Specific Filter**: If the user asks about a specific product (e.g., 'SmartPhone Ultra'), region, or category, you MUST filter the DataFrame first to calculate metrics for that specific segment (e.g., "SmartPhone Ultra Sales" instead of "Total Sales").
                   - **Specific Topic**: If the user asks about "Profit", focus on profit-related metrics. If "Feedback", focus on ratings/sentiment.
                   - **Fallback**: Only if the query is very general (e.g., "Analyze the data"), calculate overall global metrics.

                3. The data is in a dictionary `dfs`. Keys: {list(dfs.keys())}.
                4. Save result to a list variable named `kpi_results`.

                [Crucial Rules for Robustness]:
                - **SCALAR VALUES ONLY**: Calculate single numbers (e.g., sum, mean, count). **DO NOT** assign lists or arrays to new DataFrame columns.
                - **Check Columns**: Ensure columns exist in `dfs['table']` before using them.
                - **String Matching**: When filtering by string (e.g. product name), use `.str.contains(..., case=False, na=False)` to be robust against capitalization differences.
                - **Format**: Convert values to formatted strings (e.g., "$1.2M", "4.5 stars", "1,200 units").
                - **No DataFrame Modification**: Do not try to add columns to the dataframes; just read from them.
                --"dfs" Should be used in read-only mode,you can't define it.
                [KPI Data Structure]:
                List[Dict] containing: label, value, sub_label, trend, trend_color.

                [Example Code Logic]:
                # Example: User asks about "SmartPhone Ultra"
                df = dfs['sales']
                # Filter for the specific product mentioned in query
                target_df = df[df['product_name'].str.contains("SmartPhone Ultra", case=False, na=False)]

                if not target_df.empty:
                    total_rev = target_df['total_amount'].sum()
                    label_name = "SmartPhone Ultra Sales"
                else:
                    # Fallback if filter returns empty
                    total_rev = df['total_amount'].sum()
                    label_name = "Total Sales"

                kpi_results = [
                    {{"label": label_name, "value": f"${{total_rev:,.0f}}", "sub_label": "Revenue", "trend": "Stable", "trend_color": "blue"}}
                ]

                Output ONLY Python code.
                """

        code = self._extract_code(self._call_llm(prompt))

        # 传入 dfs 字典
        local_vars = {"dfs": dfs, "pd": pd, "np": np}

        try:
            exec(code,local_vars,local_vars)
            results = local_vars.get('kpi_results', [])
            if not results:
                raise ValueError("No kpi_results variable found")
            return results
        except Exception as e:
            self._emit(f"   ❌ KPI Calculation Error: {e}, using default values")
            return [{"label": "Tables Loaded", "value": str(len(dfs)), "trend_color": "blue"}]

        # --- Step 4: Plan and Plot ---
    def analyze_and_plot(self, dfs: Dict[str, pd.DataFrame], query: str, context_str: str) -> List[Dict]:
        self._emit("📈 [4/7] Planning and generating visual charts...")

        # 1. Planning Phase
        plan_prompt = f"""
                User Query: "{query}"
                [Datasets Info]: {context_str}

                Please plan 3-4 analysis angles. You can analyze single tables or merge tables.
                Return JSON format:
                {{
                    "sections": [
                        {{"title": "Analysis Title", "desc": "Goal", "chart_instruction": "Merge table A and B, then draw scatter plot..."}}
                    ]
                }}
                """
        try:
            plan_json = json.loads(self._call_llm(plan_prompt, json_mode=True))
        except Exception:
            self._emit("   ⚠️ Plan parsing failed")
            return []

        # === 关键修复：预先提取所有表的列名 ===
        table_columns_info = {name: df.columns.tolist() for name, df in dfs.items()}
        columns_context = json.dumps(table_columns_info, indent=2)
        #print(table_columns_info)
        #print(columns_context)

        results = []
        for section in plan_json.get('sections', []):
            self._emit(f"   -> Processing Section: {section['title']}")

            # 2. Plotting Phase
            code_prompt = f"""
                            The datasets are loaded in a dictionary `dfs`.
                            Table name: {list(dfs.keys())}

                            [CRITICAL: Table's Available Columns]:
                            {columns_context}

                            [Task]:
                            1. Create exactly one focused chart object `fig` using plotly.express (px). Only one chart per execution.
                            2. **Instruction**: "{section['chart_instruction']}"
                            3. **Data Handling**: 
                               - Access tables via `dfs['name']`. 
                               - **VERIFY COLUMN NAMES**: Use ONLY the column names listed above.
                               - Perform `pd.merge()` if needed.
                               - **CRITICAL**: When filtering, ALWAYS use `.copy()`.

                               >>> [AGGREGATION RULE]: When using value_counts() or groupby(), YOU MUST explicitly rename columns immediately to ensure they exist.
                               Example:
                               temp = df['col'].value_counts().reset_index()
                               temp.columns = ['category_col', 'count_col'] # FORCE RENAME
                               fig = px.bar(temp, x='category_col', y='count_col', ...)

                               - **CRITICAL FIX**: Plotly cannot serialize 'Period' objects. Convert to string (`.astype(str)`).
                               - Do NOT use `make_subplots`, dual-axis layouts, multiple domains, parallel coordinates mixed with other charts, or dashboard-style composites.
                               - Do NOT set a fixed chart width. If you set height, keep it between 380 and 520.
                               - Prefer a single bar, line, scatter, box, area, or heatmap view that fits comfortably inside a report card.

                            4. **Analysis**: Calculate table stats and `print()` them.

                            [Code Requirements]:
                            - Do not use fig.show().
                            - Output only Python code.
                            """
            #print(code_prompt)
            code = self._extract_code(self._call_llm(code_prompt))
            #print(code)
            exec_res = execute_python_code(code, dfs)
            #print(exec_res)

            chart_html = build_report_chart_placeholder_html("No chart was generated for this section.")
            stats_data = "(No statistical data produced.)"

            if exec_res['success']:
                if exec_res['fig']:
                    try:
                        chart_html = render_plotly_figure_for_report(exec_res['fig'])
                    except TypeError as e:
                        self._emit(f"      ❌ Serialization Error (Period/Type issue): {e}")
                        chart_html = build_report_chart_placeholder_html(
                            f"Chart rendering failed because the figure contains non-serializable values. {e}"
                        )
                else:
                    self._emit("      ⚠️ No figure object was produced")

                if exec_res['text']:
                    stats_data = exec_res['text'].strip()
            else:
                self._emit(f"      ⚠️ Code Execution Failed: {exec_res.get('error')}")
                chart_html = build_report_chart_placeholder_html(
                    f"Chart generation code failed: {exec_res.get('error') or 'Unknown execution error.'}"
                )

            # 3. Insight Generation Phase
            insight_prompt = f"""
                    Write a business insight (100 words).
                    [Goal]: {section['desc']}
                    [Data Facts]: {stats_data}
                    """
            insight_text = self._call_llm(insight_prompt)

            results.append({
                "title": section['title'],
                "desc": insight_text,
                "chart_html": chart_html
            })

        return results

    # --- Step 5: Render HTML ---
    def render_html(self, kpis: List[Dict], analysis_results: List[Dict],
                    summary: str, conclusion: str, title: str,
                    output_file: str, template_name: str):
        self._emit(f"🎨 [6/7] Rendering final HTML report using {template_name}...")

        template_path = Path(__file__).resolve().parent / "templates" / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"❌ Template file not found: {template_path}")

        with template_path.open("r", encoding="utf-8") as f:
            template_str = f.read()

        template = Template(template_str)

        for k in kpis:
            k['color'] = k.get('trend_color', 'blue').lower() if k.get('trend_color') in ['blue', 'green',
                                                                                          'red'] else 'blue'

        html_out = template.render(
            title=title,
            generation_date=datetime.now().strftime("%Y-%m-%d"),
            summary_text=summary,
            kpis=kpis,
            analysis_sections=analysis_results,
            conclusion_text=conclusion
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_out)
        self._emit(f"✅ [7/7] Report saved to: {output_file}")

    # --- Main Entry ---
    def run(self, csv_paths: List[str], user_query: str, template_name: str, output_file="final_report.html"):
        # 0. Load Data into Dictionary
        dfs = {}
        self._emit("📂 [0/7] Loading and parsing data files...")

        for path in csv_paths:
            if os.path.exists(path):
                file_name = os.path.splitext(os.path.basename(path))[0]
                try:
                    df_temp = pd.read_csv(path)
                    dfs[file_name] = df_temp
                    self._emit(f"   - Loaded table: '{file_name}' ({len(df_temp)} rows)")
                except Exception as e:
                    self._emit(f"   ❌ Error loading {path}: {e}")
            else:
                self._emit(f"   ❌ File not found: {path}")

        if not dfs:
            self._emit("❌ No valid data loaded.")
            return

        # 1. Generate Context
        context_str = self.generate_multi_table_context(dfs)

        # 2. Deep Mining
        mining_text = self.perform_deep_analysis(dfs, context_str, user_query)

        # 3. KPIs
        kpis = self.generate_kpis(dfs, context_str,user_query)

        # 4. Chart Analysis
        analysis_results = self.analyze_and_plot(dfs, user_query, context_str)

        # 5. Text Content
        summary_prompt = f"""
                You are a professional data analyst. Write an executive summary based on the following statistics.
        [Content Requirements]:
        Write a brief overall assessment (approximately 100 words).

        [Strictly Prohibited]:
        - Do not use markdown code blocks (```html).
        - Do not include the title "Executive Summary".

        [Data Source]:
        {mining_text}
                """
        self._emit("✍️ [5/7] Writing analysis summary and conclusions...")
        summary = self._call_llm(summary_prompt)

        conclusion_prompt = f"""
                Propose 3 specific business recommendations based on the analysis.

                [Format Requirements]:
                1. Output HTML Unordered List (<ul>).
                2. For each recommendation (<li>), use <b> to bold the title, followed by explanation.
                   Example: <li><b>Optimize Pricing:</b> Focus on the southeast region...</li>
                3. **Output strictly in ENGLISH**.

                [Strictly Forbidden]:
                - Do not use markdown blocks.

                [Data Source]:
                {mining_text}
                """
        conclusion = self._call_llm(conclusion_prompt)

        # 6. Render
        report_title = "Data Analysis Report"
        self.render_html(kpis, analysis_results, summary, conclusion, report_title, output_file, template_name)
