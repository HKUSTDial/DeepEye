import json
import os
import importlib.util
import math
from datetime import date, datetime
import numpy as np
from typing import Any, Dict, List, Optional
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# --- Path configuration ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
CHARTS_DIR = os.path.join(PUBLIC_DIR, "charts")
CONFIGS_DIR = os.path.join(PUBLIC_DIR, "configs")
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# --- Helper functions ---
def load_schema() -> Dict[str, Any]:
    schema_path = os.path.join(CONFIGS_DIR, "dashboard_config.json")
    if not os.path.exists(schema_path): return {}
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def resolve_data_path(schema: Dict[str, Any]) -> str:
    raw_path = schema.get("dataSource", {}).get("path", "")
    data_dir = os.path.join(PUBLIC_DIR, "data")

    if isinstance(raw_path, str) and raw_path:
        normalized = raw_path.rstrip("/\\")
        filename = os.path.basename(normalized)
        if filename:
            local_path = os.path.join(data_dir, filename)
            if os.path.isfile(local_path):
                return local_path
        if os.path.isfile(raw_path):
            return raw_path

    if os.path.isdir(data_dir):
        candidates = sorted(
            [
                os.path.join(data_dir, name)
                for name in os.listdir(data_dir)
                if os.path.isfile(os.path.join(data_dir, name))
            ]
        )
        if len(candidates) == 1:
            return candidates[0]
        csv_candidates = [path for path in candidates if path.lower().endswith(".csv")]
        if len(csv_candidates) == 1:
            return csv_candidates[0]

    return ""

def load_dataset(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path): return pd.DataFrame()
    df = pd.read_csv(csv_path)
    # Convert date columns
    date_cols = ["transaction_date", "enrollment_date", "birth_date", "created_at"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    
    # Pre-compute some commonly used filter fields
    if "enrollment_date" in df.columns:
        df["enrollment_year"] = df["enrollment_date"].dt.year
    
    return df

def resolve_cors_origins() -> List[str]:
    raw_value = os.environ.get("BACKEND_CORS_ORIGINS", "").strip()
    if not raw_value:
        return list(DEFAULT_CORS_ORIGINS)

    parsed: Any
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed = [item.strip() for item in raw_value.split(",")]

    if isinstance(parsed, str):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return list(DEFAULT_CORS_ORIGINS)

    origins = [str(origin).rstrip("/") for origin in parsed if str(origin).strip() and str(origin).strip() != "*"]
    return origins or list(DEFAULT_CORS_ORIGINS)

def dynamic_import_plot(py_filename: str):
    if not py_filename:
        raise ValueError("Missing python_code_name for dashboard view block")
    module_path = os.path.join(CHARTS_DIR, py_filename)
    if not os.path.exists(module_path): raise FileNotFoundError(f"Script not found: {module_path}")
    spec = importlib.util.spec_from_file_location("chart_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "plot")

def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types and handle NaN/Inf"""
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
    
    # Fix PyECharts datasetIndex data loss issue
    # PyECharts 2.0.7: when dump_options() is called, if datasetIndex is configured but no dataset exists,
    # series.data will be cleared to null. Restore correct data from chart.options.
    if hasattr(c, 'options') and isinstance(c.options, dict):
        chart_options = c.options
        if 'series' in chart_options and isinstance(chart_options['series'], list):
            chart_series = chart_options['series']
            # Check and fix each series
            if 'series' in option_dict and isinstance(option_dict['series'], list):
                for i, series in enumerate(option_dict['series']):
                    # If datasetIndex exists but no dataset, and data is all null
                    if (series.get('datasetIndex') is not None and 
                        'dataset' not in option_dict and
                        i < len(chart_series)):
                        data = series.get('data', [])
                        # Check if data is all null
                        if isinstance(data, list) and len(data) > 0 and all(x is None for x in data):
                            # Restore correct data from chart.options
                            original_series = chart_series[i]
                            original_data = original_series.get('data', [])
                            if original_data and not all(x is None for x in original_data):
                                series['data'] = convert_numpy_types(original_data)
                                # Remove datasetIndex and seriesLayoutBy
                                if 'datasetIndex' in series:
                                    del series['datasetIndex']
                                if 'seriesLayoutBy' in series:
                                    del series['seriesLayoutBy']
    
    # Final cleanup pass to handle all possible NaN/Inf
    return convert_numpy_types(option_dict)

def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if not filters or df.empty: return df
    filtered = df.copy()
    for field, cond in filters.items():
        # Special handling: if field is not in columns but data is in long format (has dimension column)
        # try to filter by dimension
        if field not in filtered.columns and "dimension" in filtered.columns:
            op, val = cond.get("operator"), cond.get("value")
            if val is None or val == "All": continue
            try:
                # Logic: if field matches a dimension value, filter within that dimension
                # e.g., field="date" corresponds to dimension="monthly_revenue"
                # Here we make a simple heuristic: if the filter's field is in the unique values of the dimension column,
                # or we directly filter by dimension
                
                # Special filtering logic for long format:
                # 1. Find data under that dimension
                # 2. Filter by name within that dimension
                # 3. Keep data from other dimensions (or decide based on requirements)
                
                # Solution: if field is a value in dimension, filter name under that dimension
                if field in filtered["dimension"].unique():
                    mask = (filtered["dimension"] == field)
                    if op == "equals" or not isinstance(val, (list, tuple)):
                        filtered = filtered[~mask | ((filtered["dimension"] == field) & (filtered["name"] == str(val)))]
                    elif op in ("in", "one_of") and isinstance(val, (list, tuple)):
                        val_strs = [str(v) for v in val]
                        filtered = filtered[~mask | ((filtered["dimension"] == field) & (filtered["name"].isin(val_strs)))]
                    continue
            except Exception as e:
                print(f"[apply_filters] skip long-format filter on {field} due to error: {e}")

        if field not in filtered.columns: continue
        op, val = cond.get("operator"), cond.get("value")
        if val is None or val == "All": continue
        try:
            column = filtered[field]
            sample = next((item for item in column.tolist() if pd.notna(item)), None)

            def coerce_scalar(raw):
                if raw is None:
                    return None
                if pd.api.types.is_datetime64_any_dtype(column) or isinstance(sample, (pd.Timestamp, datetime, date)):
                    converted = pd.to_datetime(raw, errors="coerce")
                    return None if pd.isna(converted) else converted
                if pd.api.types.is_bool_dtype(column) or isinstance(sample, bool):
                    if isinstance(raw, str):
                        normalized = raw.strip().lower()
                        if normalized in {"true", "1", "yes"}:
                            return True
                        if normalized in {"false", "0", "no"}:
                            return False
                    return raw
                if pd.api.types.is_numeric_dtype(column) or (
                    isinstance(sample, (int, float, np.integer, np.floating)) and not isinstance(sample, bool)
                ):
                    converted = pd.to_numeric([raw], errors="coerce")[0]
                    if pd.isna(converted):
                        return raw
                    return converted.item() if hasattr(converted, "item") else converted
                return raw

            # Scalar equality filter
            if op == "equals" or not isinstance(val, (list, tuple)):
                coerced = coerce_scalar(val)
                series = filtered[field]
                if isinstance(coerced, pd.Timestamp):
                    series = pd.to_datetime(series, errors="coerce")
                filtered = filtered[series == coerced]
            # Multi-select: equivalent to in
            elif op in ("in", "one_of") and isinstance(val, (list, tuple)):
                coerced_values = [coerce_scalar(item) for item in val]
                series = filtered[field]
                if any(isinstance(item, pd.Timestamp) for item in coerced_values):
                    series = pd.to_datetime(series, errors="coerce")
                filtered = filtered[series.isin(coerced_values)]
            # Range: between
            elif op == "between" and isinstance(val, (list, tuple)) and len(val) == 2:
                v1 = coerce_scalar(val[0])
                v2 = coerce_scalar(val[1])
                series = filtered[field]
                if isinstance(v1, pd.Timestamp) or isinstance(v2, pd.Timestamp):
                    series = pd.to_datetime(series, errors="coerce")
                filtered = filtered[(series >= v1) & (series <= v2)]
        except Exception as e:
            # Skip this filter condition on error to avoid crashing the entire table
            print(f"[apply_filters] skip filter on {field} due to error: {e}")
    return filtered

# --- Engine ---
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
        # Process filter ranges
        self._process_filter_ranges()
        # Process filter options
        self._process_filter_options()

    def get_layout_config(self):
        # Return template path from configuration
        return self.schema.get("layout", {})
    
    def _process_filter_options(self):
        """Process options for select/multiselect type filters"""
        if self.full_df.empty: return
        
        filter_blocks = [b for b in self.schema.get("blocks", []) if b.get("blockType") == "filter"]
        for block in filter_blocks:
            bc = block.get("blockContent", {})
            if bc.get("controlType") in ("select", "multiselect") and not bc.get("options"):
                field = bc.get("field")
                
                # Special handling for long format: if field is not in columns but is a value in dimension column
                if field not in self.full_df.columns and "dimension" in self.full_df.columns:
                    if field in self.full_df["dimension"].unique():
                        # Extract unique values from name column under that dimension
                        unique_vals = self.full_df[self.full_df["dimension"] == field]["name"].unique().tolist()
                        options = ["All"] + sorted([str(v) for v in unique_vals if pd.notna(v)])
                        bc["options"] = options
                        print(f"[_process_filter_options] Set options for dimension {field}: {len(options)} values")
                        continue

                if field in self.full_df.columns:
                    unique_vals = self.full_df[field].unique().tolist()
                    # Sort and convert to strings
                    options = ["All"] + sorted([str(v) for v in unique_vals if pd.notna(v)])
                    bc["options"] = options
                    print(f"[_process_filter_options] Set options for {field}: {len(options)} values")

    def _process_filter_ranges(self):
        """Process ranges for slider type filters, set min/max based on actual data"""
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
            
            # Only process slider or range type filters
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
                # Determine if it's a time field
                is_time_field = 'time' in field.lower() or 'hour' in field.lower()
                
                if is_time_field:
                    # Time field: extract hour from time string
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
                    # Numeric field: convert to numeric
                    values = pd.to_numeric(self.full_df[field], errors='coerce').dropna()
                
                if len(values) > 0:
                    min_val = float(values.min())
                    max_val = float(values.max())
                    
                    # Calculate appropriate step
                    if is_time_field:
                        step = 1  # Time field step is 1 hour
                    else:
                        # For numeric fields, auto-calculate step based on range
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
                    
                    # Update or create range configuration
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
                if not py_name:
                    raise ValueError(f"Missing python_code_name for block {bid}")
                print(f"[compute_charts] loading plot for block {bid} from {py_name}")
                plot_fn = dynamic_import_plot(py_name)
                # Backend only provides data, styling is handled by frontend Theme
                option = chart_option_from_plot(plot_fn, df)
                # Only print key information to avoid log bloat
                print(f"[compute_charts] block {bid} option keys = {list(option.keys())}")
                results[bid] = {"option": option}
            except Exception as e:
                print(f"[compute_charts] ERROR for block {bid}: {e}")
                results[bid] = {"error": str(e)}
        return results

    def compute_highlights(
        self, global_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Compute highlight block data
        
        Configuration format (only new format supported):
        {
            "expression": "unit_price * transaction_qty",  // Field name or arithmetic expression
            "type": "sum",                                   // Aggregation type
            "title": "Total Revenue",
            "unit": "currency"
        }
        
        expression can be:
        - Single field name: transaction_id
        - Arithmetic expression: unit_price * transaction_qty, (revenue - cost) / revenue
        """
        print(f"\n🔍 [DEBUG] ========== Starting highlight data computation ==========")
        print(f"🔍 [DEBUG] Highlight block count: {len(self.highlight_blocks)}")
        print(f"🔍 [DEBUG] Filters: {global_filters}")
        
        df = apply_filters(self.full_df, global_filters or {})
        print(f"🔍 [DEBUG] Rows after filtering: {len(df)}")
        
        items: List[Dict[str, Any]] = []
        for i, block in enumerate(self.highlight_blocks):
            print(f"\n🔍 [DEBUG] Processing highlight block {i+1}/{len(self.highlight_blocks)}: {block.get('id')}")
            
            bc = block.get("blockContent", {})
            
            # Only support new format
            expression = bc.get("expression")
            htype = bc.get("type")
            unit = bc.get("unit") or ""
            title = bc.get("title") or block.get("id")
            
            # Validate required fields
            if not expression or not htype:
                print(f"❌ [DEBUG] Missing required fields - expression: {expression}, type: {htype}")
                item = {
                    "id": block.get("id"),
                    "title": title,
                    "unit": unit,
                    "value": "N/A",
                }
                items.append(item)
                continue
            
            print(f"🔍 [DEBUG] Expression: {expression}, Type: {htype}, Unit: {unit}")
            
            value = None
            try:
                # Evaluate expression
                series = self._evaluate_expression(df, expression)
                
                if series is not None:
                    # Aggregate by type
                    value = self._aggregate_series(series, htype, expression, df)
                    print(f"🔍 [DEBUG] Computed value: {value}")
                else:
                    print(f"❌ [DEBUG] Expression evaluation failed")
                    
            except Exception as e:
                print(f"❌ [DEBUG] Computation failed: {e}")
                import traceback
                traceback.print_exc()
                value = None
            
            # Format value
            formatted_value = self._format_highlight_value(value, unit, htype)
            
            item = {
                "id": block.get("id"),
                "title": title,
                "unit": unit,
                "value": formatted_value,
            }
            items.append(item)
            print(f"🔍 [DEBUG] Highlight item: {item}")
        
        print(f"\n🔍 [DEBUG] ========== Highlight data computation completed ==========")
        return items
    
    def _evaluate_expression(self, df: pd.DataFrame, expression: str) -> Optional[pd.Series]:
        """Evaluate expression and return a Series"""
        if not expression:
            return None
        
        expression = expression.strip()
        
        # If it's a single field name
        if expression in df.columns:
            print(f"🔍 [DEBUG] Expression is a single field: {expression}")
            return df[expression]
        
        # If it's an arithmetic expression, use eval
        try:
            print(f"🔍 [DEBUG] Attempting to evaluate expression: {expression}")
            # Use DataFrame.eval to evaluate
            result = df.eval(expression, engine='python')
            
            # If result is Series, return directly
            if isinstance(result, pd.Series):
                return result
            # If result is scalar, create a constant Series
            elif isinstance(result, (int, float)):
                return pd.Series([result] * len(df))
            else:
                print(f"❌ [DEBUG] Expression evaluation result type not supported: {type(result)}")
                return None
                
        except Exception as e:
            print(f"❌ [DEBUG] Expression evaluation failed: {e}")
            return None
    
    def _aggregate_series(self, series: pd.Series, agg_type: str, expression: str, df: pd.DataFrame) -> Any:
        """Aggregate a Series"""
        if agg_type == "nunique":
            return int(series.nunique(dropna=True))
        
        elif agg_type == "count":
            return int(series.count())
        
        elif agg_type == "sum":
            return float(pd.to_numeric(series, errors="coerce").sum())
        
        elif agg_type == "mean":
            return float(pd.to_numeric(series, errors="coerce").mean())
        
        elif agg_type == "max":
            # For numeric types, return maximum value
            numeric_series = pd.to_numeric(series, errors="coerce")
            if numeric_series.notna().any():
                return float(numeric_series.max())
            # For non-numeric types, return string maximum
            return str(series.max())
        
        elif agg_type == "min":
            # For numeric types, return minimum value
            numeric_series = pd.to_numeric(series, errors="coerce")
            if numeric_series.notna().any():
                return float(numeric_series.min())
            # For non-numeric types, return string minimum
            return str(series.min())
        
        elif agg_type == "mode":
            # Return mode (most frequent value)
            # For categorical data, find the most frequent category
            value_counts = series.value_counts()
            if len(value_counts) > 0:
                return str(value_counts.index[0])
            return None
        
        else:
            print(f"❌ [DEBUG] Unsupported aggregation type: {agg_type}")
            return None
    
    def _format_highlight_value(self, value: Any, unit: str, htype: str) -> str:
        """Format highlight value as display string"""
        if value is None:
            return "N/A"
        
        # Date/time format detection and processing
        # Try to detect if it's a date or timestamp type
        if isinstance(value, (pd.Timestamp, pd.DatetimeIndex)):
            # Check if it only has date part (time is 00:00:00)
            if value.hour == 0 and value.minute == 0 and value.second == 0:
                # Only show date
                return value.strftime('%Y-%m-%d')
            else:
                # Show date and time
                return value.strftime('%Y-%m-%d %H:%M:%S')
        
        # If it's a string, try to parse as date
        if isinstance(value, str):
            try:
                dt = pd.to_datetime(value, errors='coerce')
                if pd.notna(dt):
                    # Check if it only has date part
                    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                        return dt.strftime('%Y-%m-%d')
                    else:
                        return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass  # Not a date, continue with other format processing
        
        # Currency format
        if unit == "currency" or unit == "USD":
            if isinstance(value, (int, float)):
                # If value is large, use K/M format
                if abs(value) >= 1000000:
                    return f"{value/1000000:.2f}M"
                elif abs(value) >= 1000:
                    return f"{value/1000:.2f}K"
                return f"{value:,.2f}"
            return str(value)
        
        # Percentage format
        elif unit == "%":
            if isinstance(value, (int, float)):
                return f"{value:.1f}%"
            return str(value)
        
        # Numeric format
        elif isinstance(value, float):
            # If it's an integer value, don't show decimals
            if value == int(value):
                # If value is large, use K/M format
                if abs(value) >= 1000000:
                    return f"{value/1000000:.2f}M"
                elif abs(value) >= 1000:
                    return f"{int(value)/1000:.2f}K"
                return f"{int(value):,}"
            # Otherwise keep 2 decimal places
            return f"{value:,.2f}"
        
        elif isinstance(value, int):
            # If value is large, use K/M format
            if abs(value) >= 1000000:
                return f"{value/1000000:.2f}M"
            elif abs(value) >= 1000:
                return f"{value/1000:.2f}K"
            return f"{value:,}"
        
        # Other types convert directly to string
        return str(value)

# --- App ---
engine = DashboardEngine()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=resolve_cors_origins(),
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

@app.get("/")
@app.head("/")
def index():
    # Return shell page
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

@app.get("/init")
def init_data():
    # Refresh schema
    engine.schema = load_schema()
    # Important: reprocess options and ranges, otherwise they will be overwritten by load_schema()
    engine._process_filter_ranges()
    engine._process_filter_options()
    
    print("[/init] schema loaded, blocks =", len(engine.schema.get("blocks", [])))
    layout = engine.get_layout_config()
    charts = engine.compute_charts()
    highlights = engine.compute_highlights()
    
    print("[/init] charts keys =", list(charts.keys()))
    print("[/init] highlights count =", len(highlights))
    return convert_numpy_types({
        "layout": layout,  # Contains templatePath
        "blocks": engine.schema.get("blocks", []),
        "charts": charts,
        "highlights": highlights
    })

@app.get("/data")
def get_raw_data():
    """Return raw data in JSON format for detail page table"""
    if engine.full_df.empty:
        return []
    
    # Convert to records format and limit returned rows to prevent crashes
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
    uvicorn.run(app, host="127.0.0.1", port=8007)
