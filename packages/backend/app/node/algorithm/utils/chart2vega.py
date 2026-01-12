import json
import os
import argparse
import sys
import re
from typing import Dict, Any, Optional
import openai
import requests

def get_python_to_vegalite_prompt(python_code: str) -> str:
    """生成用于将Python可视化代码转换为Vega-Lite的提示"""
    
    # 尝试读取data_context.json获取数据上下文
    data_context_str = ""
    try:
        json_path = os.path.join("storyteller", "dataset", "data_context.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data_context_dict = json.load(f)
                
                # 构建数据字段类型信息
                data_context_str = f"Dataset description: {data_context_dict.get('dataset_description', '')}\n\nField information:\n"
                
                for field, info in data_context_dict.get('fields_info', {}).items():
                    field_type = info.get('dtype', 'unknown')
                    semantic_type = info.get('semantic_type', '')
                    data_context_str += f"- {field}: type={field_type}, semantic_type={semantic_type}\n"
                
                print("✅ Successfully read data_context.json to provide field type information")
    except Exception as e:
        print(f"⚠️ Failed to read data_context.json: {str(e)}")
        data_context_str = ""  # 失败时使用空字符串

    # 使用以/storyteller开头的路径
    dataset_path = "/storyteller/dataset/co2-concentration.csv"

    prompt = """
You are an AI assistant specialized in data visualization, skilled at converting Python visualization code to Vega-Lite specifications.

Please analyze the following Python visualization code and convert it directly to an equivalent Vega-Lite JSON configuration, combining with the dataset description and field information.

# Code and Data Information to Convert
Python visualization code:
{python_code}

Dataset description:
{data_context_str}

# Conversion Requirements
Please carefully analyze the code's data processing, chart type, mappings, axes, titles and other settings to ensure the Vega-Lite configuration can completely reproduce the visualization effects of the Python code.

## 1. Format Requirements
- All strings must use double quotes, not single quotes: "text" instead of 'text'
- No comma after the last element in arrays or objects
- Use true/false for boolean values instead of True/False
- Ensure all brackets and braces are correctly paired and completely closed

## 2. Data Reference Handling
- Please use "data": {{"url": "{dataset_path}"}} to reference data
- You can also use "data": {{"values": [...] }} to provide inline data (when Python code explicitly creates static data)
- Do not create fake data or example data points
- Ensure all data processing operations from Python code are retained (such as grouping, aggregation, filtering, etc.)

## 3. Conversion Steps
1. Identify the visualization library used in the code (matplotlib, seaborn, altair, plotly, etc.)
2. Determine the chart type (bar chart, line chart, scatter plot, pie chart, box plot, etc.)
3. Analyze data processing logic (such as grouping, aggregation, filtering, etc.)
4. Extract key configurations (axis labels, legend settings, aggregation operations, color mappings, etc.)
5. Create complete Vega-Lite JSON specification

# Chart Type Processing Guidelines

## A. General Encoding Guidelines
In Vega-Lite, data transformation and aggregation are mainly implemented through two methods:
1. Set aggregation properties in the encoding object (suitable for simple operations)
```json
"encoding": {{
  "y": {{
    "field": "value",
    "aggregate": "mean"
  }}
}}
```

## B. Binning Operations
1. Simple uniform binning:
```json
"encoding": {{
  "x": {{
    "field": "Age",
    "bin": true,
    "type": "quantitative"
  }}
}}
```

2. Custom non-uniform binning:
```json
"transform": [
  {{
    "calculate": "datum.Age >= 18 && datum.Age < 30 ? '18-30' : datum.Age >= 30 ? '30+' : 'Other'",
    "as": "Age_Group"
  }}
],
"encoding": {{
  "x": {{
    "field": "Age_Group",
    "type": "nominal"
  }}
}}
```

3. Custom binning boundaries:
```json
"transform": [
  {{
    "bin": {{
      "field": "Age",
      "as": "age_bins",
      "extent": [18, 70],
      "steps": [18, 30, 45, 60, 70]
    }}
  }}
]
```

## C. Heatmap Processing
Heatmaps require special attention to the following points:

1. Basic structure:
```json
"mark": "rect",
"encoding": {{
  "x": {{ "field": "Category", "type": "nominal" }},
  "y": {{ "field": "Group", "type": "nominal" }},
  "color": {{ "field": "Value", "type": "quantitative" }}
}}
```

2. Display numeric labels (must use layers):
```json
"layer": [
  {{
    "mark": "rect",
    "encoding": {{ 
      "x": {{ "field": "Category", "type": "nominal" }},
      "y": {{ "field": "Group", "type": "nominal" }},
      "color": {{ "field": "Value", "type": "quantitative" }}
    }}
  }},
  {{
    "mark": {{ "type": "text", "fontSize": 12 }},
    "encoding": {{
      "x": {{ "field": "Category", "type": "nominal" }},
      "y": {{ "field": "Group", "type": "nominal" }},
      "text": {{ "field": "Value", "type": "quantitative" }},
      "color": {{
        "condition": {{ "test": "datum.Value < 10", "value": "black" }},
        "value": "white"
      }}
    }}
  }}
]
```

3. Color schemes (must use valid color scheme names):
```json
"color": {{
  "field": "Value",
  "type": "quantitative",
  "scale": {{
    "scheme": "blues"  // Refer to valid values in section E "Color Scheme Guidelines"
  }}
}}
```

4. Data aggregation:
```json
"transform": [
  {{
    "aggregate": [{{ "op": "count", "as": "Count" }}],
    "groupby": ["Category", "Group"]
  }}
]
```

## D. Other Common Chart Type Tips
- Bar chart: "mark": "bar"
- Line chart: "mark": "line"
- Scatter plot: "mark": "point"
- Box plot: "mark": "boxplot"
- Area chart: "mark": "area"
- Pie chart: "mark": "arc" + "theta" encoding

## E. Color Scheme Guidelines
All chart types need to pay attention to using correct color scheme names. Vega-Lite only supports the following color scheme names:

1. Categorical data color schemes (for nominal/ordinal data):
```json
"color": {{
  "field": "Category",
  "type": "nominal",
  "scale": {{
    "scheme": "category10"  // Color scheme suitable for categorical data
  }}
}}
```
Valid categorical color schemes include:
- `"category10"`, `"category20"`, `"category20b"`, `"category20c"` (default categorical colors)
- `"accent"`, `"dark2"`, `"paired"`, `"pastel1"`, `"pastel2"`, `"set1"`, `"set2"`, `"set3"`, `"tableau10"`, `"tableau20"`
- Note: Do not use `"pastel"` (invalid), should use `"pastel1"` or `"pastel2"`

2. Continuous data color schemes (for quantitative data):
```json
"color": {{
  "field": "Value",
  "type": "quantitative",
  "scale": {{
    "scheme": "blues"  // Color scheme suitable for continuous data
  }}
}}
```
Valid continuous color schemes include:
- Single color gradients: `"blues"`, `"greens"`, `"greys"`, `"oranges"`, `"purples"`, `"reds"`
- Multi-color gradients: `"viridis"`, `"inferno"`, `"magma"`, `"plasma"`, `"cividis"`, `"turbo"`
- Bipolar gradients: `"blueorange"`, `"brownbluegreen"`, `"purplegreen"`, 
"pinkyellowgreen", "redblue", "redgrey"

3. Custom color arrays:
```json
"color": {{
  "field": "Category",
  "type": "nominal",
  "scale": {{
    "range": ["#675193", "#ca8861", "#f2e029", "#a1dbb2"]  // Custom colors
  }}
}}
```

# Output Format
Please strictly follow the template format below to return the Vega-Lite configuration. Ensure the JSON format is completely valid, do not add any additional explanations, only return the JSON object:

{{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "title": "Chart title",
  "description": "Chart description",
  "data": {{"url": "{dataset_path}"}},
  "mark": "Chart type", 
  "encoding": {{
    "/* Encoding mappings, including data transformation operations */"
  }}
}}

!! Important Note: Before outputting this configuration, please check once more if there are any errors in the configuration. If there are errors, please correct them before outputting.
Finally, only return a valid JSON object, do not use Markdown format, do not add any explanatory text.
""".format(python_code=python_code, data_context_str=data_context_str, dataset_path=dataset_path)
    return prompt

def call_openai(prompt: str, **kwargs) -> str:
    """调用OpenAI API或兼容的API端点
    
    支持以下调用方法:
    1. 原生OpenAI API
    2. 兼容OpenAI API的自定义端点
    3. 通过requests直接调用API（适用于某些特殊场景）
    """
    try:
        print(f"🔄 API调用参数: model={kwargs.get('model', 'gpt-4-turbo')}, base_url={kwargs.get('base_url', '默认OpenAI')}")
        
        # 检查是否有指定的API端点
        base_url = kwargs.get('base_url')
        api_key = kwargs.get('api_key', os.environ.get("OPENAI_API_KEY", ""))
        model = kwargs.get('model', 'gpt-4-turbo')
        
        # 直接使用requests调用API（当提供了特定格式的base_url时）
        if base_url and (base_url.endswith('/chat/completions') or 'hkust-gz' in base_url):
            try:
                print(f"🔄 使用直接请求方式调用API: {base_url}")
                headers = {
                    "Content-Type": "application/json"
                }
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a data visualization expert."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": kwargs.get("temperature", 0.0),
                    "max_tokens": kwargs.get("max_tokens", 4096)
                }
                
                response = requests.post(
                    base_url,
                    headers=headers,
                    json=data
                )
                
                response_json = response.json()
                if response.status_code == 200 and 'choices' in response_json and response_json['choices']:
                    return response_json['choices'][0]['message']['content']
                else:
                    print(f"❌ API返回错误: {response.status_code} - {response_json}")
                    return ""
            except Exception as e:
                print(f"❌ 使用直接请求方式调用API失败: {str(e)}")
                print("⚠️ 尝试回退到OpenAI客户端方式")
        
        # 使用OpenAI客户端SDK调用API
        # 创建客户端参数
        client_kwargs = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        
        # 仅当base_url不是完整的chat/completions端点时才设置
        if base_url and not base_url.endswith('/chat/completions'):
            client_kwargs["base_url"] = base_url
        
        # 创建客户端
        client = openai.OpenAI(**client_kwargs)
        
        # 生成回答
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a data visualization expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=kwargs.get("temperature", 0.0),
            max_tokens=kwargs.get("max_tokens", 4096)
        )
        
        # 返回回答
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ 调用所有API方式都失败: {str(e)}")
        import traceback
        traceback.print_exc()
        



def convert_python_to_vegalite(python_code: str, llm_kwargs: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    使用LLM将Python可视化代码转换为Vega-Lite配置
    
    参数:
        python_code: Python可视化代码
        llm_kwargs: LLM调用参数
        
    返回:
        Vega-Lite配置对象或None（如果转换失败）
    """
    try:
        
        # 准备提示
        prompt = get_python_to_vegalite_prompt(python_code)
        
        # 处理llm_kwargs
        if llm_kwargs is None:
            llm_kwargs = {}
        
        # 确保必要的参数存在
        if not llm_kwargs.get("model"):
            llm_kwargs["model"] = "gpt-4-turbo"
        
        # 设置低温度以获得更确定的结果
        llm_kwargs["temperature"] = 0.0
        llm_kwargs["max_tokens"] = llm_kwargs.get("max_tokens", 4096)
        
        print(f"🔍 调用LLM ({llm_kwargs.get('model')})将Python代码转换为Vega-Lite配置...")
        print(f"   使用base_url: {llm_kwargs.get('base_url', '默认')}")
        
        # 调用LLM
        response = call_openai(prompt, **llm_kwargs)
        
        # 提取JSON内容
        json_content = extract_json_from_response(response)
        if json_content:
            # 验证并修复配色方案
            json_content = validate_and_fix_color_schemes(json_content)
            return json_content
            
        
    except Exception as e:
        print(f"❌ 转换代码时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """从LLM响应中提取JSON内容"""
    if not response:
        print("❌ LLM返回了空响应")
        return None
    
    # 记录原始响应便于调试
    print("📝 LLM原始响应:")
    print(response)
    
    # 尝试多种方式提取和解析JSON
    try:
        # 首先尝试使用更安全的json解析方式
        try:
            # 使用eval方式解析，这对于包含$schema的JSON更友好
            # 先检查响应是否是一个完整的JSON对象
            if response.strip().startswith('{') and response.strip().endswith('}'):
                # 用更灵活的方式解析
                import ast
                # 将$schema中的$替换为临时标记，以避免Python解析问题
                temp_response = response.replace('$schema', '__DOLLAR_SCHEMA__')
                # 替换JSON布尔值为Python格式
                temp_response = re.sub(r'\btrue\b', 'True', temp_response)
                temp_response = re.sub(r'\bfalse\b', 'False', temp_response)
                # 使用ast.literal_eval解析（更安全的eval）
                parsed_dict = ast.literal_eval(temp_response)
                # 恢复$schema
                if '__DOLLAR_SCHEMA__' in parsed_dict:
                    parsed_dict['$schema'] = parsed_dict.pop('__DOLLAR_SCHEMA__')
                return parsed_dict
        except (SyntaxError, ValueError) as e:
            print(f"⚠️ 安全解析方式失败: {str(e)}")
            
        # 1. 检查是否存在markdown代码块，优先提取
        if "```" in response:
            markdown_pattern = r'```(?:json)?(.*?)```'
            matches = re.findall(markdown_pattern, response, re.DOTALL)
            if matches:
                for match in matches:
                    json_content = match.strip()
                    try:
                        # 使用自定义的安全解析方法
                        return safe_parse_json(json_content)
                    except Exception as e:
                        print(f"⚠️ Markdown代码块解析失败: {str(e)}")
        
        # 2. 尝试直接将整个响应作为JSON解析
        try:
            return safe_parse_json(response.strip())
        except Exception as e:
            print(f"⚠️ 直接解析响应失败: {str(e)}")
            
        # 3. 尝试清理后解析
        clean_json = clean_json_content(response)
        try:
            return safe_parse_json(clean_json)
        except Exception as e:
            print(f"⚠️ 清理后解析失败: {str(e)}")
            
        # 4. 尝试提取大括号内的内容
        json_match = re.search(r'(\{.*\})', response, re.DOTALL)
        if json_match:
            extracted_json = json_match.group(0)
            try:
                return safe_parse_json(extracted_json)
            except Exception as e:
                print(f"⚠️ 提取大括号内容解析失败: {str(e)}")
                
        print("❌ 所有JSON解析尝试都失败了")
        return None
        
    except Exception as e:
        print(f"❌ 提取JSON时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def safe_parse_json(json_str: str) -> Dict[str, Any]:
    """安全解析JSON，处理包含$符号的情况和true/false布尔值"""
    
    # 先判断是否包含$schema
    has_dollar_schema = '"$schema"' in json_str
    
    if has_dollar_schema:
        # 替换$schema为一个安全的临时标记
        json_str = json_str.replace('"$schema"', '"__DOLLAR_SCHEMA__"')
    
    # 尝试解析修改后的JSON
    try:
        import json
        parsed = json.loads(json_str)
        
        # 恢复$schema键
        if has_dollar_schema and '__DOLLAR_SCHEMA__' in parsed:
            parsed['$schema'] = parsed.pop('__DOLLAR_SCHEMA__')
        
        return parsed
    except Exception as e:
        # 如果直接解析失败，尝试更多的替换
        try:
            # 使用正则表达式找出所有可能带$的键
            dollar_keys = re.findall(r'"(\$[^"]+)"', json_str)
            
            temp_json = json_str
            replacements = {}
            
            # 替换所有带$的键
            for key in dollar_keys:
                temp_key = f"__DOLLAR_{key[1:]}"
                replacements[temp_key] = key
                temp_json = temp_json.replace(f'"{key}"', f'"{temp_key}"')
            
            # 解析替换后的JSON
            import json
            parsed = json.loads(temp_json)
            
            # 恢复所有原始键
            for temp_key, original_key in replacements.items():
                if temp_key in parsed:
                    parsed[original_key] = parsed.pop(temp_key)
            
            return parsed
        except Exception as e:
            # 最后的备用方法：使用ast
            try:
                # 使用ast.literal_eval，但先处理true/false
                import ast
                
                # 替换JSON布尔值为Python格式
                temp_str = re.sub(r'\btrue\b', 'True', json_str)
                temp_str = re.sub(r'\bfalse\b', 'False', temp_str)
                
                # 替换所有带$的部分以避免eval问题
                temp_str = re.sub(r'"(\$[^"]+)"', r'"__DOLLAR_\1"', temp_str)
                temp_str = temp_str.replace('$', '__DOLLAR__')
                
                # 解析
                parsed_dict = ast.literal_eval(temp_str)
                
                # 恢复所有$相关的键
                for key in list(parsed_dict.keys()):
                    if key.startswith('__DOLLAR_'):
                        original_key = '$' + key[9:]  # 移除 '__DOLLAR_'
                        parsed_dict[original_key] = parsed_dict.pop(key)
                
                return parsed_dict
            except Exception as final_e:
                print(f"❌ JSON解析最终失败: {str(final_e)}")
                raise  # 如果所有方法都失败，抛出异常

def validate_and_fix_color_schemes(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证并修复Vega-Lite配置中的配色方案名称
    
    参数：
        config: Vega-Lite配置对象
        
    返回：
        修复后的配置对象
    """
    # 有效的分类配色方案列表
    categorical_schemes = [
        "category10", "category20", "category20b", "category20c", 
        "accent", "dark2", "paired", "pastel1", "pastel2", 
        "set1", "set2", "set3", "tableau10", "tableau20"
    ]
    
    # 有效的连续配色方案列表
    sequential_schemes = [
        # 单色渐变
        "blues", "greens", "greys", "oranges", "purples", "reds",
        # 多色渐变
        "viridis", "inferno", "magma", "plasma", "cividis", "turbo",
        # 双极渐变
        "blueorange", "brownbluegreen", "purplegreen", 
        "pinkyellowgreen", "redblue", "redgrey"
    ]
    
    # 常见的错误配色方案映射到正确的配色方案
    correction_map = {
        "pastel": "pastel1",
        "ylgnbu": "blues",
        "ylgn": "greens",
        "rdbu": "redblue",
        "rdgy": "redgrey",
        "rdpu": "purples",
        "rdyl": "redyellow",
        "heat": "inferno",
        "spectral": "viridis",
        "rainbow": "turbo",
        "blue": "blues",
        "green": "greens",
        "grey": "greys",
        "gray": "greys",
        "orange": "oranges",
        "purple": "purples",
        "red": "reds",
        "cat10": "category10",
        "cat20": "category20",
        "pastel1": "pastel1",  # 已经正确，保持不变
        "pastel2": "pastel2"   # 已经正确，保持不变
    }
    
    # 递归检查所有键值对
    def check_color_scheme(obj):
        if isinstance(obj, dict):
            # 检测是否为配色方案定义
            if "scale" in obj and isinstance(obj["scale"], dict) and "scheme" in obj["scale"]:
                scheme = obj["scale"]["scheme"]
                if isinstance(scheme, str):
                    # 检查是否需要修正
                    scheme_lower = scheme.lower()
                    if scheme_lower in correction_map:
                        corrected = correction_map[scheme_lower]
                        print(f"⚠️ 修正配色方案: {scheme} -> {corrected}")
                        obj["scale"]["scheme"] = corrected
                    elif scheme_lower not in categorical_schemes and scheme_lower not in sequential_schemes:
                        # 如果不在有效列表中，使用fallback
                        print(f"⚠️ 未知配色方案 {scheme}，使用 'category10' 替代")
                        obj["scale"]["scheme"] = "category10"
            
            # 递归检查所有子对象
            for key, value in obj.items():
                obj[key] = check_color_scheme(value)
        
        elif isinstance(obj, list):
            # 递归检查所有列表项
            for i, item in enumerate(obj):
                obj[i] = check_color_scheme(item)
        
        return obj
    
    # 开始验证和修复
    print(f"🔍 检查和修复配色方案...")
    return check_color_scheme(config)

def clean_json_content(json_str: str) -> str:
    """清理JSON内容，移除注释和其他非JSON元素"""
    # 移除单行注释 (// ...)
    json_str = re.sub(r'//.*?($|\n)', '', json_str)
    
    # 移除多行注释 (/* ... */)
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # 移除尾部逗号
    json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)
    
    # 移除可能的markdown标记
    json_str = re.sub(r'^```json|```$', '', json_str, flags=re.MULTILINE).strip()
    
    return json_str

def save_vegalite_config(config: Dict[str, Any], output_path: str) -> None:
    """保存Vega-Lite配置到文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Vega-Lite配置已保存到: {output_path}")
    except Exception as e:
        print(f"❌ 保存配置时出错: {str(e)}")

def create_html_viewer(config: Dict[str, Any], output_path: str) -> None:
    """创建一个包含Vega-Lite可视化的HTML文件
    
    使用配置中指定的数据集URL，不再内联数据
    """
    if not config:
        print("❌ 无法创建HTML查看器：配置为空")
        return
    
    # 确保配置中包含正确的数据引用
    if "data" not in config or "url" not in config["data"]:
        config["data"] = {"url": "/storyteller/dataset/shopping.csv"}
    else:
        # 如果已有url，确保使用正确的格式
        current_url = config["data"]["url"]
        if not current_url.startswith("/storyteller/"):
            config["data"]["url"] = "/storyteller/dataset/shopping.csv"

    # 获取图表类型，处理mark是字典或字符串的情况
    chart_type = config.get("mark", "未知图表类型")
    if isinstance(chart_type, dict):
        chart_type = chart_type.get("type", "未知图表类型")
    
    # 美化的HTML模板，使用现代CSS样式
    html_template = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <title>Vega-Lite 数据可视化</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
        <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
        <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
        <style>
            :root {
                --primary-color: #4285f4;
                --secondary-color: #34a853;
                --background-color: #f8f9fa;
                --text-color: #202124;
                --card-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }
            
            body {
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                background-color: var(--background-color);
                color: var(--text-color);
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }
            
            header {
                text-align: center;
                padding: 20px 0;
                margin-bottom: 30px;
                border-bottom: 1px solid #e0e0e0;
            }
            
            h1 {
                color: var(--primary-color);
                margin: 0;
                font-weight: 500;
            }
            
            .subtitle {
                color: #5f6368;
                margin-top: 10px;
            }
            
            .visualization-card {
                background-color: white;
                border-radius: 8px;
                box-shadow: var(--card-shadow);
                overflow: hidden;
                margin-bottom: 30px;
            }
            
            .card-header {
                padding: 15px 20px;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .card-title {
                margin: 0;
                color: var(--text-color);
                font-size: 1.2rem;
                font-weight: 500;
            }
            
            .card-body {
                padding: 20px;
                min-height: 400px;
            }
            
            #vis {
                width: 100%;
                height: 100%;
            }
            
            footer {
                text-align: center;
                padding: 20px 0;
                font-size: 0.9rem;
                color: #5f6368;
                border-top: 1px solid #e0e0e0;
                margin-top: 30px;
            }
            
            .badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 12px;
                background-color: var(--secondary-color);
                color: white;
                font-size: 0.8rem;
                margin-left: 10px;
            }
            
            @media (max-width: 768px) {
                .container {
                    padding: 10px;
                }
                
                .card-body {
                    min-height: 300px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Python代码转换的Vega-Lite可视化</h1>
                <p class="subtitle">通过chart2vega工具自动转换</p>
            </header>
            
            <div class="visualization-card">
                <div class="card-header">
                    <h2 class="card-title">{chart_title} <span class="badge">{chart_type}</span></h2>
                </div>
                <div class="card-body">
                    <div id="vis"></div>
                </div>
            </div>
            
            <footer>
                <p>由LIDA框架自动生成 | 使用Vega-Lite渲染</p>
            </footer>
        </div>
        
        <script type="text/javascript">
            const spec = {config_json};
            
            vegaEmbed('#vis', spec, {
                renderer: 'canvas',
                actions: true,
                theme: 'light'
            }).then(result => console.log('可视化加载成功')).catch(error => console.error('可视化加载失败:', error));
        </script>
    </body>
    </html>
    """
    
    try:
        # 准备模板变量
        chart_title = config.get("title", "数据可视化")
        
        # 转换为JSON字符串
        config_json = json.dumps(config, ensure_ascii=False)
        
        # 替换模板变量
        html_content = html_template.replace('{config_json}', config_json)
        html_content = html_content.replace('{chart_title}', chart_title)
        html_content = html_content.replace('{chart_type}', str(chart_type))
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML查看器已保存到: {output_path}")
    except Exception as e:
        print(f"❌ 创建HTML查看器时出错: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description='将Python可视化代码转换为Vega-Lite配置')
    parser.add_argument('input_file', help='包含Python可视化代码的输入文件路径')
    parser.add_argument('--output', '-o', help='Vega-Lite配置输出文件路径', default='vegalite_output.json')
    parser.add_argument('--html', help='HTML查看器输出文件路径', default='vegalite_viewer.html')
    parser.add_argument('--model', '-m', help='使用的LLM模型（默认为gpt-4-turbo）', default='gpt-4-turbo')
    parser.add_argument('--base-url', '-b', help='API基础URL', default=None)
    parser.add_argument('--api-key', '-k', help='API密钥', default=None)
    parser.add_argument('--no-html', action='store_true', help='不生成HTML查看器')
    
    args = parser.parse_args()
    
    # 读取Python代码
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            python_code = f.read()
    except Exception as e:
        print(f"❌ 读取Python代码文件时出错: {str(e)}")
        return
    
    # 转换为Vega-Lite
    llm_kwargs = {
        "model": args.model
    }
    if args.base_url:
        llm_kwargs["base_url"] = args.base_url
    if args.api_key:
        llm_kwargs["api_key"] = args.api_key
        
    vegalite_config = convert_python_to_vegalite(python_code, llm_kwargs=llm_kwargs)
    if vegalite_config:
        # 保存配置
        save_vegalite_config(vegalite_config, args.output)
        
        # 生成HTML查看器
        if not args.no_html:
            create_html_viewer(vegalite_config, args.html)
    else:
        print("❌ 转换失败")

if __name__ == "__main__":
    main() 