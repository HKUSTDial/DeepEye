import json
import os
import importlib.util
import math
import numpy as np
from typing import Any, Dict, List, Optional
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# --- 路径配置 ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
CHARTS_DIR = os.path.join(PUBLIC_DIR, "charts")
CONFIGS_DIR = os.path.join(PUBLIC_DIR, "configs")

# --- 辅助函数 ---
def load_schema() -> Dict[str, Any]:
    schema_path = os.path.join(CONFIGS_DIR, "dashboard_config.json")
    if not os.path.exists(schema_path): return {}
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_data_path(schema: Dict[str, Any]) -> str:
    raw_path = schema.get("dataSource", {}).get("path", "")
    filename = os.path.basename(raw_path)
    local_path = os.path.join(PUBLIC_DIR, "data", filename)
    return local_path if os.path.exists(local_path) else raw_path 

def load_dataset(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path): return pd.DataFrame()
    df = pd.read_csv(csv_path)
    # 转换日期列
    date_cols = ["transaction_date", "enrollment_date", "birth_date", "created_at"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    
    # 预计算一些常用的过滤字段
    if "enrollment_date" in df.columns:
        df["enrollment_year"] = df["enrollment_date"].dt.year
    
    return df

def dynamic_import_plot(py_filename: str):
    module_path = os.path.join(CHARTS_DIR, py_filename)
    if not os.path.exists(module_path): raise FileNotFoundError(f"Script not found: {module_path}")
    spec = importlib.util.spec_from_file_location("chart_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "plot")

def convert_numpy_types(obj):
    """递归转换 numpy 类型为 Python 原生类型，并处理 NaN/Inf"""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.ndarray):
        return [convert_numpy_types(item) for item in obj.tolist()]
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    else:
        return obj

def chart_option_from_plot(plot_fn, df: pd.DataFrame) -> Dict[str, Any]:
    c = plot_fn(df)
    option_json = c.dump_options()
    option_dict = json.loads(option_json)
    
    # 修复 PyECharts datasetIndex 导致的数据丢失问题
    # PyECharts 2.0.7 在 dump_options() 时，如果配置了 datasetIndex 但没有 dataset，
    # 会导致 series.data 被清空为 null。从 chart.options 中恢复正确的数据。
    if hasattr(c, 'options') and isinstance(c.options, dict):
        chart_options = c.options
        if 'series' in chart_options and isinstance(chart_options['series'], list):
            chart_series = chart_options['series']
            # 检查并修复每个 series
            if 'series' in option_dict and isinstance(option_dict['series'], list):
                for i, series in enumerate(option_dict['series']):
                    # 如果存在 datasetIndex 但没有 dataset，且 data 全是 null
                    if (series.get('datasetIndex') is not None and 
                        'dataset' not in option_dict and
                        i < len(chart_series)):
                        data = series.get('data', [])
                        # 检查 data 是否全是 null
                        if isinstance(data, list) and len(data) > 0 and all(x is None for x in data):
                            # 从 chart.options 中恢复正确的数据
                            original_series = chart_series[i]
                            original_data = original_series.get('data', [])
                            if original_data and not all(x is None for x in original_data):
                                series['data'] = convert_numpy_types(original_data)
                                # 移除 datasetIndex 和 seriesLayoutBy
                                if 'datasetIndex' in series:
                                    del series['datasetIndex']
                                if 'seriesLayoutBy' in series:
                                    del series['seriesLayoutBy']
    
    # 最后统一做一次清理，处理所有可能的 NaN/Inf
    return convert_numpy_types(option_dict)

def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if not filters or df.empty: return df
    filtered = df.copy()
    for field, cond in filters.items():
        if field not in filtered.columns: continue
        op, val = cond.get("operator"), cond.get("value")
        if val is None or val == "All": continue
        try:
            # 标量等值过滤
            if op == "equals" or not isinstance(val, (list, tuple)):
                filtered = filtered[filtered[field] == val]
            # 多选：等价于 in
            elif op in ("in", "one_of") and isinstance(val, (list, tuple)):
                filtered = filtered[filtered[field].isin(val)]
            # 区间：between
            elif op == "between" and isinstance(val, (list, tuple)) and len(val) == 2:
                v1, v2 = val[0], val[1]
                # 如果是日期列，尝试转为 datetime 再比较
                if "date" in field or "time" in field:
                    v1 = pd.to_datetime(v1, errors="coerce")
                    v2 = pd.to_datetime(v2, errors="coerce")
                filtered = filtered[(filtered[field] >= v1) & (filtered[field] <= v2)]
        except Exception as e:
            # 出错就跳过这个过滤条件，避免整张表挂掉
            print(f"[apply_filters] skip filter on {field} due to error: {e}")
    return filtered

# --- 引擎 ---
class DashboardEngine:
    def __init__(self):
        self.schema = load_schema()
        data_path = resolve_data_path(self.schema)
        print(f"[DashboardEngine] init, data path = {data_path}")
        self.full_df = load_dataset(data_path)
        print(f"[DashboardEngine] init, loaded rows = {len(self.full_df)}")
        self.highlight_blocks: List[Dict[str, Any]] = [
            b for b in self.schema.get("blocks", []) if b.get("blockType") == "highlight"
        ]
        # 处理 filter 的 range
        self._process_filter_ranges()
        # 处理 filter 的 options
        self._process_filter_options()

    def get_layout_config(self):
        # 返回配置中的模板路径
        return self.schema.get("layout", {})
    
    def _process_filter_options(self):
        """处理 select/multiselect 类型 filter 的 options"""
        if self.full_df.empty: return
        
        filter_blocks = [b for b in self.schema.get("blocks", []) if b.get("blockType") == "filter"]
        for block in filter_blocks:
            bc = block.get("blockContent", {})
            if bc.get("controlType") in ("select", "multiselect") and not bc.get("options"):
                field = bc.get("field")
                if field in self.full_df.columns:
                    unique_vals = self.full_df[field].unique().tolist()
                    # 排序并转为字符串
                    options = ["All"] + sorted([str(v) for v in unique_vals if pd.notna(v)])
                    bc["options"] = options
                    print(f"[_process_filter_options] Set options for {field}: {len(options)} values")

    def _process_filter_ranges(self):
        """处理 slider 类型 filter 的 range，根据实际数据设置最小/最大值"""
        print(f"[_process_filter_ranges] Starting to process filter ranges...")
        print(f"[_process_filter_ranges] DataFrame shape: {self.full_df.shape}")
        print(f"[_process_filter_ranges] DataFrame columns: {list(self.full_df.columns)}")
        
        if self.full_df.empty:
            print(f"[_process_filter_ranges] DataFrame is empty, skipping")
            return
        
        filter_blocks = [b for b in self.schema.get("blocks", []) if b.get("blockType") == "filter"]
        print(f"[_process_filter_ranges] Found {len(filter_blocks)} filter blocks")
        
        for block in filter_blocks:
            block_id = block.get("id", "unknown")
            block_content = block.get("blockContent", {})
            control_type = block_content.get("controlType", "select")
            field = block_content.get("field")
            
            print(f"[_process_filter_ranges] Processing block: {block_id}, type: {control_type}, field: {field}")
            
            # 只处理 slider 或 range 类型的 filter
            if control_type not in ("slider", "range"):
                print(f"[_process_filter_ranges] Skipping {block_id}: not a slider/range (type={control_type})")
                continue
            
            if not field:
                print(f"[_process_filter_ranges] Skipping {block_id}: no field specified")
                continue
            
            if field not in self.full_df.columns:
                print(f"[_process_filter_ranges] Skipping {block_id}: field '{field}' not in DataFrame columns")
                continue
            
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
                    
                    values = self.full_df[field].apply(extract_hour).dropna()
                else:
                    # 数值字段：转换为数值
                    values = pd.to_numeric(self.full_df[field], errors='coerce').dropna()
                
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
                            step = max(1, int(range_size / 100))
                    
                    # 更新或创建 range 配置
                    block_content['range'] = {
                        'min': min_val,
                        'max': max_val,
                        'step': step
                    }
                    
                    print(f"[_process_filter_ranges] Set range for {field}: min={min_val}, max={max_val}, step={step}")
                    
            except Exception as e:
                print(f"[_process_filter_ranges] Failed to process range for {field}: {e}")

    def compute_charts(self, filters=None):
        df = apply_filters(self.full_df, filters)
        print(f"[compute_charts] filters = {filters}, rows after filter = {len(df)}")
        results = {}
        view_blocks = [b for b in self.schema.get("blocks", []) if b.get("blockType") == "view"]
        
        for block in view_blocks:
            bid = block.get("id")
            py_name = block.get("blockContent", {}).get("python_code_name")
            try:
                print(f"[compute_charts] loading plot for block {bid} from {py_name}")
                plot_fn = dynamic_import_plot(py_name)
                # 后端只负责给数据，美化工作交给前端 Theme
                option = chart_option_from_plot(plot_fn, df)
                # 只打印一下关键信息，避免日志太大
                print(f"[compute_charts] block {bid} option keys = {list(option.keys())}")
                results[bid] = {"option": option}
            except Exception as e:
                print(f"[compute_charts] ERROR for block {bid}: {e}")
                results[bid] = {"error": str(e)}
        return results

    def compute_highlights(
        self, global_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """计算高亮块数据
        
        配置格式（仅支持新格式）：
        {
            "expression": "unit_price * transaction_qty",  // 字段名或算术表达式
            "type": "sum",                                   // 聚合类型
            "title": "Total Revenue",
            "unit": "currency"
        }
        
        expression 可以是：
        - 单个字段名：transaction_id
        - 算术表达式：unit_price * transaction_qty, (revenue - cost) / revenue
        """
        print(f"\n🔍 [DEBUG] ========== 开始计算高亮数据 ==========")
        print(f"🔍 [DEBUG] 高亮块数量: {len(self.highlight_blocks)}")
        print(f"🔍 [DEBUG] 过滤器: {global_filters}")
        
        df = apply_filters(self.full_df, global_filters or {})
        print(f"🔍 [DEBUG] 过滤后数据行数: {len(df)}")
        
        items: List[Dict[str, Any]] = []
        for i, block in enumerate(self.highlight_blocks):
            print(f"\n🔍 [DEBUG] 处理高亮块 {i+1}/{len(self.highlight_blocks)}: {block.get('id')}")
            
            bc = block.get("blockContent", {})
            
            # 只支持新格式
            expression = bc.get("expression")
            htype = bc.get("type")
            unit = bc.get("unit") or ""
            title = bc.get("title") or block.get("id")
            
            # 验证必需字段
            if not expression or not htype:
                print(f"❌ [DEBUG] 缺少必需字段 - expression: {expression}, type: {htype}")
                item = {
                    "id": block.get("id"),
                    "title": title,
                    "unit": unit,
                    "value": "N/A",
                }
                items.append(item)
                continue
            
            print(f"🔍 [DEBUG] 表达式: {expression}, 类型: {htype}, 单位: {unit}")
            
            value = None
            try:
                # 计算表达式的值
                series = self._evaluate_expression(df, expression)
                
                if series is not None:
                    # 根据类型进行聚合
                    value = self._aggregate_series(series, htype, expression, df)
                    print(f"🔍 [DEBUG] 计算结果: {value}")
                else:
                    print(f"❌ [DEBUG] 表达式求值失败")
                    
            except Exception as e:
                print(f"❌ [DEBUG] 计算失败: {e}")
                import traceback
                traceback.print_exc()
                value = None
            
            # 格式化数值
            formatted_value = self._format_highlight_value(value, unit, htype)
            
            item = {
                "id": block.get("id"),
                "title": title,
                "unit": unit,
                "value": formatted_value,
            }
            items.append(item)
            print(f"🔍 [DEBUG] 高亮项: {item}")
        
        print(f"\n🔍 [DEBUG] ========== 高亮数据计算完成 ==========")
        return items
    
    def _evaluate_expression(self, df: pd.DataFrame, expression: str) -> Optional[pd.Series]:
        """求值表达式，返回一个 Series"""
        if not expression:
            return None
        
        expression = expression.strip()
        
        # 如果是单个字段名
        if expression in df.columns:
            print(f"🔍 [DEBUG] 表达式是单个字段: {expression}")
            return df[expression]
        
        # 如果是算术表达式，使用 eval
        try:
            print(f"🔍 [DEBUG] 尝试求值表达式: {expression}")
            # 使用 DataFrame.eval 求值
            result = df.eval(expression, engine='python')
            
            # 如果结果是 Series，直接返回
            if isinstance(result, pd.Series):
                return result
            # 如果结果是标量，创建一个常量 Series
            elif isinstance(result, (int, float)):
                return pd.Series([result] * len(df))
            else:
                print(f"❌ [DEBUG] 表达式求值结果类型不支持: {type(result)}")
                return None
                
        except Exception as e:
            print(f"❌ [DEBUG] 表达式求值失败: {e}")
            return None
    
    def _aggregate_series(self, series: pd.Series, agg_type: str, expression: str, df: pd.DataFrame) -> Any:
        """对 Series 进行聚合"""
        if agg_type == "nunique":
            return int(series.nunique(dropna=True))
        
        elif agg_type == "count":
            return int(series.count())
        
        elif agg_type == "sum":
            return float(pd.to_numeric(series, errors="coerce").sum())
        
        elif agg_type == "mean":
            return float(pd.to_numeric(series, errors="coerce").mean())
        
        elif agg_type == "max":
            # 对于数值型，返回最大值
            numeric_series = pd.to_numeric(series, errors="coerce")
            if numeric_series.notna().any():
                return float(numeric_series.max())
            # 对于非数值型，返回字符串最大值
            return str(series.max())
        
        elif agg_type == "min":
            # 对于数值型，返回最小值
            numeric_series = pd.to_numeric(series, errors="coerce")
            if numeric_series.notna().any():
                return float(numeric_series.min())
            # 对于非数值型，返回字符串最小值
            return str(series.min())
        
        elif agg_type == "mode":
            # 返回众数（出现最多的值）
            # 对于分类数据，找出现次数最多的类别
            value_counts = series.value_counts()
            if len(value_counts) > 0:
                return str(value_counts.index[0])
            return None
        
        else:
            print(f"❌ [DEBUG] 不支持的聚合类型: {agg_type}")
            return None
    
    def _format_highlight_value(self, value: Any, unit: str, htype: str) -> str:
        """格式化高亮值为显示字符串"""
        if value is None:
            return "N/A"
        
        # 日期/时间格式检测与处理
        # 尝试检测是否为日期或时间戳类型
        if isinstance(value, (pd.Timestamp, pd.DatetimeIndex)):
            # 检查是否只有日期部分（时间为 00:00:00）
            if value.hour == 0 and value.minute == 0 and value.second == 0:
                # 只展示日期
                return value.strftime('%Y-%m-%d')
            else:
                # 展示日期和时间
                return value.strftime('%Y-%m-%d %H:%M:%S')
        
        # 如果是字符串，尝试解析为日期
        if isinstance(value, str):
            try:
                dt = pd.to_datetime(value, errors='coerce')
                if pd.notna(dt):
                    # 检查是否只有日期部分
                    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                        return dt.strftime('%Y-%m-%d')
                    else:
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass  # 不是日期，继续其他格式处理
        
        # 货币格式
        if unit == "currency" or unit == "USD":
            if isinstance(value, (int, float)):
                # 如果值很大，使用 K/M 格式
                if abs(value) >= 1000000:
                    return f"{value/1000000:.2f}M"
                elif abs(value) >= 1000:
                    return f"{value/1000:.2f}K"
                return f"{value:,.2f}"
            return str(value)
        
        # 百分比格式
        elif unit == "%":
            if isinstance(value, (int, float)):
                return f"{value:.1f}%"
            return str(value)
        
        # 数值格式
        elif isinstance(value, float):
            # 如果是整数值，不显示小数
            if value == int(value):
                # 如果值很大，使用 K/M 格式
                if abs(value) >= 1000000:
                    return f"{value/1000000:.2f}M"
                elif abs(value) >= 1000:
                    return f"{int(value)/1000:.2f}K"
                return f"{int(value):,}"
            # 否则保留2位小数
            return f"{value:,.2f}"
        
        elif isinstance(value, int):
            # 如果值很大，使用 K/M 格式
            if abs(value) >= 1000000:
                return f"{value/1000000:.2f}M"
            elif abs(value) >= 1000:
                return f"{value/1000:.2f}K"
            return f"{value:,}"
        
        # 其他类型直接转字符串
        return str(value)

# --- App ---
engine = DashboardEngine()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

@app.get("/")
@app.head("/")
def index():
    # 返回 Shell 页面
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

@app.get("/init")
def init_data():
    # 刷新 Schema
    engine.schema = load_schema()
    print("[/init] schema loaded, blocks =", len(engine.schema.get("blocks", [])))
    layout = engine.get_layout_config()
    charts = engine.compute_charts()
    highlights = engine.compute_highlights()
    print("[/init] charts keys =", list(charts.keys()))
    print("[/init] highlights count =", len(highlights))
    return convert_numpy_types({
        "layout": layout,  # 包含 templatePath
        "blocks": engine.schema.get("blocks", []),
        "charts": charts,
        "highlights": highlights
    })

@app.get("/data")
def get_raw_data():
    """返回原始数据的 JSON 格式，供详情页表格使用"""
    if engine.full_df.empty:
        return []
    
    # 转换为 records 格式，并限制返回条数以防崩溃
    data = engine.full_df.head(500).to_dict(orient="records")
    return convert_numpy_types(data)

# WebSocket (保持不变)
manager = WebSocketDisconnect
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "filter":
                filters = data.get("filters", {})
                await websocket.send_json(convert_numpy_types({
                    "type": "update",
                    "charts": engine.compute_charts(filters),
                    "highlights": engine.compute_highlights(filters)
                }))
    except Exception: pass
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)