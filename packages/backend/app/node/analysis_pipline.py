import json
import re
import os
import markdown
from typing import List, Dict, Any
from datetime import datetime
# --- 引入原有依赖 ---
# 请确保这些模块在你的 Python 路径下可用
from llm_client import client
from auto_viz2 import nl_to_sql, csv_to_sqlite, visualize_result_to_map
from md_chart import insert_chart_placeholders
from storyteller.algorithm.utils.DatasetContextGenerator import DatasetContextGenerator


# ==========================================
# 模块 1: HTML 报告生成器 (来自 report_html3.py)
# ==========================================
class ReportGenerator:
    def parse_markdown_structure(self, text: str):
        lines = text.split('\n')
        title = "数据分析报告"
        description = "基于现有数据的深度洞察与分析"
        body_lines = []

        header_found = False
        for i, line in enumerate(lines):
            match = re.match(r'^#\s+(.+)$', line.strip())
            if match and not header_found:
                title = match.group(1)
                header_found = True
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('!['):
                        description = next_line
                        continue
                continue
            if header_found and line.strip() == description:
                continue
            body_lines.append(line)

        raw_body = "\n".join(body_lines)
        processed_body = self.preprocess_summary_box(raw_body)
        return title, description, processed_body

    def preprocess_summary_box(self, text: str) -> str:
        lines = text.split('\n')
        new_lines = []
        in_summary = False
        header_pattern = re.compile(r'^#+\s+')

        for line in lines:
            if ("Executive Summary" in line or "摘要" in line) and header_pattern.match(line):
                new_lines.append(line)
                new_lines.append("")
                new_lines.append('<div class="summary-section">')
                in_summary = True
                continue
            if in_summary and header_pattern.match(line):
                new_lines.append('</div>')
                new_lines.append("")
                in_summary = False
                new_lines.append(line)
                continue
            new_lines.append(line)

        if in_summary:
            new_lines.append('</div>')
        return "\n".join(new_lines)

    def generate_html_report(self, markdown_content: str, chart_map: dict = None) -> str:
        title, description, body_md = self.parse_markdown_structure(markdown_content)

        # 替换图表占位符
        if chart_map:
            for chart_id, chart_html in chart_map.items():
                # 注意：这里假设 placeholder 格式为 [[chart_id]] 或类似的
                # 根据 md_chart 的逻辑，通常 markdown 中已经是占位符了
                # 这里做一次通用的替换尝试，以防万一
                placeholder_bracket = f"[[{chart_id}]]"
                if placeholder_bracket in body_md:
                    body_md = body_md.replace(placeholder_bracket, chart_html)
                # 同时也处理纯文本 ID 的情况（视具体实现而定）

        html_body = markdown.markdown(
            body_md,
            extensions=['extra', 'toc', 'smarty']
        )

        css_styles = """
            :root {
                --brand-dark: #0057d9;
                --brand-light: #e6f0ff;
                --accent: #0078ff;
                --text-main: #0f172a;
                --text-light: #64748b;
                --bg: #f8fbff;
                --card-bg: #ffffff;
            }
            [data-theme="business"] {
                --brand-dark: #0a2540;
                --brand-light: #ffffff;
                --accent: #4c8cff;
                --text-main: #1f2933;
                --text-light: #4b5563;
                --bg: #f5f7fa;
                --card-bg: #ffffff;
            }
            [data-theme="soft"] {
                --brand-dark: #7a4bb7;
                --accent: #b388f3;
                --text-main: #4a3470;
                --text-light: #7d6c99;
                --bg: #faf7ff;
                --card-bg: #ffffff;
            }
            [data-theme="china"] {
                --brand-dark: #b30000;
                --accent: #e6b800;
                --text-main: #4d0d0d;
                --text-light: #945c5c;
                --bg: #f8f3e8;
                --card-bg: #fff9f0;
            }
            body { margin: 0; padding: 0; background-color: var(--bg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: var(--text-main); }
            .hero-header { background-color: var(--brand-dark); color: var(--brand-light); padding: 80px 20px 140px 20px; text-align: center; background-image: linear-gradient(135deg, var(--brand-dark) 0%, var(--accent) 100%); }
            .hero-header h1 { margin: 0; font-size: 3rem; font-weight: 700; letter-spacing: -1px; }
            .hero-header .subtitle { margin-top: 15px; font-size: 1.2rem; opacity: 0.9; max-width: 800px; margin: auto; line-height: 1.6; }
            .main-card { max-width: 900px; margin: -100px auto 60px auto; background: var(--card-bg); border-radius: 12px; padding: 60px; box-shadow: 0 20px 40px rgba(0,0,0,0.08); position: relative; }
            h2 { font-size: 1.8rem; color: var(--brand-dark); margin-top: 50px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
            h2::before { content: ''; display: inline-block; width: 8px; height: 30px; background: var(--accent); margin-right: 15px; vertical-align: middle; border-radius: 2px; }
            h3 { color: var(--text-light); font-size: 1.3rem; margin-top: 40px; font-weight: 600; }
            p { line-height: 1.8; color: var(--text-main); margin-bottom: 1.5em; text-align: justify; }
            .summary-section { background: #f8f9fa; border-radius: 8px; padding: 20px 30px; margin-top: 20px; margin-bottom: 40px; border: 1px solid #e9ecef; border-left: 5px solid var(--accent); color: var(--text-main); font-weight: 500; }
            img { display: block; max-width: 80%; margin: 40px auto 10px auto; border-radius: 8px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); border: 1px solid #f0f0f0; }
            em { display: block; text-align: center; color: #888; font-style: normal; font-size: 0.9rem; margin-bottom: 50px; }
            .theme-switch { position: fixed; right: 20px; top: 20px; z-index: 1000; display: flex; flex-direction: column; gap: 8px; }
            .theme-btn { padding: 6px 12px; background: var(--accent); border: none; color: white; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
            @media print { body { background: white; } .hero-header { padding: 40px 0; -webkit-print-color-adjust: exact; } .main-card { margin: 0; box-shadow: none; padding: 0; max-width: 100%; } }
        """

        plotly_script = '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'

        html = f"""<!DOCTYPE html>
            <html lang="zh-CN" data-theme="tech">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{title}</title>
                {plotly_script} <style>{css_styles}</style>
            </head>
            <body>
                <div class="theme-switch">
                    <button class="theme-btn" onclick="setTheme('tech')">科技蓝</button>
                    <button class="theme-btn" onclick="setTheme('business')">深蓝</button>
                    <button class="theme-btn" onclick="setTheme('soft')">白紫</button>
                    <button class="theme-btn" onclick="setTheme('china')">国潮</button>
                </div>
                <header class="hero-header">
                    <h1>{title}</h1>
                    <div class="subtitle">{description}</div>
                </header>
                <main class="main-card">
                    {html_body}
                </main>
                <script>
                    function setTheme(t) {{ document.documentElement.setAttribute('data-theme', t); }}
                </script>
            </body>
            </html>
            """
        return html


# ==========================================
# 主 Pipeline 类
# ==========================================
class AutoReportPipeline:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.report_gen = ReportGenerator()
        # 确保 Storyteller Generator 初始化
        self.ds_generator = DatasetContextGenerator(api_key=api_key, base_url=base_url)

    def _save_visual_queries_json(
            self,
            visual_queries: List[Dict],
            output_dir: str = "outputs/visual_queries"
    ):
        os.makedirs(output_dir, exist_ok=True)

        filename = f"visual_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(output_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(visual_queries, f, ensure_ascii=False, indent=2)

        print(f"✅ 可视化查询已保存为 JSON: {path}")

    # --- 步骤 1: 生成数据上下文 (generate_data_context.py) ---
    def generate_data_context(self, csv_file: str, n_samples=5) -> Dict:
        print(f"🚀 [1/5] 正在分析数据上下文: {csv_file}")
        dataset_context = self.ds_generator.generate_context(
            data=csv_file,
            dataset_name="",  # 使用默认
            dataset_description="",  # 使用默认
            n_samples=n_samples
        )
        #print(dataset_context)
        return dataset_context

    # --- 步骤 2: 生成纯文本初稿 (raw_report.py) ---
    def generate_raw_report(self, data_context: Dict, query: str) -> str:
        print(f"📝 [2/5] 正在生成文本报告初稿...")
        data_context_str = json.dumps(data_context, ensure_ascii=False, indent=2)
        prompt = f"""
        这是一个前缀名字是西气东输二线干线的.csv文件。你是专业数据分析师，仔细分析以下 data_context 和用户 query，
        生成一篇完整的“文字版数据分析报告”。
        要求：
        - 要基于数据上下文得出洞察
        - 字数越多越好
        data_context:
        {data_context_str}

        query:
        {query}
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        print(response.choices[0].message.content.strip())
        return response.choices[0].message.content.strip()

    # --- 步骤 3: 提取可视化查询 (generate_visual_query.py) ---
    def extract_visual_queries(self, full_report: str) -> List[Dict]:
        print(f"📊 [3/5] 正在规划可视化图表...")

        prompt = f"""
    你是负责将报告转为可视化洞察的分析专家。
    给定“原始文字报告”，
    请从报告中提取所有有价值、适合用图表表达的数据分析点，并生成对应的“可视化查询”。
    不限制可视化查询的数量，但要对理解报告有实质帮助，最好让各种图类型都能出现，而且展示出来的图需美观。
    每个可视化查询输出格式必须严格为以下 JSON 对象：
    {{
        "id": "chart1",
        "chart_type": "line/bar/pie/heatmap/boxplot...",
        "nl_query": "可视化洞察",
        "reason": "为什么该信息适合用这种图表表达"
    }}

    full_report:
    {full_report}

    最终输出：
    - 一个 JSON 数组
    - 不要输出任何额外解释性文字
    """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw_output = response.choices[0].message.content.strip()

        # 1️⃣ 清理 ```json 包裹
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_output)
        cleaned = re.sub(r'\s*```$', '', cleaned)

        try:
            visual_queries = json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析失败: {e}")
            return []

        # 2️⃣ 保存为 JSON 文件（关键新增）
        self._save_visual_queries_json(visual_queries)

        # 3️⃣ 返回给后续可视化流程
        return visual_queries

    # --- 步骤 4: 重组 Markdown 报告 (report_template.py) ---
    def structure_report(self, full_report: str, visual_queries: List[Dict]) -> str:
        print(f"🏗️ [4/5] 正在重组报告结构...")
        prompt = f"""
        请根据以下原始报告（original_report）和可视化查询列表（visual_queries），将内容重写为一份分析完全的数据分析报告，内容需详细。报告需满足以下要求：

        - 采用图文混排形式，在正文中合适位置插入图表引用提示，格式为“(见图表 chart1，chart2，......)”；
        - **必须严格按照 visual_queries 中的 id 顺序引用图表**
        - **每个图表 ID 只能被引用一次**；
        - **不生成、不描述、不解释图表内容**，仅标注其插入位置；
        - 报告需保持逻辑完整、语言专业；
        - 严格遵循以下章节结构：
        # 标题（Title）（你需要起个标题）  
        # 1. 执行摘要（Executive Summary）  
        # 2. 分析背景与目标（Introduction）  
        # 3. 数据概览（Data Overview）  
        # 4. 描述性统计（Descriptive Statistics）  
        # 5. 核心发现（Key Findings）  
        # 6. 业务解读（Business Interpretation）  
        # 7. 建议（Recommendations）  
        # 8. 局限性（Limitations）  
        # 9. 结论（Conclusion）  
        ---
        original_report:  
        {full_report}

        visual_queries:  
        {json.dumps(visual_queries, ensure_ascii=False)}

        ---
        输出要求：仅输出重写后的 Markdown 正文。
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        with open("xiqi.md", "w", encoding="utf-8") as f:
            f.write(response.choices[0].message.content.strip())
        return response.choices[0].message.content.strip()

    # --- 步骤 5: 执行 SQL, 生成图表并渲染 HTML (report_html3.py) ---
    def generate_final_html(self, csv_path: str, visual_queries: List[Dict], markdown_report: str,
                            output_html_path: str):
        print(f"🎨 [5/5] 正在生成图表并渲染最终 HTML...")

        # 1. CSV 转 SQLite schema
        table_name = os.path.splitext(os.path.basename(csv_path))[0]
        # 注意: csv_to_sqlite 在 auto_viz2 中通常返回 schema 字符串
        schema = csv_to_sqlite(csv_path, table_name)

        # 2. 生成 SQL 并执行
        for ins in visual_queries:
            # 调用 LLM 将自然语言转 SQL
            ins["sql"] = nl_to_sql(ins["nl_query"], schema)

        # 3. 生成图表 HTML 片段 map
        # key: chart_id, value: <div>...</div>
        chart_map = visualize_result_to_map(visual_queries)

        # 4. 在 Markdown 中插入占位符
        available_ids = list(chart_map.keys())
        # 使用 md_chart 库处理插入逻辑
        markdown_with_placeholders = insert_chart_placeholders(markdown_report, available_ids)

        # 5. 生成最终 HTML
        # 这里实际上 ReportGenerator 会再次做替换，但 md_chart 可能做的是类似 [[chart1]] 的格式化
        final_html = self.report_gen.generate_html_report(markdown_with_placeholders, chart_map)

        with open(output_html_path, "w", encoding="utf-8") as f:
            f.write(final_html)

        print(f"✅ 成功！HTML 报告已保存为: {output_html_path}")

    # --- 总入口 ---
    def run(self, csv_path: str, user_query: str, output_html_path: str = "final_report.html"):
        # 1. 获取数据上下文
        context = self.generate_data_context(csv_path)

        # 2. 生成文字报告
        raw_report_text = self.generate_raw_report(context, user_query)

        # 3. 规划图表
        visual_queries = self.extract_visual_queries(raw_report_text)

        # 4. 生成带结构的 Markdown (此时只有文字引用)
        structured_md = self.structure_report(raw_report_text, visual_queries)

        # 5. 生成 SQL -> 图表 -> HTML
        self.generate_final_html(csv_path, visual_queries, structured_md, output_html_path)


# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 配置
    API_KEY = "sk-z38TPP3SlXtHNj3tsnf8rSEHS0xqKCQxglXHSUHlQzutV6rB"  # 请替换你的 Key
    BASE_URL = "https://www.chatgtp.cn/v1"  # 或你的 Base URL
    CSV_PATH="xiqi.csv"

    #USER_QUERY = "请分析各地区的销售趋势以及不同游戏类型的表现。"
    USER_QUERY = "我想要个详细的分析报告，生成的报告需要和数据集主题需匹配，忽略缺失值。"
    OUTPUT_FILE = "xiqi_analysis.html"

    # 初始化 Pipeline
    pipeline = AutoReportPipeline(api_key=API_KEY, base_url=BASE_URL)

    # 运行
    try:
        pipeline.run(CSV_PATH, USER_QUERY, OUTPUT_FILE)
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        import traceback

        traceback.print_exc()