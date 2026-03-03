#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visualization quality detection script (fixed version).
Fixes type misjudgment caused by ECharts [x,y] data format.
"""

import os
import sys
import re
import pandas as pd
import numpy as np
from pathlib import Path

# Add current directory to path for local deepeye_pack import
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import deepeye_pack
from deepeye_pack.view import Chart, View
from deepeye_pack.features import Type, Features
from deepeye_pack.table_l import Table


class VisualizationDetector:
    """Visualization quality detector."""

    def __init__(self, csv_path, deepeye_model_path=None):
        self.csv_path = csv_path
        self.deepeye_model_path = deepeye_model_path
        self.dp = None
        self.data = None
        self.csv_columns = []

    def load_data(self):
        """Load CSV data."""
        try:
            self.data = pd.read_csv(self.csv_path, encoding='utf-8-sig')
            self.data.columns = [str(col).strip().replace('\ufeff', '') for col in self.data.columns]
            self.csv_columns = list(self.data.columns)
        except Exception as e:
            print(f"Failed to load data: {e}")
            try:
                self.data = pd.read_csv(self.csv_path, encoding='utf-8')
                self.csv_columns = list(self.data.columns)
            except Exception:
                print("Unable to read data file.")

    def initialize_deepeye(self):
        """Initialize deepeye system (lightweight version)."""
        self.dp = deepeye_pack.deepeye('detection')

        # Create virtual Instance to avoid View init errors
        from deepeye_pack.instance import Instance
        virtual_instance = Instance('Simulated_Table')
        if self.data is not None:
            virtual_instance.tuple_num = len(self.data)
        else:
            virtual_instance.tuple_num = 1000
        self.dp.instance = virtual_instance
        
        # deepeye init done (lightweight mode, manual data injection)

    def parse_visualization_code(self, code_file_path):
        """Static parsing."""
        with open(code_file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        info = {
            'file': os.path.basename(code_file_path),
            'chart_type': 'bar',
            'title': ''
        }
        
        code_lower = code.lower()
        if 'bar(' in code_lower: info['chart_type'] = 'bar'
        elif 'line(' in code_lower: info['chart_type'] = 'line'
        elif 'scatter(' in code_lower: info['chart_type'] = 'scatter'
        elif 'pie(' in code_lower: info['chart_type'] = 'pie'
        elif 'heatmap(' in code_lower: info['chart_type'] = 'heatmap'
        
        title_match = re.search(r'title\s*=\s*[\'"]([^\'"]+)[\'"]', code)
        if title_match:
            info['title'] = title_match.group(1)
            
        return info

    def execute_visualization_code(self, code_file_path, viz_info):
        """
        Core fix: smart data extraction with [x, y] format splitting.
        """
        result = {
            'x_data': [],
            'y_data': [],
            'series_num': 0,
            'status': 'success',
            'error': None
        }
        
        try:
            with open(code_file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()

            import pyecharts.options as opts
            from pyecharts.charts import Bar, Line, Scatter, Pie, HeatMap
            
            local_scope = {
                'pd': pd, 'np': np, 'opts': opts,
                'Bar': Bar, 'Line': Line, 'Scatter': Scatter, 'Pie': Pie, 'HeatMap': HeatMap
            }
            
            exec(code_content, local_scope)
            
            if 'plot' in local_scope:
                chart_obj = local_scope['plot'](self.data.copy())
                
                # Smart data extraction: pyecharts data may be in options dict or private attrs
                # Prefer options['series'] for full render data
                
                extracted_x_from_series = []
                extracted_y_all_series = []
                
                if hasattr(chart_obj, 'options') and chart_obj.options.get('series'):
                    series_list = chart_obj.options['series']
                    
                    for s in series_list:
                        raw_data = s.get('data', [])
                        s_x = []
                        s_y = []
                        
                        for item in raw_data:
                            # 1. Extract value part
                            val = item
                            if isinstance(item, dict):
                                val = item.get('value')
                                # Pie: X usually in name
                                if viz_info['chart_type'] == 'pie':
                                    s_x.append(item.get('name'))

                            # 2. Check if value is [x, y] format
                            if isinstance(val, (list, tuple)) and len(val) >= 2:
                                # [x, y]: index 0 = x (time/category), index 1 = y (value), or scatter [x,y]
                                s_x.append(val[0])
                                s_y.append(val[1])
                            else:
                                s_y.append(val)

                        extracted_y_all_series.append(s_y)
                        if not extracted_x_from_series and s_x and viz_info['chart_type'] != 'pie':
                            extracted_x_from_series = s_x
                        elif viz_info['chart_type'] == 'pie' and s_x:
                            extracted_x_from_series = s_x

                # Final X: prefer xAxis.data (explicit axis)
                final_x = []
                if hasattr(chart_obj, 'options') and chart_obj.options.get('xAxis'):
                    xaxis = chart_obj.options['xAxis']
                    if isinstance(xaxis, list) and len(xaxis) > 0:
                        final_x = xaxis[0].get('data', [])

                if not final_x and extracted_x_from_series:
                    final_x = extracted_x_from_series
                if not final_x and hasattr(chart_obj, '_xaxis_data'):
                    final_x = list(chart_obj._xaxis_data)

                # Final Y: flatten if single series, keep list if multi-series
                if len(extracted_y_all_series) == 1:
                    final_y = extracted_y_all_series[0]
                    result['series_num'] = 1
                elif len(extracted_y_all_series) > 1:
                    final_y = extracted_y_all_series
                    result['series_num'] = len(extracted_y_all_series)
                else:
                    final_y = []
                    result['series_num'] = 0

                result['x_data'] = final_x
                result['y_data'] = final_y
                
                print(f"  Data extraction OK: X points={len(final_x)}, series={result['series_num']}")

            else:
                result['status'] = 'error'
                result['error'] = "plot function not found"

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
        return result

    def get_data_type(self, values):
        """Infer type from actual list content."""
        if not values or len(values) == 0:
            return Type.categorical

        sample = [v for v in values[:50] if v is not None]
        if not sample:
            return Type.categorical

        numeric_count = 0
        for v in sample:
            try:
                float(v)
                numeric_count += 1
            except (ValueError, TypeError):
                pass

        if numeric_count / len(sample) > 0.8:
            return Type.numerical

        # Check for time (Type 3)
        try:
            pd.to_datetime(sample[0])
            return Type.temporal
        except:
            pass
            
        return Type.categorical

    def validate_rules(self, viz_info, x_data, y_data):
        """Validate rules on extracted real data."""
        res = {'valid': True, 'msg': []}

        if not x_data or not y_data:
            return {'valid': False, 'msg': ['Data is empty']}

        y_flat = []
        if isinstance(y_data[0], list):
            for s in y_data:
                y_flat.extend(s)
        else:
            y_flat = y_data

        y_type = self.get_data_type(y_flat)

        # Rule 1: Y must be numerical
        if viz_info['chart_type'] in ['bar', 'line', 'scatter']:
            if y_type != Type.numerical:
                sample_str = str(y_flat[:5])
                res['valid'] = False
                res['msg'].append(f"Y-axis type error: expected numerical, got {y_type} (sample: {sample_str})")

        # Rule 2: Pie must not have negative values
        if viz_info['chart_type'] == 'pie':
            try:
                if any(float(v) < 0 for v in y_flat if v is not None):
                    res['valid'] = False
                    res['msg'].append("Pie chart data contains negative values")
            except: pass
            
        return res

    def create_view_from_visualization(self, viz_info, viz_data):
        """Create View object from visualization data."""
        x_raw = viz_data['x_data']
        y_raw = viz_data['y_data']
        series_num = viz_data['series_num']

        if not x_raw:
            return None

        temp_table = Table(self.dp.instance, False, 'Simulated_Table', '')

        # X features
        x_type = self.get_data_type(x_raw)
        fx = Features(name="Extracted_X", type=x_type, origin=0)
        try:
            fx.distinct = len(set([str(x) for x in x_raw]))
            fx.ratio = fx.distinct / len(x_raw) if len(x_raw) > 0 else 0
            if x_type == Type.numerical:
                nums = [float(x) for x in x_raw if x is not None]
                fx.min, fx.max = (min(nums), max(nums)) if nums else (0, 0)
            else:
                fx.min, fx.max = 0, fx.distinct
        except Exception:
            pass

        # Y features
        fy = Features(name="Extracted_Y", type=Type.numerical, origin=1)
        y_flat = []
        if series_num > 1:
            for s in y_raw: y_flat.extend(s)
        else:
            y_flat = y_raw
            
        try:
            valid_y = []
            for v in y_flat:
                try: valid_y.append(float(v))
                except: pass
            
            fy.distinct = len(set(valid_y))
            fy.ratio = fy.distinct / len(valid_y) if len(valid_y) > 0 else 0
            if valid_y:
                fy.min, fy.max = min(valid_y), max(valid_y)
                if fy.min == fy.max: fy.max += 0.00001
            else:
                fy.min, fy.max = 0, 0
        except: pass

        temp_table.features = [fx, fy]
        temp_table.tuple_num = len(x_raw)
        
        if series_num > 1:
            X_view = [x_raw for _ in range(series_num)]
            Y_view = y_raw
        else:
            X_view = [x_raw]
            Y_view = [y_raw]
            
        chart_map = {'bar': Chart.bar, 'line': Chart.line, 'scatter': Chart.scatter, 'pie': Chart.pie, 'heatmap': Chart.scatter}
        target_chart = chart_map.get(viz_info['chart_type'], Chart.bar)
        
        try:
            view = View(temp_table, 0, 1, -1, series_num, X_view, Y_view, target_chart)
            print(f"  Features -> X type: {x_type}, X distinct: {fx.distinct}")
            print(f"  Features -> Y type: numerical(2), Y range: [{fy.min:.2f}, {fy.max:.2f}]")
            print(f"  DeepEye score -> M: {view.M:.4f}, Q: {view.Q:.4f}")
            return view
        except Exception as e:
            print(f"Failed to create View: {e}")
            return None

    def calculate_view_score(self, view):
        """Compute score (RankLib)."""
        if not view or not self.dp: return None
        try:
            import subprocess, tempfile
            ltr_string = view.output_score()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ltr', delete=False, encoding='utf-8') as f:
                f.write(ltr_string + '\n')
                ltr_path = f.name
            with tempfile.NamedTemporaryFile(mode='r', suffix='.score', delete=False, encoding='utf-8') as f:
                score_path = f.name
            
            jar_path = os.path.join(script_dir, 'deepeye_pack', 'jars', 'RankLib.jar')
            model_path = os.path.join(script_dir, 'deepeye_pack', 'jars', 'rank.model')
            
            if not os.path.exists(jar_path): return 0.5
            
            cmd = f'java -jar "{jar_path}" -load "{model_path}" -rank "{ltr_path}" -score "{score_path}"'
            subprocess.run(cmd, shell=True, capture_output=True)
            
            score = 0
            with open(score_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines and len(lines[0].split('\t')) >= 3:
                    score = float(lines[0].split('\t')[2])
            
            try: os.unlink(ltr_path); os.unlink(score_path)
            except: pass
            
            return score
        except: return None

    def detect_visualization(self, code_file_path):
        """Main detection flow."""
        print("\n" + "="*80)
        print(f"Starting detection: {os.path.basename(code_file_path)}")

        viz_info = self.parse_visualization_code(code_file_path)
        viz_data = self.execute_visualization_code(code_file_path, viz_info)

        result = {'file': viz_info['file'], 'chart_type': viz_info['chart_type'], 'status': 'fail', 'score': None, 'quality': 'Not scored', 'issues': []}

        if viz_data['status'] == 'error':
            result['issues'].append(f"Code execution error: {viz_data['error']}")
            return result

        validation = self.validate_rules(viz_info, viz_data['x_data'], viz_data['y_data'])
        if not validation['valid']:
            print(f"❌ Rule validation failed: {validation['msg']}")
            result['issues'] = validation['msg']
            result['quality'] = 'Rule violation'
            return result

        view = self.create_view_from_visualization(viz_info, viz_data)
        if view:
            score = self.calculate_view_score(view)
            result['status'] = 'success'
            result['score'] = score
            result['M_value'] = view.M
            result['Q_value'] = view.Q
            print(f"✅ Detection done, score: {score}")
            if score is not None:
                if score > 0.7:
                    result['quality'] = 'Excellent'
                elif score > 0.5:
                    result['quality'] = 'Good'
                else:
                    result['quality'] = 'Fair'

        return result

    def generate_report(self, results):
        print("\n" + "="*80)
        print("Detection report")
        print("="*80)
        for res in results:
            print(f"File: {res['file']}")
            print(f"Quality: {res['quality']}")
            if res['score'] is not None:
                print(f"Score: {res['score']:.4f}")
            if res['issues']:
                print(f"Issues: {', '.join(res['issues'])}")
            print("-" * 40)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'Coffee Shop Sales.csv')
    test_vis_dir = os.path.join(script_dir, 'test_vis')
    
    if not os.path.exists(csv_path): return
    viz_files = [os.path.join(test_vis_dir, f) for f in os.listdir(test_vis_dir) if f.endswith('.py')]
    if not viz_files: return
        
    detector = VisualizationDetector(csv_path)
    detector.load_data()
    detector.initialize_deepeye()
    
    results = []
    for f in viz_files:
        results.append(detector.detect_visualization(f))
    detector.generate_report(results)

if __name__ == '__main__':
    main()