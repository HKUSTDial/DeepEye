#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
可视化质量检测脚本 - 修复版
修复了 ECharts [x,y] 数据格式导致的类型误判问题
"""

import os
import sys
import re
import pandas as pd
import numpy as np
from pathlib import Path
import traceback

# 添加当前目录到路径，以便导入本地的deepeye_pack
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import deepeye_pack
from deepeye_pack.view import Chart, View
from deepeye_pack.features import Type, Features
from deepeye_pack.table_l import Table


class VisualizationDetector:
    """可视化质量检测器"""
    
    def __init__(self, csv_path, deepeye_model_path=None):
        self.csv_path = csv_path
        self.deepeye_model_path = deepeye_model_path
        self.dp = None
        self.data = None
        self.csv_columns = []
        
    def load_data(self):
        """加载CSV数据"""
        # print(f"正在加载数据: {self.csv_path}")
        try:
            self.data = pd.read_csv(self.csv_path, encoding='utf-8-sig')
            self.data.columns = [str(col).strip().replace('\ufeff', '') for col in self.data.columns]
            self.csv_columns = list(self.data.columns)
            # print(f"数据加载完成，共 {len(self.data)} 行，{len(self.data.columns)} 列")
        except Exception as e:
            print(f"数据加载失败: {e}")
            try:
                self.data = pd.read_csv(self.csv_path, encoding='utf-8')
                self.csv_columns = list(self.data.columns)
            except:
                print("无法读取数据文件")

    def initialize_deepeye(self):
        """初始化deepeye系统（轻量级版本）"""
        # print("\n正在初始化deepeye系统...")
        self.dp = deepeye_pack.deepeye('detection')
        
        # 创建虚拟 Instance 对象防止 View 初始化报错
        from deepeye_pack.instance import Instance
        virtual_instance = Instance('Simulated_Table')
        if self.data is not None:
            virtual_instance.tuple_num = len(self.data)
        else:
            virtual_instance.tuple_num = 1000
        self.dp.instance = virtual_instance
        
        # print("deepeye系统初始化完成（轻量级模式，使用手动数据注入）")
        
    def parse_visualization_code(self, code_file_path):
        """静态解析"""
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
        【核心修复】智能提取数据，支持 [x, y] 格式拆分
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
            from pyecharts.charts import Bar, Line, Scatter, Pie, HeatMap, Grid, Page
            
            local_scope = {
                'pd': pd, 'np': np, 'opts': opts,
                'Bar': Bar, 'Line': Line, 'Scatter': Scatter, 'Pie': Pie, 'HeatMap': HeatMap
            }
            
            exec(code_content, local_scope)
            
            if 'plot' in local_scope:
                chart_obj = local_scope['plot'](self.data.copy())
                
                # --- 智能数据提取 ---
                # Pyecharts 数据可能在 options 字典中，也可能在私有属性中
                # 我们优先解析 options['series']，因为那里包含了最完整的渲染数据
                
                extracted_x_from_series = []
                extracted_y_all_series = []
                
                if hasattr(chart_obj, 'options') and chart_obj.options.get('series'):
                    series_list = chart_obj.options['series']
                    
                    for s in series_list:
                        raw_data = s.get('data', [])
                        s_x = []
                        s_y = []
                        
                        for item in raw_data:
                            # 1. 提取 Value 部分
                            val = item
                            if isinstance(item, dict):
                                val = item.get('value')
                                # 饼图特殊处理：X通常在 name 中
                                if viz_info['chart_type'] == 'pie':
                                    s_x.append(item.get('name'))
                            
                            # 2. 判断 Value 是否为 [x, y] 格式
                            if isinstance(val, (list, tuple)) and len(val) >= 2:
                                # 假设 [x, y] 格式，通常 index 0 是 x (时间/类别), index 1 是 y (数值)
                                # 或者是散点图 [x, y]
                                s_x.append(val[0])
                                s_y.append(val[1])
                            else:
                                # 纯数值格式
                                s_y.append(val)
                        
                        extracted_y_all_series.append(s_y)
                        # 如果还没提取到 X 轴数据（且不是饼图），暂存这里的 X
                        if not extracted_x_from_series and s_x and viz_info['chart_type'] != 'pie':
                            extracted_x_from_series = s_x
                        # 饼图需要收集所有 name
                        elif viz_info['chart_type'] == 'pie' and s_x:
                            extracted_x_from_series = s_x

                # --- 确定最终 X 轴数据 ---
                # 优先使用 xAxis.data (显式定义的轴)
                final_x = []
                if hasattr(chart_obj, 'options') and chart_obj.options.get('xAxis'):
                    xaxis = chart_obj.options['xAxis']
                    if isinstance(xaxis, list) and len(xaxis) > 0:
                        final_x = xaxis[0].get('data', [])
                
                # 如果 xAxis 为空，使用从 series 中提取的 X (通常用于 Time Series 或 Dataset)
                if not final_x and extracted_x_from_series:
                    final_x = extracted_x_from_series
                
                # 备用：私有属性
                if not final_x and hasattr(chart_obj, '_xaxis_data'):
                     final_x = list(chart_obj._xaxis_data)

                # --- 确定最终 Y 轴数据 ---
                # 如果是单系列，展平；多系列保持列表
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
                
                print(f"  数据提取成功: X点数={len(final_x)}, 系列数={result['series_num']}")
                
            else:
                result['status'] = 'error'
                result['error'] = "找不到 plot 函数"

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
        return result

    def get_data_type(self, values):
        """根据数据列表的实际内容判断类型"""
        if not values or len(values) == 0:
            return Type.categorical
        
        # 增加采样
        sample = [v for v in values[:50] if v is not None]
        if not sample: return Type.categorical
        
        # 宽松的数值判断：尝试转换 float
        numeric_count = 0
        for v in sample:
            try:
                float(v)
                numeric_count += 1
            except (ValueError, TypeError):
                pass
        
        # 只要 >80% 是数字，就认为是 Numerical (Type 2)
        if numeric_count / len(sample) > 0.8:
            return Type.numerical
            
        # 判断时间 (Type 3)
        try:
            pd.to_datetime(sample[0])
            return Type.temporal
        except:
            pass
            
        return Type.categorical

    def validate_rules(self, viz_info, x_data, y_data):
        """基于提取后的真实数据验证规则"""
        res = {'valid': True, 'msg': []}
        
        if not x_data or not y_data:
            return {'valid': False, 'msg': ['数据为空']}
            
        # 展平 Y 数据
        y_flat = []
        if isinstance(y_data[0], list):
             for s in y_data: y_flat.extend(s)
        else:
             y_flat = y_data
             
        y_type = self.get_data_type(y_flat)
        
        # 规则 1: Y 轴必须是数值
        if viz_info['chart_type'] in ['bar', 'line', 'scatter']:
            if y_type != Type.numerical:
                # 采样打印，方便调试
                sample_str = str(y_flat[:5])
                res['valid'] = False
                res['msg'].append(f"Y轴数据类型错误: 期望数值，实际检测为 {y_type} (样本: {sample_str})")
                
        # 规则 2: 饼图不能有负数
        if viz_info['chart_type'] == 'pie':
            try:
                if any(float(v) < 0 for v in y_flat if v is not None):
                    res['valid'] = False
                    res['msg'].append("饼图数据包含负数")
            except: pass
            
        return res

    def create_view_from_visualization(self, viz_info, viz_data):
        """创建 View 对象"""
        x_raw = viz_data['x_data']
        y_raw = viz_data['y_data']
        series_num = viz_data['series_num']
        
        if not x_raw: return None
            
        temp_table = Table(self.dp.instance, False, 'Simulated_Table', '')
        
        # X 特征
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
        except: pass
            
        # Y 特征
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
            # 打印调试信息
            print(f"  特征确认 -> X类型: {x_type}, X唯一值: {fx.distinct}")
            print(f"  特征确认 -> Y类型: 数值(2), Y范围: [{fy.min:.2f}, {fy.max:.2f}]")
            print(f"  DeepEye评分结果 -> M: {view.M:.4f}, Q: {view.Q:.4f}")
            return view
        except Exception as e:
            print(f"创建View失败: {e}")
            return None

    def calculate_view_score(self, view):
        """计算评分 (RankLib)"""
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
        """主检测流程"""
        print("\n" + "="*80)
        print(f"开始检测: {os.path.basename(code_file_path)}")
        
        viz_info = self.parse_visualization_code(code_file_path)
        viz_data = self.execute_visualization_code(code_file_path, viz_info)
        
        result = {'file': viz_info['file'], 'chart_type': viz_info['chart_type'], 'status': 'fail', 'score': None, 'quality': '无法评分', 'issues': []}
        
        if viz_data['status'] == 'error':
            result['issues'].append(f"代码执行错误: {viz_data['error']}")
            return result
            
        validation = self.validate_rules(viz_info, viz_data['x_data'], viz_data['y_data'])
        if not validation['valid']:
            print(f"❌ 规则校验失败: {validation['msg']}")
            result['issues'] = validation['msg']
            result['quality'] = '违反生成规则'
            return result
            
        view = self.create_view_from_visualization(viz_info, viz_data)
        if view:
            score = self.calculate_view_score(view)
            result['status'] = 'success'
            result['score'] = score
            result['M_value'] = view.M
            result['Q_value'] = view.Q
            print(f"✅ 检测完成, 评分: {score}")
            if score is not None:
                if score > 0.7: result['quality'] = '优秀'
                elif score > 0.5: result['quality'] = '良好'
                else: result['quality'] = '一般'
        
        return result

    def generate_report(self, results):
        print("\n" + "="*80)
        print("检测报告")
        print("="*80)
        for res in results:
            print(f"文件: {res['file']}")
            print(f"质量: {res['quality']}")
            if res['score'] is not None: print(f"评分: {res['score']:.4f}")
            if res['issues']: print(f"问题: {', '.join(res['issues'])}")
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