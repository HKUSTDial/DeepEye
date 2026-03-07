import pandas as pd
import numpy as np
import json
import logging
import re
from typing import Any, Dict, List, Union
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


# 自定义JSON编码器以处理pandas的Timestamp对象
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if pd.api.types.is_datetime64_any_dtype(obj) or isinstance(obj, pd.Timestamp):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super().default(obj)


class DatasetContextGenerator:
    """数据集上下文信息生成器"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ):
        """
        初始化数据集上下文生成器
        参数：
        - api_key (str): OpenAI API Key
        - base_url (str, optional): OpenAI API 基础 URL
        """
        self.api_key = api_key
        self.base_url = base_url
        resolved_model = (model_name or settings.LLM_MODEL or "").strip()
        if not resolved_model:
            raise ValueError("LLM_MODEL is required for report generation")
        self.model_name = resolved_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)

    def generate_context(
            self,
            data: Union[pd.DataFrame, str],
            dataset_name: str = "",
            dataset_description: str = "",
            n_samples: int = 5
        ) -> Dict:
        """
        生成符合data_context.json格式的数据集上下文信息
        
        参数：
        - data (pd.DataFrame | str): 数据集或 CSV 文件路径
        - dataset_name (str): 数据集名称
        - dataset_description (str): 数据集描述，默认为空
        - n_samples (int): 生成列全名时参考的样本行数
        
        返回：
        - Dict: JSON 结构化数据集信息
        """
        if isinstance(data, str):
            file_name = dataset_name or data.split("/")[-1]
            try:
                # 首先尝试 UTF-8 编码，保持原始列名
                df = pd.read_csv(data)
                # 输出读取到的列名，用于调试
                logger.info("CSV columns read with utf-8: %s", df.columns.tolist())
            except UnicodeDecodeError:
                # 如果 UTF-8 失败，尝试 latin1 编码
                logger.warning("UTF-8 decode failed, retry with latin1: %s", data)
                df = pd.read_csv(data, encoding='latin1')
                logger.info("CSV columns read with latin1: %s", df.columns.tolist())
            
            # 打印实际行数和列数
            logger.info("Dataset %s rows=%d cols=%d", file_name, len(df), len(df.columns))
            logger.debug("Dataset columns: %s", df.columns.tolist())
            
        else:
            df = data
            file_name = dataset_name or "dataset"
        
        # 尝试转换日期列，但保留原始列名
        df = self._try_parse_dates(df)
        
        # 对于日期列，我们需要将其转换为字符串以便JSON序列化
        date_cols = df.select_dtypes(include=['datetime64']).columns
        for col in date_cols:
            df[col] = df[col].dt.strftime("%Y-%m-%d")

        # **1️⃣ 计算类别列 & 数值列 & 日期列**
        data_types, categorical_columns, category_distribution, numerical_columns, datetime_columns = self._analyze_columns(df)

        # **2️⃣ 一次 LLM 调用生成【完整列名】+【数据集摘要】**
        # 准备样本数据，确保可以序列化
        sample_data = df.head(n_samples).to_dict(orient="records")
        
        llm_result = self._generate_column_names_and_summary(
            file_name, len(df), len(df.columns), df.columns.tolist(), 
            sample_data, data_types, 
            categorical_columns, numerical_columns, datetime_columns
        )

        # 确保使用原始列名作为键
        original_columns = df.columns.tolist()
        full_column_names = llm_result.get("full_column_names", {})
        # 确保所有列名都在full_column_names中
        for col in original_columns:
            if col not in full_column_names:
                full_column_names[col] = col
                
        dataset_summary = llm_result.get("dataset_summary", dataset_description or "暂无摘要信息")

        # **3️⃣ 组织 JSON 结构 (按照data_context.json格式)**
        dataset_context = {
            "name": file_name,
            "dataset_description": dataset_summary,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "fields_info": {},
            "categorical_details": {},
            "numerical_details": {},
            "datetime_details": {}  # 新增日期类型详情
        }
        
        # 填充fields_info，使用原始列名
        for col in original_columns:
            dtype = str(df[col].dtype)
            num_unique = df[col].nunique()
            missing = df[col].isna().sum()
            
            # 确定语义类型 (use pd.api.types to support pandas StringDtype)
            semantic_type = "UNKNOWN"
            if col in datetime_columns:
                semantic_type = "DATETIME"
            elif col.lower() in ["id", "customer_id", "user_id"] or "id" in col.lower():
                semantic_type = "ID"
            elif pd.api.types.is_bool_dtype(df[col]):
                semantic_type = "CATEGORY"
            elif pd.api.types.is_numeric_dtype(df[col]):
                semantic_type = "NUMERIC"
            elif num_unique < len(df) * 0.5:  # 如果唯一值数量相对较少，视为类别型
                semantic_type = "CATEGORY"
            elif pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                semantic_type = "TEXT"
            
            dataset_context["fields_info"][col] = {
                "dtype": dtype,
                "num_unique_values": int(num_unique),
                "missing_values": int(missing),
                "semantic_type": semantic_type
            }
        
        # 填充categorical_details (排除日期列)，使用原始列名
        for col, unique_count in categorical_columns.items():
            if col not in datetime_columns:  # 排除已被识别为日期的列
                # 获取这个列的每个值的计数
                value_counts = df[col].value_counts().to_dict()
                
                # 如果类别太多，只保留前10个和后10个
                if len(value_counts) > 20:
                    top_values = dict(list(df[col].value_counts().head(10).items()))
                    bottom_values = dict(list(df[col].value_counts().tail(10).items()))
                    value_counts = {**top_values, **bottom_values}
                
                dataset_context["categorical_details"][col] = {
                    "unique_values": value_counts,
                    "total_categories": unique_count
                }
        
        # 填充numerical_details，使用原始列名
        for col, stats in numerical_columns.items():
            dataset_context["numerical_details"][col] = {
                "min": stats.get("min", float(df[col].min())),
                "max": stats.get("max", float(df[col].max())),
                "mean": stats.get("mean", float(df[col].mean())),
                "std": stats.get("std", float(df[col].std())),
                "quartiles": {
                    "25%": stats.get("quartiles", {}).get("25%", float(df[col].quantile(0.25))),
                    "50%": stats.get("quartiles", {}).get("50%", float(df[col].quantile(0.50))),
                    "75%": stats.get("quartiles", {}).get("75%", float(df[col].quantile(0.75)))
                }
            }
            
        # 填充datetime_details，使用原始列名
        for col in datetime_columns:
            dataset_context["datetime_details"][col] = datetime_columns[col]

        return dataset_context
    
    def _try_parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """尝试将日期类型的列转换为datetime，保留原始列名"""
        # 常见的日期列名
        date_col_patterns = ["date", "time", "year", "month", "day", "创建日期", "更新日期", "时间"]
        
        for col in df.columns:
            # 如果列名包含日期相关关键词
            if any(pattern in col.lower() for pattern in date_col_patterns):
                try:
                    # 尝试转换为datetime，保留原始列名
                    df[col] = pd.to_datetime(df[col])
                    logger.info("Column %s converted to datetime", col)
                except Exception as e:
                    # 转换失败就保持原样
                    logger.debug("Column %s failed datetime conversion: %s", col, str(e))
                    pass
        
        return df
    
    def _generate_column_names_and_summary(
            self,
            dataset_name: str,
            total_rows: int,
            total_columns: int,
            column_names: List[str],
            sample_data: List[Dict],
            data_types: Dict[str, str],
            categorical_columns: Dict[str, int],
            numerical_columns: Dict[str, Dict[str, float]],
            datetime_columns: Dict[str, Dict[str, str]] = None
        ) -> Dict:
        """**一次性调用 LLM 生成完整列名 + 数据集摘要**"""
        datetime_part = ""
        if datetime_columns:
            # 使用自定义JSON编码器序列化datetime对象
            datetime_json = json.dumps(datetime_columns, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            datetime_part = f"\n\n**日期列的统计信息**：\n{datetime_json}"
            
        # 使用自定义JSON编码器序列化所有数据
        sample_json = json.dumps(sample_data, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
        data_types_json = json.dumps(data_types, indent=2, ensure_ascii=False)
        categorical_json = json.dumps(categorical_columns, indent=2, ensure_ascii=False)
        numerical_json = json.dumps(numerical_columns, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            
        prompt = f"""
        Dataset Name: {dataset_name}
        This dataset contains {total_rows} rows and {total_columns} columns.
        
        **Original Column Names**:
        {json.dumps(column_names, indent=2, ensure_ascii=False)}

        **First 5 Rows Sample Data**:
        {sample_json}

        **Data Types for Each Column**:
        {data_types_json}

        **Categorical Columns and Category Counts**:
        {categorical_json}

        **Statistical Information for Numerical Columns**:
        {numerical_json}{datetime_part}

        **Please complete the following tasks**:
        1️⃣ **Generate full column names for each column**, for example:
        - "age" → "User Age (years)"
        - "revenue" → "Order Revenue (USD)"
        
        **Important: Keep the original column names as JSON keys, do not modify the column name format**

        2️⃣ **Generate dataset summary**, which should describe:
        - Main content of the dataset
        - Important categorical columns and their category counts
        - Value ranges of important numerical columns
        - If there are date columns, describe the time span of the data

        **Please return directly in JSON format**:
        ```json
        {{
            "full_column_names": {{
                "age": "User Age (years)",
                "revenue": "Order Revenue (USD)"
            }},
            "dataset_summary": "This dataset contains information about..."
        }}
        ```
        """

        response = self._call_openai_api(prompt)
        return self._parse_json(response, default={"full_column_names": {col: col for col in column_names}, "dataset_summary": "No summary information available"})

    def _call_openai_api(self, prompt: str) -> str:
        """调用 OpenAI API（兼容新版 API）"""
        try:
            try:
                request_params: dict[str, Any] = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "You are a data analysis expert responsible for generating descriptive summaries of datasets."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.temperature,
                }
                if self.max_tokens and self.max_tokens > 0:
                    request_params["max_tokens"] = self.max_tokens

                response = self.client.chat.completions.create(**request_params)
                
                # 处理响应
                if isinstance(response, str):
                    return response.strip()
                elif hasattr(response, 'choices'):
                    content = response.choices[0].message.content
                    return content.strip() if content else ""
                elif isinstance(response, dict):
                    return response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                else:
                    logger.warning("Unknown OpenAI response type: %s", type(response))
                    logger.debug("OpenAI response payload: %s", response)
                    return str(response)
                
            except Exception as api_error:
                logger.error("OpenAI API call error: %s", str(api_error))
                if hasattr(api_error, 'response'):
                    logger.error("OpenAI response status=%s", api_error.response.status_code)
                    logger.error("OpenAI response body=%s", api_error.response.text)
                raise
            
        except Exception:
            logger.exception("OpenAI API call failed")
            raise

    def _parse_json(self, text: str, default: dict) -> dict:
        """解析 LLM 生成的 JSON，确保格式正确"""
        try:
            json_match = re.search(r"```json\n(.*)\n```", text, re.DOTALL)
            json_text = json_match.group(1) if json_match else text
            parsed_json = json.loads(json_text)
            return parsed_json if isinstance(parsed_json, dict) else default
        except Exception:
            return default

    def _analyze_columns(self, data: pd.DataFrame):
        """分析数据列类型、类别列统计、数值列统计和日期列统计"""
        data_types = {}
        categorical_columns = {}
        category_distribution = {}
        numerical_columns = {}
        datetime_columns = {}

        # 使用原始列名
        for col in data.columns:
            dtype = str(data[col].dtype)
            data_types[col] = dtype  # 记录数据类型
            
            # 检查是否为日期类型
            if pd.api.types.is_datetime64_any_dtype(data[col]) or self._is_date_column(data[col]):
                try:
                    date_series = pd.to_datetime(data[col])
                    min_date = date_series.min()
                    max_date = date_series.max()
                    datetime_columns[col] = {
                        "min_date": min_date.strftime("%Y-%m-%d") if not pd.isna(min_date) else None,
                        "max_date": max_date.strftime("%Y-%m-%d") if not pd.isna(max_date) else None,
                        "date_range_days": (max_date - min_date).days if not pd.isna(min_date) and not pd.isna(max_date) else None
                    }
                    continue  # 如果是日期类型，跳过后续的分析
                except Exception as e:
                    logger.debug("Failed processing datetime column %s: %s", col, str(e))
                    # 如果转换失败，则当作普通列处理
                    pass
            
            # 非日期类型的处理 (use pd.api.types to support pandas StringDtype)
            if self._is_categorical(data[col]):
                unique_values_count = data[col].nunique()
                categorical_columns[col] = unique_values_count
                category_distribution[col] = data[col].value_counts(normalize=True).head(5).to_dict()  # 前 5 类占比
            
            elif pd.api.types.is_numeric_dtype(data[col]):
                numerical_columns[col] = {
                    "min": float(data[col].min()),
                    "max": float(data[col].max()),
                    "mean": float(data[col].mean()),
                    "std": float(data[col].std()),
                    "quartiles": {
                        "25%": float(data[col].quantile(0.25)),
                        "50%": float(data[col].quantile(0.50)),
                        "75%": float(data[col].quantile(0.75))
                    }
                }
        
        return data_types, categorical_columns, category_distribution, numerical_columns, datetime_columns

    def _is_categorical(self, series):
        """判断一个列是否为类别型 (supports pandas StringDtype)"""
        if pd.api.types.is_bool_dtype(series):
            return True

        # 如果是对象/字符串类型（通常是字符串）
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            return True
        
        # 如果是数值类型，但唯一值较少（比如小于列长度的10%）
        if pd.api.types.is_numeric_dtype(series):
            unique_count = series.nunique()
            return unique_count < len(series) * 0.1 and unique_count < 20
        
        return False
    
    def _is_date_column(self, series):
        """检查是否为日期列，尝试匹配常见的日期格式 (supports pandas StringDtype)"""
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            return False
            
        # 取前10个非空值样本
        samples = series.dropna().head(10)
        if len(samples) == 0:
            return False
            
        # 检查样本是否都匹配常见的日期格式
        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{4}',   # MM/DD/YYYY
            r'\d{1,2}-\d{1,2}-\d{4}',   # DD-MM-YYYY
            r'\d{4}/\d{1,2}/\d{1,2}'    # YYYY/MM/DD
        ]
        
        for sample in samples:
            is_date = False
            for pattern in date_patterns:
                if re.fullmatch(pattern, str(sample)):
                    is_date = True
                    break
            if not is_date:
                return False
                
        return True
