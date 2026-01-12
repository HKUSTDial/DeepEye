import json
import re
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import numpy as np
import os
import sys
import yaml
from dotenv import load_dotenv
from storyteller.llm_call.openai_llm import call_openai
from storyteller.llm_call.prompt_factory import get_prompt

# 加载环境变量
load_dotenv(override=True)

# 添加项目根目录到Python路径
# 获取当前文件的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录（假设当前文件在storyteller/algorithm/utils/下）
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# 加载全局配置
def load_config():
    """加载config.yaml中的配置"""
    config_path = os.path.join(current_dir, "../../config/config.yaml")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✅ 成功加载配置文件: {config_path}")
        return config
    except Exception as e:
        print(f"⚠️ 加载配置文件失败: {str(e)}")
        return {"llm_kwargs": {}}

# 全局配置
GLOBAL_CONFIG = load_config()

class ChartConfigExtractor:
    """
    使用LLM解析Python可视化代码，提取图表配置信息，
    以便转换为AntV G2配置。
    
    主要功能：
    1. 使用GPT-4分析Python可视化代码
    2. 提取关键配置信息（图表类型、字段、聚合方法等）
    3. 处理数据并生成G2格式的配置
    """
    
    def __init__(self, data_context_path: str = None):
        """
        初始化提取器
        
        参数:
            data_context_path: 数据上下文文件路径，包含数据集的列名信息
        """
        self.default_config = {
            "chart_type": "bar",
            "title": None,
            "x_field": None,
            "y_field": None,
            "data_columns": [],
            "hue_column": None,
            "is_stacked": False,
            "agg_method": None,
            "binning": None
        }
        
        # 字段映射配置
        self.field_mappings = {
            'Purchase_Amount__USD_': {
                'display': 'Purchase Amount (USD)',
                'agg_prefix': 'Average'
            },
            'Previous_Purchases': {
                'display': 'Previous Purchases',
                'agg_prefix': 'Average'
            },
            'Review_Rating': {
                'display': 'Review Rating',
                'agg_prefix': None
            }
        }
        
        # 加载数据上下文
        self.data_context = None
        if data_context_path:
            try:
                with open(data_context_path, 'r', encoding='utf-8') as f:
                    self.data_context = json.load(f)
                print(f"✅ 成功加载数据上下文: {data_context_path}")
            except Exception as e:
                print(f"⚠️ 加载数据上下文失败: {str(e)}")

    def get_display_name(self, field: str, agg_method: str = None) -> str:
        """获取字段的显示名称"""
        if field in self.field_mappings:
            base_name = self.field_mappings[field]['display']
            if agg_method and self.field_mappings[field].get('agg_prefix'):
                prefix = self.field_mappings[field]['agg_prefix']
                return f"{prefix} {base_name}"
            return base_name
        return field

    def _handle_histogram_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """处理直方图特殊配置"""
        if config['chart_type'] == 'histogram':
            config['y_field'] = None
            config['agg_method'] = 'count'
            
            # 确保有binning配置
            if not config.get('binning'):
                config['binning'] = {
                    'bin_count': 30,  # 默认30个bins
                    'bin_width': None
                }
        return config

    def _process_aggregation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """处理聚合配置"""
        if config.get('agg_method'):
            y_field = config['y_field']
            if y_field:
                config['display_names'] = {
                    y_field: self.get_display_name(y_field, config['agg_method'])
                }
        return config

    def extract_from_code(self, code: str) -> Dict[str, Any]:
        """
        从代码中提取图表配置
        
        参数:
            code: 可视化代码字符串
            
        返回:
            包含图表配置的字典
        """
        try:
            # 准备参数
            prompt_args = {
                "CODE": code,
                "DATA_CONTEXT": json.dumps(self.data_context, ensure_ascii=False, indent=2) if self.data_context else "{}"
            }
            
            # 获取模板
            prompt = get_prompt("chart_config_analysis", prompt_args)
            
            # 从全局配置中获取LLM参数
            llm_kwargs = GLOBAL_CONFIG.get("llm_kwargs", {})
            if not llm_kwargs:
                print("⚠️ 未找到全局LLM配置，使用默认值")
                llm_kwargs = {
                    "model": "gpt-4-32k",
                    "temperature": 0.0,
                    "max_tokens": 4096
                }
            else:
                # 确保关键参数存在，同时覆盖temperature为0
                llm_kwargs = llm_kwargs.copy()  # 创建副本避免修改全局配置
                llm_kwargs["temperature"] = 0.0  # 对于配置提取，始终使用低temperature
                llm_kwargs["max_tokens"] = llm_kwargs.get("max_tokens", 4096)
            
            print(f"🔍 使用LLM配置: model={llm_kwargs.get('model')}, base_url={llm_kwargs.get('base_url', '默认')}")
            
            # 实现重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 调用LLM
                    responses = call_openai(prompt, **llm_kwargs)
                    print(f"✅ 成功获取LLM响应 (尝试 {attempt+1}/{max_retries})")
                    
                    # 解析JSON响应
                    if isinstance(responses, list):
                        response = responses[0]
                    else:
                        response = responses
                    
                    try:
                        config = json.loads(response)
                    except:
                        # 如果直接解析失败，尝试提取JSON部分
                        import re
                        json_match = re.search(r'\{.*\}', response, re.DOTALL)
                        if json_match:
                            config = json.loads(json_match.group(0))
                        else:
                            raise ValueError("无法从响应中提取JSON配置")
                    
                    # 特殊处理：检测value_counts()操作
                    if "value_counts()" in code:
                        # 从代码中提取被统计的字段
                        import re
                        field_match = re.search(r"data\['([^']+)'\]\.value_counts\(\)", code)
                        if field_match:
                            x_field = field_match.group(1)
                            config.update({
                                "chart_type": "bar",
                                "x_field": x_field,
                                "y_field": "count",
                                "agg_method": "count",
                                "data_columns": [x_field]
                            })
                    
                    # 填充默认值
                    config = self._fill_config_defaults(config)
                    
                    # 处理直方图特殊配置
                    config = self._handle_histogram_config(config)
                    
                    # 处理聚合配置
                    config = self._process_aggregation(config)
                    
                    return config
                    
                except Exception as e:
                    print(f"⚠️ 尝试 {attempt+1} 失败: {str(e)}")
                    if attempt == max_retries - 1:
                        print("❌ 所有重试都失败，返回默认配置")
                        return self.default_config
                    else:
                        print(f"重试中... ({attempt+2}/{max_retries})")
                    
        except Exception as e:
            print(f"❌ 提取配置时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.default_config
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """解析LLM返回的JSON响应"""
        try:
            # 直接尝试解析
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except:
                    print("无法解析提取的JSON部分")
            
            # 最后一次尝试：修复常见的JSON格式错误
            try:
                # 替换单引号为双引号
                fixed_text = response_text.replace("'", '"')
                # 确保属性名有双引号
                fixed_text = re.sub(r'(\w+):', r'"\1":', fixed_text)
                return json.loads(fixed_text)
            except:
                print("所有JSON解析尝试都失败了")
            
        return None
    
    def _fill_config_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """填充配置中缺失的默认值"""
        # 复制默认配置
        result = self.default_config.copy()
        
        # 确保不丢失派生列信息
        if "derived_columns" in config:
            result["derived_columns"] = config["derived_columns"]
        
        # 用提供的配置更新默认值
        result.update(config)
        
        # 确保图表类型有效
        if not result["chart_type"]:
            result["chart_type"] = "bar"
        
        # 智能构建标题（如果缺失）
        if not result["title"]:
            x_field = result.get("x_field", "")
            y_field = result.get("y_field", "")
            agg_method = result.get("agg_method", "")
            
            if agg_method and y_field:
                agg_display = {
                    "count": "Count of",
                    "sum": "Sum of",
                    "mean": "Average",
                    "min": "Minimum",
                    "max": "Maximum"
                }.get(agg_method, agg_method.capitalize())
                
                result["title"] = f"{agg_display} {y_field} by {x_field}"
            elif x_field and y_field:
                result["title"] = f"{y_field} by {x_field}"
        
        return result
    
    def _handle_special_chart_types(self, df_copy: pd.DataFrame, chart_type: str, x_field: str, y_field: str) -> Optional[Dict[str, Any]]:
        """处理特殊图表类型（boxplot、violin、histogram、scatter）"""
        try:
            if not (x_field and y_field and y_field in df_copy.columns):
                return None
                
            print(f"为{chart_type}类型准备数据，不使用聚合...")
            
            # 散点图特殊处理
            if chart_type == "scatter":
                return self._handle_scatter_plot(df_copy, x_field, y_field)
            
            # boxplot等其他分布图表处理
            # 获取唯一的x值作为标签
            unique_x = df_copy[x_field].unique()
            labels = [str(x) for x in unique_x]
            
            # 为每个x值创建对应的y值数组
            datasets = []
            for x_val in unique_x:
                y_values = df_copy[df_copy[x_field] == x_val][y_field].tolist()
                datasets.append({
                    "label": str(x_val),
                    "data": y_values
                })
            
            return {
                "type": chart_type,  # 添加图表类型
                "labels": labels,
                "datasets": datasets
            }
            
        except Exception as e:
            print(f"处理{chart_type}数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _handle_scatter_plot(self, df: pd.DataFrame, x_field: str, y_field: str) -> Dict[str, Any]:
        """处理散点图数据"""
        df_copy = df.copy()
        
        # 确保x和y字段都是数值类型
        for field, name in [(x_field, 'X轴'), (y_field, 'Y轴')]:
            if not pd.api.types.is_numeric_dtype(df_copy[field]):
                try:
                    print(f"{name}字段不是数值类型，尝试转换...")
                    df_copy[field] = pd.to_numeric(df_copy[field], errors='coerce')
                except Exception as e:
                    print(f"无法将{name}字段转换为数值类型: {str(e)}")
        
        # 去除缺失值
        valid_data = df_copy.dropna(subset=[x_field, y_field])
        if len(valid_data) < len(df_copy):
            print(f"警告: 移除了{len(df_copy)-len(valid_data)}行含缺失值的数据")
        
        # 为散点图返回所有数据点
        return {
            "type": "scatter",
            "datasets": [{
                "label": y_field,
                "data": [{"x": x, "y": y} for x, y in zip(valid_data[x_field].tolist(), valid_data[y_field].tolist())],
                "backgroundColor": 'rgba(54, 162, 235, 0.7)',
                "borderColor": 'rgba(54, 162, 235, 1.0)',
                "borderWidth": 1,
                "pointRadius": 4,
                "pointHoverRadius": 6
            }]
        }
        
    def _handle_distribution_plot(self, df: pd.DataFrame, chart_type: str, x_field: str, y_field: str) -> Dict[str, Any]:
        """处理分布图（boxplot、violin、histogram）数据"""
        # 获取唯一的x值作为标签
        unique_x = df[x_field].unique()
        labels = [str(x) for x in unique_x]
        
        # 为每个x值创建对应的y值数组
        datasets = []
        for x_val in unique_x:
            y_values = df[df[x_field] == x_val][y_field].tolist()
            datasets.append({
                "label": str(x_val),
                "data": y_values
            })
        
        return {
            "type": chart_type,
            "labels": labels,
            "datasets": datasets
        }
        
    def resolve_chart_data(self, df: pd.DataFrame, config: Dict[str, Any] = None):
        """处理图表数据"""
        if config is None:
            config = {}
            
        try:
            # 提取配置
            chart_type = config.get("chart_type", "bar")
            x_field = config.get("x_field")
            y_field = config.get("y_field")
            hue_field = config.get("hue_column")
            
            # 处理直方图特殊情况
            if chart_type == "histogram":
                if not config.get('binning'):
                    config['binning'] = {'bin_count': 30}
                return self._prepare_histogram_data(df, x_field, config['binning'])
            
            # 处理箱线图特殊情况
            if chart_type == "boxplot":
                print(f"处理箱线图数据: x={x_field}, y={y_field}")
                return self._prepare_boxplot_data(df, x_field, y_field)
            
            # 处理聚合方法
            agg_method = config.get("agg_method", "sum")
            if chart_type in ["scatter"]:
                agg_method = None
            
            # 验证字段
            self._validate_fields(df, config)
            
            # 根据图表类型处理数据
            if chart_type == "pie":
                return self._prepare_pie_data(df, x_field, y_field, agg_method)
            elif hue_field:
                return self._prepare_grouped_data(df, x_field, y_field, hue_field, agg_method, config.get("is_stacked", False))
            else:
                return self._prepare_single_series_data(df, x_field, y_field, agg_method)
                
        except Exception as e:
            print(f"处理数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _validate_fields(self, df: pd.DataFrame, config: Dict[str, Any]):
        """验证字段是否存在于DataFrame中"""
        if not isinstance(df, pd.DataFrame):
            print("⚠️ 输入数据不是DataFrame类型")
            return False
            
        required_fields = []
        if config.get("x_field"):
            required_fields.append(config["x_field"])
        if config.get("y_field"):
            required_fields.append(config["y_field"])
        if config.get("hue_column"):
            required_fields.append(config["hue_column"])
            
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            print(f"⚠️ 以下字段在DataFrame中不存在: {missing_fields}")
            return False
            
        return True
    
    def _calculate_boxplot_stats(self, df: pd.DataFrame, x_field: str, y_field: str) -> List[Dict[str, Any]]:
        """计算箱线图所需的统计量"""
        result = []
        
        # 对每个分类值计算统计量
        for category in df[x_field].unique():
            values = df[df[x_field] == category][y_field].dropna()
            
            if len(values) == 0:
                continue
            
            # 计算统计量
            min_val = values.min()
            q1 = values.quantile(0.25)
            median = values.quantile(0.5)
            q3 = values.quantile(0.75)
            max_val = values.max()
            
            # 计算异常值
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # 过滤出非异常值的最小和最大值
            normal_min = values[values >= lower_bound].min()
            normal_max = values[values <= upper_bound].max()
            
            # 获取异常值
            outliers = values[(values < lower_bound) | (values > upper_bound)].tolist()
            
            result.append({
                x_field: category,
                "min": float(normal_min),
                "q1": float(q1),
                "median": float(median),
                "q3": float(q3),
                "max": float(normal_max),
                "outliers": outliers,
                "range": [float(normal_min), float(q1), float(median), float(q3), float(normal_max)]
            })
        
        return result

    def _prepare_boxplot_data(self, df: pd.DataFrame, x_field: str, y_field: str) -> List[Dict[str, Any]]:
        """准备箱线图数据（G2格式）"""
        if not x_field or x_field not in df.columns:
            raise ValueError(f"箱线图需要有效的分类字段: {x_field}")
        if not y_field or y_field not in df.columns:
            raise ValueError(f"箱线图需要有效的数值字段: {y_field}")
        
        try:
            return self._calculate_boxplot_stats(df, x_field, y_field)
        except Exception as e:
            print(f"准备箱线图数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _prepare_pie_data(self, df: pd.DataFrame, x_field: str, y_field: str, agg_method: str):
        """准备饼图数据（G2格式）"""
        if not x_field or x_field not in df.columns:
            raise ValueError("饼图需要有效的类别字段")
        
        try:
            # 计算各类别的计数或聚合值
            if y_field and y_field in df.columns:
                if agg_method == "count":
                    data = df.groupby(x_field)[y_field].count()
                elif agg_method == "mean":
                    data = df.groupby(x_field)[y_field].mean()
                elif agg_method in [None, "none"]:
                    print("饼图通常需要聚合，使用sum作为默认聚合方法")
                    data = df.groupby(x_field)[y_field].sum()
                else:  # 默认使用sum
                    data = df.groupby(x_field)[y_field].sum()
            else:
                # 如果只有x字段，使用计数
                data = df[x_field].value_counts()
            
            # 创建结果DataFrame
            result_df = pd.DataFrame({
                'category': data.index,
                'value': data.values
            })
            
            # 计算百分比
            total = result_df['value'].sum()
            result_df['percentage'] = (result_df['value'] / total * 100).round(1)
            
            return result_df.to_dict('records')
            
        except Exception as e:
            print(f"准备饼图数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 返回基本的错误数据结构
            return [
                {"category": "错误", "value": 0, "percentage": 0},
                {"category": "请检查数据", "value": 0, "percentage": 0}
            ]
    
    def _prepare_grouped_data(self, df: pd.DataFrame, x_field: str, y_field: str, hue_field: str, agg_method: str, is_stacked: bool):
        """准备分组数据（G2格式）"""
        if not x_field or x_field not in df.columns:
            raise ValueError(f"X轴字段 '{x_field}' 不存在")
        if not hue_field or hue_field not in df.columns:
            raise ValueError(f"分组字段 '{hue_field}' 不存在")
        
        try:
            # 克隆数据，避免修改原数据
            df_copy = df.copy()
            
            # 确保数据类型正确
            for col in [x_field, y_field, hue_field]:
                if col and col in df.columns:
                    if df[col].apply(lambda x: isinstance(x, (list, dict, tuple))).any():
                        df_copy[col] = df_copy[col].astype(str)
                    elif df[col].dtype == 'object' or not pd.api.types.is_categorical_dtype(df[col]):
                        df_copy[col] = df_copy[col].astype(str)
            
            # 处理聚合
            pivot_data = None
            if y_field and y_field in df.columns:
                try:
                    if agg_method == "count":
                        pivot_data = pd.crosstab(df_copy[x_field], df_copy[hue_field])
                except Exception as e:
                    print(f"数据透视表处理失败: {str(e)}")
                    # 使用更安全的方法
                    grouped = df_copy.groupby([x_field, hue_field])
                    if agg_method == "count":
                        grouped = grouped.size()
                    else:
                        grouped = grouped[y_field].agg(agg_method or 'sum')
                    pivot_data = grouped.unstack(fill_value=0)
            
            if pivot_data is None:
                pivot_data = pd.crosstab(df_copy[x_field], df_copy[hue_field])
            
            # 直接返回G2格式数据
            processed_data = []
            for x_val in pivot_data.index:
                for hue_val in pivot_data.columns:
                    processed_data.append({
                        x_field: str(x_val),
                        y_field: float(pivot_data.loc[x_val, hue_val]),
                        hue_field: str(hue_val)
                    })
            
            return processed_data
        
        except Exception as e:
            print(f"准备分组数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 返回基本的错误数据结构
            return [
                {x_field: "错误", y_field: 0, hue_field: "请检查数据"}
            ]
    
    def _prepare_single_series_data(self, df: pd.DataFrame, x_field: str, y_field: str, agg_method: str):
        """准备单系列数据（G2格式）"""
        if x_field is None or x_field not in df.columns:
            print(f"警告: X轴字段 '{x_field}' 不存在或为None，使用索引作为X轴")
            temp_df = df.copy()
            temp_df['index_as_x'] = range(len(df))
            df = temp_df
            x_field = 'index_as_x'
        
        try:
            df_copy = df.copy()
            
            # 确保数据类型正确
            for col in [x_field]:
                if col and col in df.columns:
                    if df[col].dtype == 'object':
                        df_copy[col] = df_copy[col].astype(str)
            
            # 特殊处理：当y_field为'count'时，表示这是一个计数统计
            if y_field == 'count' or (y_field is None and agg_method == 'count'):
                counts = df_copy[x_field].value_counts()
                return [
                    {x_field: str(x), 'count': int(y)}
                    for x, y in counts.items()
                ]
            
            # 处理聚合
            grouped = None
            if y_field and y_field in df.columns:
                if agg_method == "mean":
                    grouped = df_copy.groupby(x_field)[y_field].mean()
                elif agg_method == "count":
                    grouped = df_copy.groupby(x_field)[y_field].count()
                elif agg_method == "sum":
                    grouped = df_copy.groupby(x_field)[y_field].sum()
                elif agg_method in [None, "none"]:
                    print("不使用聚合方法，直接使用原始数据")
                    grouped = df_copy.groupby(x_field)[y_field].mean()
            else:
                # 如果没有y_field，使用计数统计
                grouped = df_copy[x_field].value_counts().sort_index()
                y_field = 'count'  # 设置y_field为count
            
            if grouped is None:
                print(f"警告: Y轴字段 '{y_field}' 不存在或为None，使用计数作为Y轴")
                grouped = df_copy[x_field].value_counts().sort_index()
                y_field = 'count'  # 设置y_field为count
            
            # 直接返回G2格式数据
            return [
                {x_field: str(x), y_field: float(y)}
                for x, y in zip(grouped.index, grouped.values)
            ]
        
        except Exception as e:
            print(f"准备单系列数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 返回基本的错误数据结构
            return [
                {x_field: "错误", y_field: 0},
                {x_field: "请检查数据", y_field: 0}
            ]
    
    def _prepare_histogram_data(self, df: pd.DataFrame, x_field: str, binning: Dict[str, Any]) -> List[Dict[str, Any]]:
        """准备直方图数据"""
        if not x_field or x_field not in df.columns:
            raise ValueError(f"直方图需要有效的分布字段: {x_field}")
            
        try:
            # 获取数据
            values = df[x_field].dropna()
            
            # 计算bin边界
            bin_count = binning.get('bin_count', 30)
            bin_width = binning.get('bin_width')
            
            if bin_width:
                bins = np.arange(
                    values.min(),
                    values.max() + bin_width,
                    bin_width
                )
            else:
                bins = bin_count
                
            # 计算直方图数据
            hist, bin_edges = np.histogram(values, bins=bins)
            
            # 转换为G2格式
            data = []
            for i in range(len(hist)):
                data.append({
                    x_field: float(bin_edges[i]),
                    'count': int(hist[i])
                })
                
            return data
            
        except Exception as e:
            print(f"准备直方图数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def convert_to_antv_config(self, config: Dict[str, Any], chart_data=None) -> Dict[str, Any]:
        """
        将提取的配置转换为AntV G2配置
        
        参数:
            config: 提取的图表配置
            chart_data: G2格式的图表数据
            
        返回:
            AntV G2配置对象
        """
        chart_type = config.get("chart_type", "bar")
        title = config.get("title", "")
        x_field = config.get("x_field", "")
        y_field = config.get("y_field", "")
        hue_field = config.get("hue_column")
        is_stacked = config.get("is_stacked", False)
        binning = config.get("binning", {})
        
        # 获取显示名称
        display_names = {}
        if x_field:
            display_names[x_field] = self.get_display_name(x_field)
        if y_field:
            if y_field == "count":
                display_names[y_field] = "Count"
            else:
                display_names[y_field] = self.get_display_name(y_field, config.get("agg_method"))
        
        # 颜色配置
        colors = [
            '#FF6384',  # 红色
            '#36A2EB',  # 蓝色
            '#FFCE56',  # 黄色
            '#4BC0C0',  # 绿色
            '#9966FF',  # 紫色
            '#FF9F40',  # 橙色
            '#C7C7C7'   # 灰色
        ]
        
        # 映射图表类型到G2 V4类型
        type_map = {
            "bar": "interval",
            "line": "line",
            "scatter": "point",
            "pie": "interval",  # 饼图在G2中是特殊处理的interval
            "boxplot": "schema",  # 箱线图在G2 V4中使用schema几何标记
            "histogram": "interval"
        }
        g2_type = type_map.get(chart_type, "interval")
        
        # 构建基础G2配置
        g2_config = {
            "type": g2_type,
            "data": chart_data or [],
            "title": title,
            "autoFit": True,
            "animation": True
        }
        
        # 根据图表类型添加特定配置
        if chart_type == "histogram":
            g2_config.update({
                "xField": x_field,
                "yField": "count",
                "binField": x_field,
                "binWidth": binning.get("bin_width"),
                "binNumber": binning.get("bin_count", 30),
                "tooltip": {
                    "showMarkers": False,
                    "fields": [x_field, "count"],
                    "formatter": f"function(datum) {{ return {{ {x_field}: datum.{x_field}, count: datum.count }}; }}"
                },
                "meta": {
                    x_field: {
                        "alias": display_names.get(x_field, x_field)
                    },
                    "count": {
                        "alias": "Count"
                    }
                }
            })
        elif chart_type == "pie":
            # G2 V4 饼图配置
            g2_config.update({
                "angleField": "value",
                "colorField": "category",
                "radius": 0.8,
                "coordinate": {"type": "theta"},  # 添加极坐标系配置
                "label": {
                    "type": "outer",
                    "content": "{name}: {percentage}%"  # 显示名称和百分比
                },
                "tooltip": {
                    "showMarkers": False,
                    "formatter": f"function(datum) {{ return {{ 类别: datum.category, 数量: datum.value, 百分比: datum.percentage + '%' }}; }}"
                },
                "color": colors,
                "interactions": [
                    {"type": "element-active"},
                    {"type": "pie-legend-active"}
                ],
                "legend": {
                    "position": "right"
                }
            })
        elif chart_type == "boxplot":
            # G2 V4 箱线图配置
            g2_config = {
                "type": "schema",  # G2中使用schema几何标记表示箱线图
                "data": chart_data or [],
                "shapeType": "box",  # 指定形状为箱线图
                "title": title,
                "autoFit": True,
                "animation": True,
                "xField": x_field,
                "yField": "range",  # 使用包含5个统计值的range字段
                "meta": {
                    x_field: {
                        "alias": display_names.get(x_field, x_field)
                    },
                    "range": {
                        "alias": display_names.get(y_field, y_field)
                    }
                },
                "boxStyle": {
                    "stroke": "#545454",
                    "fill": "#1890FF",
                    "fillOpacity": 0.3
                },
                "tooltip": {
                    "showMarkers": False,
                    "showCrosshairs": False,
                    "formatter": f"function(datum) {{ return {{ {x_field}: datum.{x_field}, '最小值': datum.min, '下四分位数': datum.q1, '中位数': datum.median, '上四分位数': datum.q3, '最大值': datum.max }}; }}"
                },
                "interactions": [
                    {"type": "element-active"},
                    {"type": "legend-active"}
                ]
            }
        elif chart_type == "scatter":
            g2_config.update({
                "xField": x_field,
                "yField": y_field,
                "shape": "circle",
                "pointStyle": {
                    "fillOpacity": 0.7,
                    "stroke": "#ffffff",
                    "lineWidth": 0.5
                },
                "tooltip": {
                    "showMarkers": False,
                    "fields": [x_field, y_field],
                    "formatter": f"function(datum) {{ return {{ {x_field}: datum.{x_field}, {y_field}: datum.{y_field} }}; }}"
                },
                "meta": {
                    x_field: {
                        "alias": display_names.get(x_field, x_field)
                    },
                    y_field: {
                        "alias": display_names.get(y_field, y_field)
                    }
                }
            })
        else:
            # 柱状图、折线图通用配置
            g2_config.update({
                "xField": x_field,
                "yField": y_field,
                "meta": {
                    x_field: {
                        "alias": display_names.get(x_field, x_field)
                    },
                    y_field: {
                        "alias": display_names.get(y_field, y_field)
                    }
                }
            })
            
            # 添加分组字段
            if hue_field:
                g2_config["seriesField"] = hue_field
                g2_config["color"] = colors
                g2_config["meta"][hue_field] = {
                    "alias": self.get_display_name(hue_field)
                }
            else:
                g2_config["color"] = colors[0]
            
            # 堆叠配置
            if is_stacked and chart_type in ["bar", "column"]:
                g2_config["isStack"] = True
                # 确保堆叠图有正确的分组字段
                if not g2_config.get("seriesField") and hue_field:
                    g2_config["seriesField"] = hue_field
            
            # 图表样式配置
            if chart_type in ["bar", "column"]:
                g2_config["columnStyle"] = {
                    "fillOpacity": 0.7,
                    "lineWidth": 1
                }
            
            if chart_type == "line":
                g2_config["lineStyle"] = {
                    "lineWidth": 2
                }
                g2_config["point"] = {
                    "size": 5,
                    "shape": 'circle',
                    "style": {
                        "lineWidth": 1
                    }
                }
        
        # 添加图例配置（除了已有特定配置的图表类型）
        if chart_type not in ["pie", "boxplot"]:
            g2_config["legend"] = {
            "position": "right",
            "itemName": {
                "formatter": f"function(text) {{ return '{display_names.get(hue_field, '')}' || text; }}"
            }
        }
        
        # 添加工具提示配置（除了已有特定配置的图表类型）
        if not g2_config.get("tooltip") and chart_type not in ["pie", "boxplot"]:
            g2_config["tooltip"] = {
                "showMarkers": True,
                "showCrosshairs": chart_type == "line",
                "shared": True,
                "formatter": f"function(datum) {{ const result = {{}}; for (const key in datum) {{ result[key] = datum[key]; }}; return result; }}"
            }
        
        # 添加交互配置（除了已有特定配置的图表类型）
        if chart_type not in ["pie", "boxplot"] and not g2_config.get("interactions"):
            g2_config["interactions"] = [
            {"type": "element-active"},
            {"type": "legend-active"},
            {"type": "legend-filter"}
        ]
        
        return g2_config

    def convert_to_vegalite_config(self, config: Dict[str, Any], chart_data=None) -> Dict[str, Any]:
        """
        将提取的配置转换为Vega-Lite配置
        
        参数:
            config: 提取的图表配置
            chart_data: 处理后的图表数据
            
        返回:
            Vega-Lite配置对象
        """
        chart_type = config.get("chart_type", "bar")
        title = config.get("title", "")
        x_field = config.get("x_field", "")
        y_field = config.get("y_field", "")
        hue_field = config.get("hue_column")
        is_stacked = config.get("is_stacked", False)
        
        # 获取显示名称
        display_names = {}
        if x_field:
            display_names[x_field] = self.get_display_name(x_field)
        if y_field:
            if y_field == "count":
                display_names[y_field] = "Count"
            else:
                display_names[y_field] = self.get_display_name(y_field, config.get("agg_method"))
        
        # 确保有数据
        if not chart_data:
            chart_data = []
        
        # 基础Vega-Lite配置
        vegalite_config = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title,
            "data": {"values": chart_data},
            "width": "container",
            "height": 400,
            "background": "white",
            "config": {
                "axis": {
                    "titleFontSize": 14,
                    "labelFontSize": 12
                },
                "header": {
                    "titleFontSize": 14,
                    "labelFontSize": 12
                },
                "title": {
                    "fontSize": 16,
                    "font": "sans-serif",
                    "fontWeight": "bold"
                }
            }
        }
        
        # 根据图表类型设置mark和编码
        encoding = {}
        
        if chart_type == "bar":
            vegalite_config["mark"] = "bar"
            
            # 设置编码
            encoding = {
                "x": {
                    "field": x_field, 
                    "type": "nominal",
                    "title": display_names.get(x_field, x_field)
                },
                "y": {
                    "field": y_field, 
                    "type": "quantitative",
                    "title": display_names.get(y_field, y_field)
                },
                "tooltip": [
                    {"field": x_field, "type": "nominal", "title": display_names.get(x_field, x_field)},
                    {"field": y_field, "type": "quantitative", "title": display_names.get(y_field, y_field)}
                ]
            }
            
            # 处理分组和堆叠
            if hue_field:
                encoding["color"] = {
                    "field": hue_field, 
                    "type": "nominal",
                    "title": self.get_display_name(hue_field)
                }
                encoding["tooltip"].append({"field": hue_field, "type": "nominal", "title": self.get_display_name(hue_field)})
                
                if is_stacked:
                    vegalite_config["mark"] = {"type": "bar", "stack": "zero"}
                else:
                    # 分组柱状图
                    vegalite_config["mark"] = {"type": "bar", "opacity": 0.8}
        
        elif chart_type == "line":
            vegalite_config["mark"] = {"type": "line", "point": True}
            
            # 设置编码
            encoding = {
                "x": {
                    "field": x_field, 
                    "type": "nominal",
                    "title": display_names.get(x_field, x_field)
                },
                "y": {
                    "field": y_field, 
                    "type": "quantitative",
                    "title": display_names.get(y_field, y_field)
                },
                "tooltip": [
                    {"field": x_field, "type": "nominal", "title": display_names.get(x_field, x_field)},
                    {"field": y_field, "type": "quantitative", "title": display_names.get(y_field, y_field)}
                ]
            }
            
            if hue_field:
                encoding["color"] = {
                    "field": hue_field, 
                    "type": "nominal",
                    "title": self.get_display_name(hue_field)
                }
                encoding["tooltip"].append({"field": hue_field, "type": "nominal", "title": self.get_display_name(hue_field)})
        
        elif chart_type == "scatter":
            vegalite_config["mark"] = {"type": "point", "opacity": 0.7, "size": 60}
            
            # 设置编码
            encoding = {
                "x": {
                    "field": x_field, 
                    "type": "quantitative",
                    "title": display_names.get(x_field, x_field)
                },
                "y": {
                    "field": y_field, 
                    "type": "quantitative",
                    "title": display_names.get(y_field, y_field)
                },
                "tooltip": [
                    {"field": x_field, "type": "quantitative", "title": display_names.get(x_field, x_field)},
                    {"field": y_field, "type": "quantitative", "title": display_names.get(y_field, y_field)}
                ]
            }
            
            if hue_field:
                encoding["color"] = {
                    "field": hue_field, 
                    "type": "nominal",
                    "title": self.get_display_name(hue_field)
                }
                encoding["tooltip"].append({"field": hue_field, "type": "nominal", "title": self.get_display_name(hue_field)})
        
        elif chart_type == "pie":
            # 饼图在Vega-Lite中需要特殊处理
            # 对于饼图，我们需要确保数据包含category和value字段
            
            vegalite_config["mark"] = {"type": "arc", "innerRadius": 0}
            
            encoding = {
                "theta": {"field": "value", "type": "quantitative"},
                "color": {"field": "category", "type": "nominal"},
                "tooltip": [
                    {"field": "category", "type": "nominal", "title": "Category"},
                    {"field": "value", "type": "quantitative", "title": "Value"},
                    {"field": "percentage", "type": "quantitative", "title": "Percentage", "format": ".1f"}
                ]
            }
            
            # 添加百分比标签
            vegalite_config["transform"] = [{
                "calculate": "datum.percentage + '%'",
                "as": "percentageLabel"
            }]
            
            encoding["text"] = {"field": "percentageLabel", "type": "nominal"}
            vegalite_config["mark"]["text"] = {"radiusOffset": 10}
        
        elif chart_type == "boxplot":
            # 箱线图需要特殊处理
            # 在Vega-Lite中，箱线图有内置支持
            vegalite_config["mark"] = {"type": "boxplot", "extent": "min-max"}
            
            # 箱线图数据处理，Vega-Lite需要原始数据点
            # 如果传入的是已经计算好的统计值，需要转换回原始数据格式
            if chart_data and len(chart_data) > 0 and "range" in chart_data[0]:
                print("检测到预计算的箱线图数据，转换为Vega-Lite格式")
                # 转换为Vega-Lite可用的格式
                new_data = []
                for item in chart_data:
                    if x_field in item and "range" in item:
                        x_val = item[x_field]
                        # 创建合成数据点来表示箱线图
                        # 这里使用q1, median, q3和min/max值来创建合成数据
                        new_data.append({x_field: x_val, y_field: item.get("min", item["range"][0])})
                        new_data.append({x_field: x_val, y_field: item.get("q1", item["range"][1])})
                        new_data.append({x_field: x_val, y_field: item.get("median", item["range"][2])})
                        new_data.append({x_field: x_val, y_field: item.get("q3", item["range"][3])})
                        new_data.append({x_field: x_val, y_field: item.get("max", item["range"][4])})
                        # 添加异常值如果存在
                        if "outliers" in item and item["outliers"]:
                            for outlier in item["outliers"]:
                                new_data.append({x_field: x_val, y_field: outlier})
                
                chart_data = new_data
                vegalite_config["data"]["values"] = chart_data
            
            encoding = {
                "x": {
                    "field": x_field,
                    "type": "nominal",
                    "title": display_names.get(x_field, x_field)
                },
                "y": {
                    "field": y_field,
                    "type": "quantitative",
                    "title": display_names.get(y_field, y_field)
                }
            }
        
        elif chart_type == "histogram":
            # 直方图在Vega-Lite中有专门的mark类型
            vegalite_config["mark"] = "bar"
            
            bin_count = config.get("binning", {}).get("bin_count", 10)
            
            encoding = {
                "x": {
                    "field": x_field,
                    "type": "quantitative",
                    "bin": {"maxbins": bin_count},
                    "title": display_names.get(x_field, x_field)
                },
                "y": {
                    "aggregate": "count",
                    "title": "Count"
                }
            }
        
        # 添加编码到配置
        vegalite_config["encoding"] = encoding
        
        return vegalite_config