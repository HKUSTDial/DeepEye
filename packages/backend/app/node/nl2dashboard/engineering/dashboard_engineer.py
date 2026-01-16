"""Dashboard 工程实现器

负责根据设计结果实现 Dashboard。
参考 va_system_builder.py 的实现流程。
"""

import json
import os
import re
import shutil
import glob
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..llm_compat import LLMClient, Message
from .prompt import LAYOUT_POSITION_GENERATION_PROMPT


class DashboardEngineer:
    """Dashboard 工程实现器
    
    根据设计结果，生成实际的 Dashboard 代码或配置文件。
    参考 va_system_builder.py 的 _build_va_system 方法实现。
    
    Attributes:
        design_result: 设计结果字典
        output_path: 输出路径
        llm_client: LLM 客户端
        page_theme_content: 页面主题内容（用于图表美化）
    
    Example:
        >>> engineer = DashboardEngineer(llm_client=llm_client)
        >>> engineer.implement(design_result, output_path, info_doc)
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None, model: str = "gpt-4o"):
        """初始化工程实现器
        
        Args:
            llm_client: LLM 客户端（可选，如果为None则从环境变量获取）
            model: 使用的模型名
        """
        self.design_result: Optional[Dict[str, Any]] = None
        self.output_path: Optional[str] = None
        self.page_theme_content: str = ""
        
        # 加载模板映射配置
        self.template_mapping = self._load_template_mapping()
        
        # 初始化 LLM 客户端
        if llm_client is None:
            import os
            api_key = os.getenv("DEEPEYE_LLM_API_KEY")
            base_url = os.getenv("DEEPEYE_LLM_BASE_URL", "https://api.openai.com/v1")
            env_model = os.getenv("DEEPEYE_LLM_MODEL", model)
            
            if api_key:
                self.llm_client = LLMClient(api_key=api_key, base_url=base_url)
                self.llm_model = env_model
            else:
                self.llm_client = None
                self.llm_model = env_model
        else:
            self.llm_client = llm_client
            self.llm_model = model  # 使用传入的模型名
    
    def implement(
        self,
        design_result: Dict[str, Any],
        output_path: str,
        info_doc: Dict[str, Any]
    ) -> str:
        """实现 Dashboard
        
        参考 va_system_builder.py 的 _build_va_system 方法实现。
        
        Args:
            design_result: 设计结果字典，包含：
                - layout: Dashboard 布局结构
                - charts: 图表配置列表
                - filters: 过滤器配置
                - metadata: 设计元数据
            output_path: 输出路径
            info_doc: 信息文档，包含：
                - question: 用户问题
                - dataset_path: 数据集路径
                - output_path: 输出路径
                - data_schema: 数据schema信息
        
        Returns:
            实现的 Dashboard 文件路径（va_app 目录路径）
        """
        self.design_result = design_result
        self.output_path = output_path
        
        # 提取信息
        question = info_doc.get("question", "")
        dataset_path = info_doc.get("dataset_path", "")
        
        # 构建 VA 系统
        va_app_path = self._build_va_system(
            output_path=output_path,
            dataset_path=dataset_path,
            question=question,
            design_result=design_result
        )
        
        return va_app_path
    
    def _build_va_system(
        self,
        output_path: str,
        dataset_path: str,
        question: str,
        design_result: Dict[str, Any]
    ) -> str:
        """构建VA系统的核心实现
        
        参考 va_system_builder.py 的 _build_va_system 方法。
        
        实现步骤：
        1. 前置文件的处理：模板复制、数据集复制、配置文件生成、配置路径更新
        2. 配置文件的处理：个性化布局实现、Filter组件数据绑定
        3. 页面模板美化：基于问题主题生成个性化页面样式
        4. 图表美化：基于页面主题美化图表样式
        
        Args:
            output_path: 输出路径
            dataset_path: 数据集路径
            question: 用户问题
            design_result: 设计结果
        
        Returns:
            va_app 目录路径
        """
        # ========== 步骤 1: 前置文件的处理 ==========
        # 1.1 从模板目录克隆整个文件到output_path下
        template_path = os.path.join(os.path.dirname(__file__), 'template')
        template_path = os.path.abspath(template_path)
        
        # 创建目标目录下的va_app文件夹
        va_app_path = os.path.join(output_path, 'va_app')
        if os.path.exists(va_app_path):
            shutil.rmtree(va_app_path)
        shutil.copytree(template_path, va_app_path)
        
        # 1.2 从设计结果中查找图表代码目录
        echart_source = None
        if 'charts_directory' in design_result:
            charts_dir = design_result['charts_directory']
            if os.path.isabs(charts_dir):
                echart_source = os.path.join(charts_dir, 'echart_code') if os.path.exists(charts_dir) else None
            else:
                echart_source = os.path.join(output_path, charts_dir, 'echart_code')
        
        # 如果设计结果中没有指定，尝试查找默认位置
        if not echart_source or not os.path.exists(echart_source):
            # 查找 visualizations_* 目录
            viz_charts_dirs = glob.glob(os.path.join(output_path, 'visualizations_*'))
            if viz_charts_dirs:
                # 使用最新的一个
                viz_charts_dirs.sort(reverse=True)
                echart_source = os.path.join(viz_charts_dirs[0], 'echart_code')
        
        charts_dest = os.path.join(va_app_path, 'public', 'charts')
        
        if echart_source and os.path.exists(echart_source):
            # 检测并生成HTML文件（如果不存在）
            # print(f"🔧 Generating HTML from Python charts...")
            # self._generate_html_from_python_charts(
            #     echart_source_dir=echart_source,
            #     dataset_path=dataset_path,
            #     max_workers=4
            # )
            
            # 清空目标charts目录
            if os.path.exists(charts_dest):
                shutil.rmtree(charts_dest)
            os.makedirs(charts_dest)
            
            # 复制所有echart文件并处理
            print(f"📋 Processing and copying chart files...")
            for file in os.listdir(echart_source):
                src_file = os.path.join(echart_source, file)
                dst_file = os.path.join(charts_dest, file)
                if os.path.isfile(src_file) and file.endswith('.html'):
                    # 读取、处理并写入HTML文件
                    self._process_echart_html(src_file, dst_file)
                elif os.path.isfile(src_file):
                    # 非HTML文件直接复制
                    shutil.copy2(src_file, dst_file)
            print(f"✓ Processed echart code from {echart_source}")
        
        # 1.3 复制 dashboard_config.json 到 va_app/public/configs 下
        # 这个文件是由 DashboardDesigner.save_design() 生成的
        configs_dest = os.path.join(va_app_path, 'public', 'configs')
        
        # 查找配置文件（可能是 dashboard_config.json 或 dashboard_config_*.json）
        config_files = []
        dashboard_config_path = os.path.join(output_path, 'dashboard_config.json')
        if os.path.exists(dashboard_config_path):
            config_files.append(dashboard_config_path)
        else:
            # 查找带时间戳的配置文件
            config_pattern = os.path.join(output_path, 'dashboard_config_*.json')
            config_files = glob.glob(config_pattern)
        
        config_file = None
        dashboard_config_filename = None
        
        if config_files:
            # 使用第一个找到的配置文件
            source_config = config_files[0]
            dashboard_config_filename = os.path.basename(source_config)
            config_file = os.path.join(configs_dest, dashboard_config_filename)
            
            shutil.copy2(source_config, config_file)
            print(f"✓ Copied config file: {dashboard_config_filename}")
            
            # 更新配置文件中的 python_code_name 和 html_code_name 字段
            if os.path.exists(charts_dest):
                print(f"🔧 Updating config with HTML names...")
                self._update_config_with_html_names(config_file, charts_dest)
        else:
            print(f"⚠️  No dashboard_config.json found in {output_path}, generating from design_result...")
            # 如果找不到配置文件，从 design_result 生成
            config_file = self._generate_dashboard_config(design_result, va_app_path)
            if config_file:
                dashboard_config_filename = os.path.basename(config_file)
                if os.path.exists(charts_dest):
                    self._update_config_with_html_names(config_file, charts_dest)
        
        # 1.4 复制数据集到va_app/public/data下
        if dataset_path and os.path.exists(dataset_path):
            data_dest = os.path.join(va_app_path, 'public', 'data')
            filename = os.path.basename(dataset_path)
            dst_file = os.path.join(data_dest, filename)
            shutil.copy2(dataset_path, dst_file)
            print(f"✓ Copied dataset to {dst_file}")
        
        # 1.5 更新app.py中的schema_path配置，指向配置文件
        if dashboard_config_filename:
            app_py_path = os.path.join(va_app_path, 'app.py')
            self._update_app_config(app_py_path, dashboard_config_filename)
        
        # ========== 步骤 2: 配置文件的处理 ==========
        if config_file and self.llm_client:
            # 2.1 个性化布局实现：生成Layout和Position信息
            # 2.2 Filter组件数据绑定：为Filter组件生成Options
            print(f"🔧 Processing dashboard config (layout + filter options)...")
            self._process_dashboard_config(
                config_file_path=config_file,
                dataset_path=dataset_path,
                question=question,
                va_app_path=va_app_path,
                max_retries=3
            )
        
        # ========== 步骤 3: 页面模板美化 ==========
        # 根据配置中的highlight块和图表数量动态选择模板
        selected_template = self._select_template_by_config(config_file)
        print(f"🎨 Applying {selected_template} with variable substitution...")
        template_success = self._apply_template_with_substitution(
            template_name=selected_template,
            va_app_path=va_app_path,
            question=question,
            config_file=config_file
        )
        
        # 如果页面模板应用成功，更新配置文件中的pageTemplate路径
        if template_success and config_file:
            print(f"🔧 Updating page template path in config...")
            self._update_page_template_config(config_file)
        
        return va_app_path
    
    def _generate_dashboard_config(
        self,
        design_result: Dict[str, Any],
        va_app_path: str
    ) -> Optional[str]:
        """生成 Dashboard 配置文件
        
        Args:
            design_result: 设计结果
            va_app_path: VA应用路径
        
        Returns:
            配置文件路径
        """
        configs_dest = os.path.join(va_app_path, 'public', 'configs')
        
        # 从设计结果生成配置
        config = {
            "layout": design_result.get("layout", {}),
            "blocks": design_result.get("blocks", [])
        }
        
        # 添加 dataSource 信息（必需，否则 app.py 无法找到数据文件）
        if "dataSource" in design_result:
            data_source = design_result["dataSource"].copy()
            # 将绝对路径转换为相对于 va_app 的路径
            if "path" in data_source and os.path.isabs(data_source["path"]):
                # 数据文件应该在 public/data/ 下
                filename = os.path.basename(data_source["path"])
                data_source["path"] = f"/data/{filename}"
            config["dataSource"] = data_source
        
        # 如果没有 blocks，尝试从旧格式的 charts 和 filters 生成
        if not config["blocks"]:
            # 添加图表块
            charts = design_result.get("charts", [])
            for i, chart in enumerate(charts):
                config["blocks"].append({
                    "id": f"chart_{i}",
                    "blockType": "view",
                    "blockContent": {
                        "description": chart.get("title", ""),
                        "html_code_name": f"chart_{i}.html"
                    }
                })
            
            # 添加过滤器块
            filters = design_result.get("filters", [])
            for i, filter_config in enumerate(filters):
                config["blocks"].append({
                    "id": f"filter_{i}",
                    "blockType": "filter",
                    "blockContent": {
                        "field": filter_config.get("field", ""),
                        "type": filter_config.get("type", "select"),
                        "options": []
                    }
                })
        
        # 保存配置
        config_file = os.path.join(configs_dest, 'dashboard_config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # print(f"✓ Generated dashboard config with {len(config.get('blocks', []))} blocks")
        
        return config_file
    
    def _process_dashboard_config(
        self,
        config_file_path: str,
        dataset_path: str,
        question: str,
        va_app_path: str,
        max_retries: int = 3
    ):
        """处理仪表板配置：添加Filter Options、Layout和Position信息
        
        参考 va_system_builder.py 的 _process_dashboard_config 方法。
        
        Args:
            config_file_path: 配置文件路径
            dataset_path: 数据集路径
            question: 用户问题
            va_app_path: VA应用路径
            max_retries: 最大重试次数
        """
        if not self.llm_client:
            return
        
        try:
            # 读取配置文件
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 1. 为Filter组件生成Options和Range
            if dataset_path and os.path.exists(dataset_path):
                try:
                    import pandas as pd
                    import numpy as np
                    df = pd.read_csv(dataset_path)
                    
                    if 'blocks' in config:
                        for block in config['blocks']:
                            if block.get('blockType') == 'filter' and 'blockContent' in block:
                                field = block['blockContent'].get('field')
                                control_type = block['blockContent'].get('controlType', 'select')
                                if field and field in df.columns:
                                    # 对于 date_range 类型，生成日期格式的 range 配置
                                    if control_type == 'date_range':
                                        try:
                                            # 尝试将字段转换为日期类型
                                            date_series = pd.to_datetime(df[field], errors='coerce').dropna()
                                            
                                            if len(date_series) > 0:
                                                min_date = date_series.min()
                                                max_date = date_series.max()
                                                
                                                # 格式化为日期字符串
                                                # 检查是否只有日期部分（时间为 00:00:00）
                                                if min_date.hour == 0 and min_date.minute == 0 and min_date.second == 0:
                                                    min_date_str = min_date.strftime('%Y/%m/%d')
                                                else:
                                                    min_date_str = min_date.strftime('%Y/%m/%d %H:%M:%S')
                                                
                                                if max_date.hour == 0 and max_date.minute == 0 and max_date.second == 0:
                                                    max_date_str = max_date.strftime('%Y/%m/%d')
                                                else:
                                                    max_date_str = max_date.strftime('%Y/%m/%d %H:%M:%S')
                                                
                                                # 设置 date_range 的 range
                                                block['blockContent']['range'] = {
                                                    'min': min_date_str,
                                                    'max': max_date_str
                                                }
                                                
                                                # 移除不需要的 options
                                                if 'options' in block['blockContent']:
                                                    del block['blockContent']['options']
                                                
                                                print(f"  ✓ Set date_range for {field}: {min_date_str} ~ {max_date_str}")
                                        except Exception as e:
                                            print(f"  ⚠️  Failed to process date_range for {field}: {e}")
                                            pass
                                    # 对于 slider 或 range 类型，生成 range 配置
                                    elif control_type in ('slider', 'range'):
                                        try:
                                            # 判断是否为时间字段
                                            is_time_field = 'time' in field.lower() or 'hour' in field.lower()
                                            
                                            if is_time_field:
                                                # 时间字段：从时间字符串中提取小时数
                                                def extract_hour(time_str):
                                                    if pd.isna(time_str):
                                                        return None
                                                    time_str = str(time_str).strip()
                                                    if ':' in time_str:
                                                        hour_str = time_str.split(':')[0]
                                                        try:
                                                            return int(hour_str)
                                                        except ValueError:
                                                            return None
                                                    return None
                                                
                                                values = df[field].apply(extract_hour).dropna()
                                            else:
                                                # 数值字段：尝试转换为数值
                                                values = pd.to_numeric(df[field], errors='coerce').dropna()
                                            
                                            if len(values) > 0:
                                                min_val = float(values.min())
                                                max_val = float(values.max())
                                                
                                                # 计算合适的 step
                                                if is_time_field:
                                                    step = 1  # 时间字段步长为1小时
                                                else:
                                                    # 对于数值字段，根据范围自动计算step
                                                    range_size = max_val - min_val
                                                    if range_size <= 10:
                                                        step = 0.1
                                                    elif range_size <= 100:
                                                        step = 1
                                                    elif range_size <= 1000:
                                                        step = 10
                                                    elif range_size <= 10000:
                                                        step = 100
                                                    else:
                                                        step = max(1, int(range_size / 100))  # 大约100个步长
                                                
                                                # 设置 slider 的 range
                                                block['blockContent']['range'] = {
                                                    'min': min_val,
                                                    'max': max_val,
                                                    'step': step
                                                }
                                                
                                                # 移除不需要的 options
                                                if 'options' in block['blockContent']:
                                                    del block['blockContent']['options']
                                                
                                                print(f"  ✓ Set slider range for {field}: {min_val}-{max_val} (step: {step})")
                                            else:
                                                print(f"  ⚠️  No valid values found for slider field {field}")
                                        except Exception as e:
                                            print(f"  ⚠️  Failed to process slider for {field}: {e}")
                                            pass
                                    else:
                                        # 对于非slider类型，生成options
                                        unique_values = df[field].dropna().unique().tolist()
                                        # 限制最多50个选项
                                        if len(unique_values) > 50:
                                            unique_values = unique_values[:50]
                                        # 对于 multiselect 类型不添加 "All" 选项
                                        if control_type == 'multiselect':
                                            options = [str(v) for v in unique_values]
                                        else:
                                            # 其他类型（select, checkbox等）添加 "All" 选项
                                            options = ["All"] + [str(v) for v in unique_values]
                                        block['blockContent']['options'] = options
                except Exception as e:
                    # 如果读取数据集失败，跳过
                    print(f"  ⚠️  Failed to process filters: {e}")
                    pass
            
            # 2. 读取图表HTML文件的尺寸信息
            chart_dimensions = self._extract_chart_dimensions(config, va_app_path)
            chart_dimensions_str = self._format_chart_dimensions(chart_dimensions)
            
            # 3. 使用LLM生成Layout和Position信息（带重试机制）
            from .prompt import LAYOUT_POSITION_GENERATION_PROMPT
            
            config_json_str = json.dumps(config, ensure_ascii=False, indent=2)
            prompt = LAYOUT_POSITION_GENERATION_PROMPT.format(
                config_json=config_json_str,
                chart_dimensions=chart_dimensions_str
            )
            
            updated_config = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    # 调用 LLM
                    messages = [Message(role="user", content=prompt)]
                    response = self.llm_client.generate(
                        messages,
                        model=self.llm_model,
                        temperature=0.0,
                        max_tokens=8192
                    )
                    
                    response_content = response.content
                    
                    # 尝试提取JSON
                    json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
                    if json_match:
                        response_content = json_match.group(1)
                    elif '```' in response_content:
                        # 如果有代码块但不是json标记
                        response_content = re.sub(r'```\w*\s*|\s*```', '', response_content)
                    
                    response_content = response_content.strip()
                    
                    # 尝试解析JSON
                    try:
                        updated_config = json.loads(response_content)
                        break  # 成功解析，跳出重试循环
                    except json.JSONDecodeError:
                        # 尝试修复常见问题
                        response_fixed = re.sub(r',\s*}', '}', response_content)
                        response_fixed = re.sub(r',\s*\]', ']', response_fixed)
                        
                        try:
                            updated_config = json.loads(response_fixed)
                            break
                        except json.JSONDecodeError:
                            if attempt < max_retries:
                                prompt = f"{prompt}\n\nIMPORTANT: Please return ONLY valid JSON, no explanations."
                            else:
                                # 使用默认配置
                                updated_config = config
                                if 'layout' not in updated_config:
                                    updated_config['layout'] = {
                                        "type": "grid",
                                        "columns": 3,
                                        "gap": 1.0,
                                        "pageTemplate": "public/templates/page_default.html"
                                    }
                
                except Exception as e:
                    if attempt >= max_retries:
                        # 使用默认配置
                        updated_config = config
                        if 'layout' not in updated_config:
                            updated_config['layout'] = {
                                "type": "grid",
                                "columns": 3,
                                "gap": 1.0,
                                "pageTemplate": "public/templates/page_default.html"
                            }
            
            # 如果所有尝试都失败，使用默认配置
            if updated_config is None:
                updated_config = config
                if 'layout' not in updated_config:
                    updated_config['layout'] = {
                        "type": "grid",
                        "columns": 3,
                        "gap": 1.0,
                        "pageTemplate": "public/templates/page_default.html"
                    }
            
            # 为每个block添加默认position（如果没有）
            if 'blocks' in updated_config:
                row = 1
                col = 1
                for block in updated_config['blocks']:
                    if 'position' not in block and block.get('blockType') in ['highlight', 'view']:
                        block['position'] = {
                            "col": col,
                            "row": row,
                            "span": 1,
                            "rowSpan": 1
                        }
                        col += 1
                        if col > 3:
                            col = 1
                            row += 1
            
            # 保存更新后的配置
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_config, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            # 如果处理失败，继续执行
            pass
    
    def _extract_chart_dimensions(self, config: dict, va_app_path: str) -> dict:
        """从HTML文件中提取图表的尺寸信息
        
        参考 va_system_builder.py 的 _extract_chart_dimensions 方法。
        
        Args:
            config: 配置文件字典
            va_app_path: VA应用路径
        
        Returns:
            字典，格式为 {block_id: {"width": int, "height": int, "aspect_ratio": float, "html_file": str}}
        """
        dimensions = {}
        charts_dir = os.path.join(va_app_path, 'public', 'charts')
        
        if 'blocks' not in config or not os.path.exists(charts_dir):
            return dimensions
        
        for block in config['blocks']:
            if block.get('blockType') != 'view':
                continue
            
            block_id = block.get('id') or block.get('blockId')
            block_content = block.get('blockContent', {})
            html_file = block_content.get('html_code_name')
            
            if not html_file or not block_id:
                continue
            
            html_path = os.path.join(charts_dir, html_file)
            
            if not os.path.exists(html_path):
                continue
            
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 从div的style属性中提取 width 和 height
                width = None
                height = None
                
                style_match = re.search(r'style\s*=\s*["\']([^"\']*width[^"\']*)["\']', html_content, re.IGNORECASE)
                if style_match:
                    style_str = style_match.group(1)
                    width_match = re.search(r'width\s*:\s*(\d+)px', style_str, re.IGNORECASE)
                    height_match = re.search(r'height\s*:\s*(\d+)px', style_str, re.IGNORECASE)
                    
                    if width_match:
                        width = int(width_match.group(1))
                    if height_match:
                        height = int(height_match.group(1))
                
                # 如果成功提取到尺寸，计算长宽比
                if width and height:
                    aspect_ratio = round(width / height, 2)
                    dimensions[block_id] = {
                        "width": width,
                        "height": height,
                        "aspect_ratio": aspect_ratio,
                        "html_file": html_file,
                        "description": block_content.get('description', '')
                    }
                else:
                    # 使用默认值
                    dimensions[block_id] = {
                        "width": 1000,
                        "height": 500,
                        "aspect_ratio": 2.0,
                        "html_file": html_file,
                        "description": block_content.get('description', '')
                    }
            except Exception:
                # 使用默认值
                dimensions[block_id] = {
                    "width": 1000,
                    "height": 500,
                    "aspect_ratio": 2.0,
                    "html_file": html_file,
                    "description": block_content.get('description', '')
                }
        
        return dimensions
    
    def _format_chart_dimensions(self, dimensions: dict) -> str:
        """格式化图表尺寸信息为可读的字符串
        
        参考 va_system_builder.py 的 _format_chart_dimensions 方法。
        
        Args:
            dimensions: 图表尺寸字典
        
        Returns:
            格式化的字符串
        """
        if not dimensions:
            return "No chart dimension information available."
        
        lines = ["### Chart Dimensions and Aspect Ratios:\n"]
        
        for block_id, info in dimensions.items():
            width = info['width']
            height = info['height']
            ratio = info['aspect_ratio']
            html_file = info['html_file']
            description = info.get('description', '')
            
            # 判断图表形状类型
            if ratio > 2.0:
                shape_type = "Wide (宽横向)"
            elif ratio > 1.2:
                shape_type = "Landscape (横向)"
            elif ratio >= 0.8:
                shape_type = "Square (方形)"
            elif ratio >= 0.5:
                shape_type = "Portrait (竖向)"
            else:
                shape_type = "Tall (高竖向)"
            
            lines.append(f"**{block_id}**:")
            lines.append(f"  - File: `{html_file}`")
            lines.append(f"  - Dimensions: {width}px × {height}px")
            lines.append(f"  - Aspect Ratio: {ratio} ({shape_type})")
            if description:
                lines.append(f"  - Description: {description}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _load_template_mapping(self) -> Dict[str, Any]:
        """加载模板映射配置文件
        
        Returns:
            模板映射配置字典
        """
        mapping_file = os.path.join(
            os.path.dirname(__file__),
            'template_mapping.json'
        )
        
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠️  Template mapping file not found: {mapping_file}, using default")
                # 返回默认配置
                return {
                    "template_library_path": "template_library",
                    "default_template": "template_base.html",
                    "rules": [],
                    "templates": {}
                }
        except Exception as e:
            print(f"⚠️  Error loading template mapping: {e}, using default")
            return {
                "template_library_path": "template_library",
                "default_template": "template_base.html",
                "rules": [],
                "templates": {}
            }
    
    def _select_template_by_config(self, config_file: Optional[str] = None) -> str:
        """根据配置文件中的highlight块和图表数量选择模板
        
        从映射配置文件中读取规则并匹配。
        
        Args:
            config_file: 配置文件路径（可选）
        
        Returns:
            模板文件名（如 'template_base.html'）
        """
        # 从映射配置获取默认模板
        default_template = self.template_mapping.get('default_template', 'template_base.html')
        
        if not config_file or not os.path.exists(config_file):
            return default_template
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 统计highlight块和view块的数量
            highlight_count = 0
            view_count = 0
            
            for block in config.get('blocks', []):
                block_type = block.get('blockType', '')
                if block_type == 'highlight':
                    highlight_count += 1
                elif block_type == 'view':
                    view_count += 1
            
            # 从映射配置读取规则并匹配
            rules = self.template_mapping.get('rules', [])
            for rule in rules:
                conditions = rule.get('conditions', {})
                match = True
                
                # 检查highlight_count条件
                if 'highlight_count' in conditions:
                    highlight_cond = conditions['highlight_count']
                    if 'min' in highlight_cond and highlight_count < highlight_cond['min']:
                        match = False
                    if 'max' in highlight_cond and highlight_count > highlight_cond['max']:
                        match = False
                
                # 检查view_count条件
                if 'view_count' in conditions:
                    view_cond = conditions['view_count']
                    if 'min' in view_cond and view_count < view_cond['min']:
                        match = False
                    if 'max' in view_cond and view_count > view_cond['max']:
                        match = False
                
                # 如果匹配，返回对应的模板
                if match:
                    template = rule.get('template')
                    if template:
                        print(f"✓ Matched rule '{rule.get('name', 'unknown')}': {rule.get('description', '')}")
                        return template
            
            # 如果没有匹配的规则，返回默认模板
            print(f"✓ No rule matched, using default template: {default_template}")
            return default_template
            
        except Exception as e:
            print(f"⚠️  Error selecting template: {e}, using default template")
            return default_template
    
    def _apply_template_with_substitution(
        self,
        template_name: str,
        va_app_path: str,
        question: str,
        config_file: Optional[str] = None
    ) -> bool:
        """应用指定的模板并替换变量（通用方法）
        
        流程：
        1. 从模板库（template_library）读取模板
        2. 复制模板到va_app/public/templates/
        3. 进行变量替换和应用
        
        Args:
            template_name: 模板文件名（如 'template_base.html' 或 'template_with_table.html'）
            va_app_path: VA应用路径
            question: 用户问题
            config_file: 配置文件路径（可选）
        
        Returns:
            是否成功应用模板
        """
        try:
            # 1. 从映射配置获取模板信息
            templates_info = self.template_mapping.get('templates', {})
            template_info = templates_info.get(template_name, {})
            
            # 获取模板库路径
            template_library_path = self.template_mapping.get('template_library_path', 'template_library')
            template_library_dir = os.path.join(os.path.dirname(__file__), template_library_path)
            
            # 2. 确定模板源文件路径
            # 优先使用映射配置中的source_path
            if template_info.get('source_path'):
                template_source = os.path.join(os.path.dirname(__file__), template_info['source_path'])
            else:
                # 回退到模板库目录
                template_source = os.path.join(template_library_dir, template_name)
            
            # 如果模板库中不存在，尝试从旧位置查找（向后兼容）
            if not os.path.exists(template_source):
                # 尝试从 ui_templates 目录查找
                template_source = os.path.join(
                    os.path.dirname(__file__),
                    'ui_templates',
                    template_name
                )
                
                # 如果还是不存在，尝试从 template/public/templates 查找
                if not os.path.exists(template_source):
                    template_source = os.path.join(
                        os.path.dirname(__file__),
                        'template',
                        'public',
                        'templates',
                        template_name
                    )
            
            if not os.path.exists(template_source):
                print(f"⚠️  Template {template_name} not found")
                # 如果找不到指定模板，回退到默认模板
                default_template = self.template_mapping.get('default_template', 'template_base.html')
                if template_name != default_template:
                    print(f"⚠️  Falling back to {default_template}")
                    return self._apply_template_with_substitution(
                        default_template, va_app_path, question, config_file
                    )
                return False
            
            # 3. 读取模板内容
            with open(template_source, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 4. 确保目标目录存在
            templates_dest = os.path.join(va_app_path, 'public', 'templates')
            os.makedirs(templates_dest, exist_ok=True)
            
            # 5. 从配置文件中读取所有信息
            dashboard_name = "Dashboard"
            dashboard_description = "Explore data insights and analytics."
            chart_titles = []
            chart_ids = []
            highlight_titles = []
            highlight_ids = []
            
            if config_file and os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # 1. 从metadata中获取dashboard名字和描述
                    metadata = config.get('metadata', {})
                    dashboard_name = metadata.get('dashboard_name', dashboard_name)
                    dashboard_description = metadata.get('dashboard_description', dashboard_description)
                    
                    # 如果没有metadata，尝试从layout中获取
                    if dashboard_name == "Dashboard":
                        layout = config.get('layout', {})
                        dashboard_name = layout.get('dashboard_name', dashboard_name)
                        dashboard_description = layout.get('dashboard_description', dashboard_description)
                    
                    # 2. 获取所有highlight blocks的标题和ID
                    for block in config.get('blocks', []):
                        if block.get('blockType') == 'highlight':
                            block_id = block.get('id', '')
                            block_content = block.get('blockContent', {})
                            title = block_content.get('title', '')
                            if block_id:
                                highlight_ids.append(block_id)
                            if title:
                                highlight_titles.append(title)
                    
                    # 3. 获取所有view blocks的标题和ID（按配置中的顺序）
                    for block in config.get('blocks', []):
                        if block.get('blockType') == 'view':
                            block_id = block.get('id', '')
                            block_content = block.get('blockContent', {})
                            # 优先使用description，如果没有则使用title
                            title = block_content.get('description', '') or block_content.get('title', '')
                            if block_id:
                                chart_ids.append(block_id)
                            if title:
                                chart_titles.append(title)
                except Exception as e:
                    print(f"⚠️  Error reading config file: {e}")
                    # 如果读取失败，使用question作为fallback
                    dashboard_name = self._extract_dashboard_name(question)
                    dashboard_description = self._extract_dashboard_description(question)
            
            # 替换变量
            # 1. 替换Dashboard名字
            template_content = re.sub(
                r'<span class="font-bold text-xl tracking-tight text-gray-800">DataMiner</span>',
                f'<span class="font-bold text-xl tracking-tight text-gray-800">{dashboard_name}</span>',
                template_content
            )
            
            # 2. 替换标题和描述
            template_content = re.sub(
                r'<h2 class="text-xl font-bold text-gray-800">Maven Roasters Sales</h2>\s*<p class="text-xs text-gray-500 mt-0.5">Explore sales trends and product performance across NYC locations\.</p>',
                f'<h2 class="text-xl font-bold text-gray-800">{dashboard_name}</h2>\n                <p class="text-xs text-gray-500 mt-0.5">{dashboard_description}</p>',
                template_content
            )
            
            # 3. 替换highlight标题（如果模板中有highlight部分）
            if highlight_titles:
                # 查找highlight标题模式（根据实际模板结构调整）
                highlight_pattern = r'(<div[^>]*class="[^"]*highlight[^"]*"[^>]*>.*?<[^>]*>)([^<]+)(</[^>]*>)'
                # 或者更通用的模式：查找包含"highlight"关键词的文本
                # 这里需要根据实际模板结构调整
            
            # 4. 替换图表标题（查找所有图表标题并替换）
            chart_title_pattern = r'(<h3 class="font-bold text-gray-800 mb-6 text-sm uppercase tracking-wide flex items-center gap-2">\s*<span class="w-1 h-4 bg-\[#[^\]]+\] rounded-full"></span>\s*)([^<]+)(</h3>)'
            
            title_index = 0
            def replace_chart_title(match):
                nonlocal title_index
                prefix = match.group(1)
                current_title = match.group(2).strip()
                suffix = match.group(3)
                
                # 如果有可用的图表标题，使用它；否则保持原样
                if title_index < len(chart_titles):
                    new_title = chart_titles[title_index]
                    title_index += 1
                    return prefix + new_title + suffix
                return match.group(0)
            
            template_content = re.sub(chart_title_pattern, replace_chart_title, template_content)
            
            # 5. 替换图表ID（将模板中的 intent_X_goal_0_chart0 替换为配置文件中的实际ID）
            if chart_ids:
                # 查找所有图表ID模式：intent_数字_goal_数字_chart数字
                chart_id_pattern = r'id="(intent_\d+_goal_\d+_chart\d+)"'
                
                chart_id_index = 0
                def replace_chart_id(match):
                    nonlocal chart_id_index
                    old_id = match.group(1)
                    
                    # 如果有可用的图表ID，使用它；否则保持原样
                    if chart_id_index < len(chart_ids):
                        new_id = chart_ids[chart_id_index]
                        chart_id_index += 1
                        return f'id="{new_id}"'
                    return match.group(0)
                
                template_content = re.sub(chart_id_pattern, replace_chart_id, template_content)
            
            # 6. 如果是通用模板，注入配置数据供JavaScript使用
            if template_name == 'template_universal.html' and config_file and os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # 将配置数据注入到HTML中
                    config_json_str = json.dumps(config_data, ensure_ascii=False)
                    config_script = f'\n<script id="dashboard-config-data" type="application/json">{config_json_str}</script>\n'
                    
                    # 优先在第一个 <script> 标签之前插入，确保配置在模板脚本执行前可用
                    first_script_pos = template_content.find('<script')
                    if first_script_pos != -1:
                        template_content = template_content[:first_script_pos] + config_script + template_content[first_script_pos:]
                    elif '</body>' in template_content:
                        template_content = template_content.replace('</body>', config_script + '</body>')
                    elif '</div>' in template_content:
                        # 找到最后一个</div>之前插入
                        last_div_pos = template_content.rfind('</div>')
                        if last_div_pos != -1:
                            template_content = template_content[:last_div_pos] + config_script + template_content[last_div_pos:]
                    else:
                        # 如果没有找到，在末尾插入
                        template_content = template_content + config_script
                    
                    print(f"✓ Injected dashboard config data for universal template")
                except Exception as e:
                    print(f"⚠️  Failed to inject config data for universal template: {e}")
            
            # 7. 保存替换后的模板到目标路径（templates_dest已在前面创建）
            customized_template_path = os.path.join(templates_dest, 'page_customized.html')
            with open(customized_template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            # 保存主题内容供图表美化使用
            self.page_theme_content = template_content
            
            print(f"✓ Applied {template_name} with substitutions")
            return True
            
        except Exception as e:
            print(f"❌ Error applying template {template_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _extract_dashboard_name(self, question: str) -> str:
        """从问题中提取Dashboard名字
        
        Args:
            question: 用户问题
        
        Returns:
            Dashboard名字
        """
        if not question:
            return "Dashboard"
        
        # 尝试提取关键名词作为名字
        # 移除常见的问句词汇
        question_clean = question.strip()
        
        # 如果问题很短，直接使用
        if len(question_clean) <= 30:
            # 移除问号、句号等
            question_clean = re.sub(r'[?。！？]$', '', question_clean)
            return question_clean[:30]
        
        # 如果问题很长，提取前几个关键词
        # 简单处理：取前20个字符
        question_clean = re.sub(r'[?。！？]$', '', question_clean)
        return question_clean[:20] + "..."
    
    def _extract_dashboard_description(self, question: str) -> str:
        """从问题中提取Dashboard描述
        
        Args:
            question: 用户问题
        
        Returns:
            Dashboard描述
        """
        if not question:
            return "Explore data insights and analytics."
        
        # 如果问题很短，直接使用
        if len(question) <= 60:
            return question
        
        # 如果问题很长，使用前50个字符
        return question[:50] + "..."
    
    
    def _update_app_config(self, app_py_path: str, config_filename: str):
        """更新app.py中的配置文件路径
        
        参考 va_system_builder.py 的 _update_app_config 方法。
        
        Args:
            app_py_path: app.py文件路径
            config_filename: 配置文件名
        """
        try:
            with open(app_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换schema_path配置
            pattern = r'schema_path\s*=\s*os\.path\.join\(CONFIGS_DIR,\s*["\'][^"\']*["\']\)'
            replacement = f'schema_path = os.path.join(CONFIGS_DIR, "{config_filename}")'
            
            updated_content = re.sub(pattern, replacement, content)
            
            with open(app_py_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
        except Exception:
            pass
    
    def _update_page_template_config(self, config_file_path: str):
        """更新配置文件中的pageTemplate路径
        
        参考 va_system_builder.py 的 _update_page_template_config 方法。
        
        Args:
            config_file_path: 配置文件路径
        """
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新layout中的pageTemplate
            if 'layout' in config:
                config['layout']['pageTemplate'] = 'public/templates/page_customized.html'
                
                with open(config_file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _generate_html_from_python_charts(
        self, 
        echart_source_dir: str, 
        dataset_path: str,
        max_workers: int = 4
    ):
        """
        检测echart_code目录中是否有HTML文件，如果没有则运行Python代码生成
        
        参考 va_system_builder.py 的 _generate_html_from_python_charts 方法。
        
        Args:
            echart_source_dir: echart_code目录路径
            dataset_path: 数据集路径
            max_workers: 最大并行worker数
        """
        if not os.path.exists(echart_source_dir):
            print(f"⚠️  EChart source directory not found: {echart_source_dir}")
            return
        
        # 1. 检查是否已有HTML文件
        html_files = [f for f in os.listdir(echart_source_dir) if f.endswith('.html')]
        python_files = [f for f in os.listdir(echart_source_dir) if f.endswith('.py')]
        
        if html_files:
            print(f"✓ Found {len(html_files)} HTML files in {echart_source_dir}, skip generation")
            return
        
        if not python_files:
            print(f"⚠️  No Python files found in {echart_source_dir}")
            return
        
        print(f"🔧 No HTML files found, generating from {len(python_files)} Python files...")
        
        # 2. 准备数据路径（检查数据集是否存在）
        if not os.path.exists(dataset_path):
            print(f"❌ Dataset not found: {dataset_path}")
            return
        
        # 3. 定义单个Python文件的执行函数
        def execute_python_chart(py_file: str) -> Tuple[str, bool, str]:
            """执行单个Python图表文件生成HTML"""
            py_path = os.path.join(echart_source_dir, py_file)
            chart_name = os.path.splitext(py_file)[0]
            
            try:
                # 读取Python代码
                with open(py_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # 检查代码结构：是否有plot函数定义？
                has_plot_function = 'def plot(' in code
                
                # 创建临时执行环境
                exec_globals = {
                    '__file__': py_path,
                    '__name__': '__main__',
                    'dataset_path': dataset_path,
                }
                
                # 构建执行代码
                if has_plot_function:
                    # LIDA生成的代码：有plot(data)函数
                    exec_code = f"""
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import *
import os

# 加载数据
data = pd.read_csv(r'{dataset_path}')

# 执行原始代码（定义plot函数）
{code}

# 调用plot函数生成图表
chart = plot(data)

# 渲染HTML文件
chart.render(r'{os.path.join(echart_source_dir, chart_name + ".html")}')
"""
                else:
                    # 直接生成图表的代码
                    exec_code = f"""
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import *
import os

# 加载数据
data = pd.read_csv(r'{dataset_path}')

# 执行原始代码
{code}

# 查找chart对象并渲染
for var_name in dir():
    var = locals().get(var_name)
    if hasattr(var, 'render') and hasattr(var, 'options'):
        var.render(r'{os.path.join(echart_source_dir, chart_name + ".html")}')
        break
"""
                
                # 执行代码生成HTML
                exec(exec_code, exec_globals)
                
                # 检查是否生成了HTML文件
                expected_html = os.path.join(echart_source_dir, f"{chart_name}.html")
                if os.path.exists(expected_html):
                    return py_file, True, f"✓ Generated {chart_name}.html"
                else:
                    return py_file, False, "✗ No HTML generated after execution"
                        
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                # 记录完整的错误信息
                print(f"❌ Error executing {py_file}:\n{error_detail}")
                return py_file, False, f"✗ Error: {str(e)}"
        
        # 4. 使用线程池并行执行
        success_count = 0
        failed_files = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(execute_python_chart, py_file): py_file 
                for py_file in python_files
            }
            
            # 收集结果
            for future in as_completed(future_to_file):
                py_file, success, message = future.result()
                if success:
                    success_count += 1
                    print(f"  {message}")
                else:
                    failed_files.append((py_file, message))
                    print(f"  {message}")
        
        # 5. 输出汇总
        print(f"HTML generation completed: {success_count}/{len(python_files)} succeeded")
        if failed_files:
            print(f"⚠️  Failed files ({len(failed_files)}):")
            for py_file, error in failed_files:
                print(f"  - {py_file}: {error}")
    
    def _process_echart_html(self, src_file: str, dst_file: str):
        """处理ECharts HTML文件：删除title，截取数据只保留前10个示例
        
        参考 va_system_builder.py 的 _process_echart_html 方法。
        
        Args:
            src_file: 源文件路径
            dst_file: 目标文件路径
        """
        try:
            with open(src_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找 option 配置的起始位置
            option_pattern = r'var option_[a-zA-Z0-9_]+ = ({.*?});'
            match = re.search(option_pattern, content, re.DOTALL)
            
            if match:
                option_json_str = match.group(1)
                
                try:
                    # 解析JSON配置
                    option_config = json.loads(option_json_str)
                    
                    # 1. 删除title配置
                    if 'title' in option_config:
                        del option_config['title']
                    
                    # 2. 处理series中的数据，只保留前10个
                    if 'series' in option_config:
                        for series in option_config['series']:
                            if 'data' in series and isinstance(series['data'], list):
                                original_length = len(series['data'])
                                if original_length > 10:
                                    series['data'] = series['data'][:10]
                            
                            # 将label隐藏
                            if 'label' in series:
                                series['label']['show'] = False
                    
                    # 3. 处理xAxis中的数据，只保留前10个
                    if 'xAxis' in option_config:
                        x_axes = option_config['xAxis'] if isinstance(option_config['xAxis'], list) else [option_config['xAxis']]
                        for x_axis in x_axes:
                            if 'data' in x_axis and isinstance(x_axis['data'], list):
                                original_length = len(x_axis['data'])
                                if original_length > 10:
                                    x_axis['data'] = x_axis['data'][:10]
                    
                    # 4. 处理grid
                    if 'grid' in option_config:
                        option_config['grid']['containLabel'] = True
                    else:
                        option_config['grid'] = {
                            "containLabel": True
                        }

                    # 5. 处理legend中的top配置
                    if 'legend' in option_config:
                        # legend 可能是字典或列表
                        if isinstance(option_config['legend'], dict):
                            option_config['legend']['top'] = '5%'
                        elif isinstance(option_config['legend'], list):
                            for legend in option_config['legend']:
                                if isinstance(legend, dict):
                                    legend['top'] = '5%'
                    
                    # 将修改后的配置转回JSON字符串
                    new_option_json = json.dumps(option_config, ensure_ascii=False, indent=4)
                    
                    # 替换原内容中的option配置
                    new_content = content[:match.start(1)] + new_option_json + content[match.end(1):]
                    
                    # 写入目标文件
                    with open(dst_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                except json.JSONDecodeError:
                    # 解析失败，直接复制原文件
                    shutil.copy2(src_file, dst_file)
            else:
                # 找不到配置，直接复制原文件
                shutil.copy2(src_file, dst_file)
                
        except Exception:
            # 处理失败，直接复制原文件
            shutil.copy2(src_file, dst_file)
    
    def _update_config_with_html_names(self, config_file_path: str, charts_dir: str):
        """
        更新配置文件中的python_code_name和html_code_name字段，确保指向实际生成的文件
        
        参考 va_system_builder.py 的 _update_config_with_html_names 方法。
        
        Args:
            config_file_path: 配置文件路径
            charts_dir: charts目录路径
        """
        try:
            # 读取配置文件
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 获取charts目录中的所有文件
            if not os.path.exists(charts_dir):
                print(f"⚠️  Charts directory not found: {charts_dir}")
                return
            
            available_files = set(os.listdir(charts_dir))
            updated_count = 0
            
            # 遍历所有blocks
            for block in config.get('blocks', []):
                if block.get('blockType') == 'view':
                    block_content = block.get('blockContent', {})
                    
                    # 检查是否已有python_code_name和html_code_name
                    python_name = block_content.get('python_code_name', '')
                    html_name = block_content.get('html_code_name', '')
                    
                    # 如果字段不存在，尝试从layers中提取
                    if not python_name:
                        layers = block_content.get('layers', [])
                        if layers and 'code_file' in layers[0]:
                            code_file = layers[0].get('code_file', '')
                            python_name = os.path.basename(code_file) if code_file else ''
                            html_name = python_name.replace('.py', '.html') if python_name else ''
                    
                    # 验证文件是否存在
                    if python_name:
                        # 更新字段
                        block_content['python_code_name'] = python_name
                        block_content['html_code_name'] = html_name
                        
                        updated_count += 1
            
            # 保存更新后的配置
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Updated {updated_count} view blocks with python_code_name and html_code_name")
            
        except Exception as e:
            print(f"❌ Error updating config with HTML names: {str(e)}")
    
    def _reprocess_charts_after_beautify(self, charts_dest: str):
        """在图表美化后，对所有图表再次应用标准化处理（原地处理）
        
        参考 va_system_builder.py 的 _reprocess_charts_after_beautify 方法。
        
        - 统一隐藏 series.label
        - 截断 series/xAxis 的 data 至前 10 条
        - 保持 grid.containLabel 为 True
        
        Args:
            charts_dest: 图表目录路径
        """
        try:
            if not os.path.exists(charts_dest):
                print(f"⚠️  Charts directory not found for reprocess: {charts_dest}")
                return
            
            for file in os.listdir(charts_dest):
                src_path = os.path.join(charts_dest, file)
                if os.path.isfile(src_path) and file.endswith('.html'):
                    # 原地处理：src 与 dst 相同
                    self._process_echart_html(src_path, src_path)
            
            print("✓ Reprocessed charts after beautify (labels hidden, data trimmed)")
        except Exception as e:
            print(f"❌ Error in _reprocess_charts_after_beautify: {e}")

