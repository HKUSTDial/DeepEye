import copy
import json
import re,os,traceback
from typing import Dict, List, Any, Optional
from storyteller.algorithm.utils.DatasetContextGenerator import DatasetContextGenerator  # 引入数据集解析器
from storyteller.algorithm.mcts_node import *
from storyteller.llm_call.openai_llm import call_openai
from storyteller.llm_call.prompt_factory import get_prompt
from typing import List, Dict, Any
import pandas as pd
from enum import Enum
import base64
from PIL import Image
import io,requests
from openai import OpenAI
from .utils.html2image import convert_html_file_to_image
from storyteller.algorithm.mcts_node import ReportGenerationState
from llmx import llm, TextGenerator
from lida.components.manager import Manager
from storyteller.algorithm.utils.universalsc import run_universal_self_consistency  # 导入universalsc功能
from storyteller.algorithm.utils.unified_framework import unified_generation_framework  # 导入统一框架
import time
from tqdm import tqdm
import glob
import random




class DataStorytellingAction:
    def __init__(self, action_id: str, description: str):
        self.action_id = action_id
        self.description = description# 默认的下一个状态
        
        # 添加 MCTS 统计属性
        #self.Q = 0.0  # 累积奖励
        #self.N = 0    # 访问次数
  

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = self
            child_node.depth = node.depth + 1
        
            raise NotImplementedError
        
    
class Query2Chapters(DataStorytellingAction):
    def __init__(self):
        super().__init__("A1", "定义章节结构") 
        self.use_unified_framework = True  # 是否使用统一框架

    def generate_chapter_prompt(self, node, **kwargs):
        """生成章节提示词"""
        query = node.report.clarified_query if node.report.clarified_query else node.report.original_query
        data_context = node.report.data_context
        
        # 使用预设的提示模板
        prompt_args = {
            "QUERY": query,
            "DATA_CONTEXT": data_context
        }
        
        return get_prompt("Query2Chapters_test", prompt_args)
    
    def apply_chapters(self, node, action, cluster, **kwargs):
        """将章节应用到子节点"""
        try:
            cluster_id = cluster.get("cluster_id", "未知")
            chapters = cluster.get("chapters", [])
            
            if not chapters:
                print(f"⚠️ 聚类 {cluster_id} 没有章节内容，跳过")
                return None
            
            print(f"📘 为聚类 {cluster_id} 应用章节方案")
            print(f"   章节结构: {chapters}")
            
            # 创建子节点
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = action
            child_node.depth = node.depth + 1
            
            # 清空现有章节
            child_node.report.chapters = []
            
            # 添加章节
            for title in chapters:
                child_node.report.add_chapter(Chapter(title=title))
            
            # 设置节点状态
            child_node.node_type = ReportGenerationState.a1
            
            print(f"✅ 成功添加聚类 {cluster_id} 的章节方案")
            return [child_node]
            
        except Exception as e:
            print(f"❌ 应用章节时出错: {str(e)}")
            traceback.print_exc()
            return None

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """
        根据用户查询和数据上下文，使用统一框架生成多样化章节结构
        """
        if self.use_unified_framework:
            return unified_generation_framework(
                node=node,
                action=self,
                llm_kwargs=llm_kwargs,
                action_type="chapters",
                prompt_generator=self.generate_chapter_prompt,
                node_applier=self.apply_chapters,
                n=4
            )
        else:
            # 使用原有方法的实现（保留以便兼容）
            # 使用 clarified_query（如果有）或原始查询
            query = node.report.clarified_query if node.report.clarified_query else node.report.original_query
            data_context = node.report.data_context
            print(data_context)
            # 运行USC流程获取聚类结果
            clusters = run_universal_self_consistency(query, data_context, llm_kwargs, n=4)
            print(f"✅ 完成章节聚类，得到 {len(clusters)} 个聚类")
            
            # 从每个聚类中创建子节点
            nodes = []
            for cluster in clusters:
                cluster_id = cluster.get("cluster_id", "未知")
                chapters = cluster.get("chapters", [])
                
                # 跳过没有章节的聚类
                if not chapters:
                    print(f"⚠️ 聚类 {cluster_id} 没有章节内容，跳过")
                    continue
        
                print(f"📘 为聚类 {cluster_id} 创建子节点")
                print(f"   章节结构: {chapters}")
                
                # 创建子节点
                child_node = copy.deepcopy(node)
                child_node.parent_node = node
                child_node.parent_action = self
                child_node.depth = node.depth + 1
                
                # 清空现有章节
                child_node.report.chapters = []
                
                # 添加章节
                for title in chapters:
                        child_node.report.add_chapter(Chapter(title=title))
                
                # 设置节点状态
                child_node.node_type = ReportGenerationState.a1
                
                # 添加到节点列表
                nodes.append(child_node)
                print(f"✅ 成功添加聚类 {cluster_id} 的章节方案")
        
        return nodes



class Chapters2Tasks(DataStorytellingAction):
    def __init__(self):
        super().__init__("A2", "根据章节方案划分章节任务方案")
        self.use_unified_framework = True  # 是否使用统一框架

    def generate_tasks_prompt(self, node, **kwargs):
        """生成任务提示词"""
        # 获取数据集信息
        data_context = node.report.data_context
        query = node.report.clarified_query if node.report.clarified_query else node.report.original_query
        
        # 构建章节列表
        chapters_list = []
        for i, chapter in enumerate(node.report.chapters):
            # 安全获取标题
            if isinstance(chapter, dict):
                # 如果章节是字典类型
                if 'title' in chapter:
                    # 如果章节字典有'title'键
                    if isinstance(chapter['title'], dict):
                        # 如果'title'键对应的值也是字典
                        title_text = chapter['title'].get('title', '') or chapter['title'].get('text', f"章节{i+1}")
                    else:
                        # 如果'title'键对应的值是字符串
                        title_text = chapter['title']
                else:
                    # 如果章节字典没有'title'键，使用默认值
                    title_text = f"章节{i+1}"
            else:
                # 如果章节是对象类型
                title_attr = getattr(chapter, 'title', None)
                if isinstance(title_attr, dict):
                    # 如果title属性是字典
                    title_text = title_attr.get('title', '') or title_attr.get('text', f"章节{i+1}")
                else:
                    # 如果title属性是字符串或其他类型
                    title_text = title_attr if title_attr else f"章节{i+1}"
            
            chapters_list.append(title_text)
        
        # 生成 LLM 提示词
        prompt_args = {
            "QUERY": query,
            "DATA_CONTEXT": data_context,
            "CHAPTERS": json.dumps(chapters_list, ensure_ascii=False)
        }
        
        return get_prompt("Chapters2Tasks_test", prompt_args)
    
    def apply_tasks(self, node, action, cluster, **kwargs):
        """将任务应用到子节点"""
        try:
            # 创建子节点
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = action
            child_node.depth = node.depth + 1
            
            # 获取聚类中的章节任务
            cluster_id = cluster.get("cluster_id", "未知")
            chapters_info = cluster.get("chapters", [])
            
            if not chapters_info:
                print(f"⚠️ 聚类 {cluster_id} 没有任务内容，跳过")
                return None
            
            print(f"📋 为聚类 {cluster_id} 应用任务方案")
            
            # 创建章节标题到索引的映射
            chapter_title_to_index = {}
            for i, chapter in enumerate(child_node.report.chapters):
                # 安全获取标题文本
                if isinstance(chapter, dict):
                    # 如果章节是字典类型
                    if 'title' in chapter:
                        # 如果章节字典有'title'键
                        if isinstance(chapter['title'], dict):
                            # 如果'title'键对应的值也是字典
                            title_text = chapter['title'].get('title', '') or chapter['title'].get('text', f"章节{i+1}")
                        else:
                            # 如果'title'键对应的值是字符串
                            title_text = chapter['title']
                    else:
                        # 如果章节字典没有'title'键，使用默认值
                        title_text = f"章节{i+1}"
                else:
                    # 如果章节是对象类型
                    title_attr = getattr(chapter, 'title', None)
                    if isinstance(title_attr, dict):
                        # 如果title属性是字典
                        title_text = title_attr.get('title', '') or title_attr.get('text', f"章节{i+1}")
                    else:
                        # 如果title属性是字符串或其他类型
                        title_text = title_attr if title_attr else f"章节{i+1}"
                
                # 确保title_text是字符串类型
                if not isinstance(title_text, str):
                    title_text = str(title_text)
                    
                # 存储小写标题文本到索引的映射
                chapter_title_to_index[title_text.lower()] = i
            
            # 跟踪哪些章节已经分配了任务
            chapters_with_tasks = set()
            
            # 处理每个章节
            for chapter_info in chapters_info:
                raw_title = chapter_info.get("title", "")
                
                # 安全获取标题文本
                if isinstance(raw_title, dict):
                    # 如果是字典，尝试提取文本
                    title_text = raw_title.get('title', '') or raw_title.get('text', '')
                else:
                    # 如果不是字典，直接使用
                    title_text = raw_title
                
                # 确保title_text是字符串类型
                if not isinstance(title_text, str):
                    title_text = str(title_text) if title_text is not None else ""
                    
                tasks = chapter_info.get("tasks", [])
                
                # 查找匹配的章节
                chapter_idx = -1
                title_lower = title_text.lower()  # 现在可以安全调用lower()
                
                # 精确匹配
                if title_lower in chapter_title_to_index:
                    chapter_idx = chapter_title_to_index[title_lower]
                else:
                    # 模糊匹配
                    for i, chapter in enumerate(child_node.report.chapters):
                        # 安全获取章节标题
                        if isinstance(chapter, dict):
                            if 'title' in chapter:
                                if isinstance(chapter['title'], dict):
                                    search_title = chapter['title'].get('title', '') or chapter['title'].get('text', f"章节{i+1}")
                                else:
                                    search_title = chapter['title']
                            else:
                                search_title = f"章节{i+1}"
                        else:
                            title_attr = getattr(chapter, 'title', None)
                            if isinstance(title_attr, dict):
                                search_title = title_attr.get('title', '') or title_attr.get('text', f"章节{i+1}")
                            else:
                                search_title = title_attr if title_attr else f"章节{i+1}"
                        
                        # 确保search_title是字符串类型
                        if not isinstance(search_title, str):
                            search_title = str(search_title)
                            
                        search_title_lower = search_title.lower()
                        if title_lower in search_title_lower or search_title_lower in title_lower:
                            chapter_idx = i
                            break
                
                if chapter_idx >= 0 and chapter_idx < len(child_node.report.chapters):
                    chapter = child_node.report.chapters[chapter_idx]
                    
                    # 清空现有任务列表
                    chapter.visualization_tasks = []
                    
                    # 添加任务
                    for task in tasks:
                        task_id = task.get("task_id", "")
                        description = task.get("task_description", "")
                        chart_type = task.get("chart_type", ["Bar Chart"])
                        
                        # 创建任务对象
                        task_obj = {
                            "task_id": task_id,
                            "task_description": description,
                            "chart_type": chart_type,
                            "status": "pending",  # 添加状态字段
                            "visualization_success": False  # 添加可视化成功标志
                        }
                        
                        # 添加到章节的任务列表
                        if not hasattr(chapter, 'visualization_tasks'):
                            chapter.visualization_tasks = []
                        chapter.visualization_tasks.append(task_obj)
                        
                        # 打印任务状态
                        print(f"   - 任务ID: '{task_id}'")
                        print(f"   - 任务描述: '{description}'")
                        print(f"   - 图表类型: {chart_type}")
                        print(f"   - 状态: {task_obj.get('status')}")
                    
                    # 记录已分配任务的章节
                    chapters_with_tasks.add(chapter_idx)
                    
                    # 打印调试信息
                    print(f"✅ 为章节 {chapter_idx+1} ({chapter.title}) 生成了 {len(tasks)} 个可视化任务")
                else:
                    print(f"❌ 找不到匹配的章节: {title_text}")
            
            # 检查所有章节是否都有任务
            all_chapters_have_tasks = True
            for i, chapter in enumerate(child_node.report.chapters):
                if i not in chapters_with_tasks:
                    print(f"⚠️ 章节 {i+1} ({chapter.title}) 没有任务")
                    all_chapters_have_tasks = False
            
            # 只有当所有章节都有任务时，才返回这个节点
            if all_chapters_have_tasks:
                # 设置节点状态
                child_node.node_type = ReportGenerationState.a2
                print(f"✅ 成功应用聚类 {cluster_id} 的任务方案")
                return [child_node]
            else:
                print(f"⚠️ 聚类 {cluster_id} 的任务方案不完整，跳过")
                return None
                
        except Exception as e:
            print(f"❌ 应用任务时出错: {str(e)}")
            traceback.print_exc()
            return None

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """为每个章节生成多种任务方案"""
        # 只使用统一框架的实现，移除原有的方法
        return unified_generation_framework(
            node=node,
            action=self,
            llm_kwargs=llm_kwargs,
            action_type="tasks",
            prompt_generator=self.generate_tasks_prompt,
            node_applier=self.apply_tasks,
            n=3  # 生成3个不同的任务方案变体
        )



class Tasks2Charts(DataStorytellingAction):
    def __init__(self):
        super().__init__("A3", "生成可视化")
        # 保存配置参数而不是实际的对象实例
        self.similarity_threshold = 0.90  # 相似度阈值
        self.use_similarity_check = True  # 标记是否应该使用相似度检查
        self.use_chart2vega = True  # 标记是否应该使用chart2vega

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = self
        child_node.depth = node.depth + 1

        try:
            # 初始化图表相似度检测工具（推迟到需要使用时才创建）
            similarity_tool = None
            if self.use_similarity_check:
                try:
                    from storyteller.algorithm.utils.ChartSimilarity import ChartSimilarity
                    similarity_tool = ChartSimilarity()
                    print("✅ 图表相似度检测工具初始化成功")
                except Exception as e:
                    print(f"⚠️ 图表相似度检测工具初始化失败: {str(e)}")
                    similarity_tool = None
            
            # 初始化chart2vega（推迟到需要使用时才创建）
            chart2vega_module = None
            if self.use_chart2vega:
                try:
                    from storyteller.algorithm.utils import chart2vega
                    chart2vega_module = chart2vega
                    print("✅ chart2vega工具初始化成功")
                except Exception as e:
                    print(f"⚠️ chart2vega工具初始化失败: {str(e)}")
                    chart2vega_module = None
            
            # 递增迭代号 - 确保每次创建新节点时迭代号加1
            # child_node.report.current_iteration += 1
            current_iteration = child_node.report.current_iteration
            print(f"✅ 当前迭代号: {current_iteration}")
            
            # 确定当前迭代号和保存路径
            iteration_dir = os.path.join("storyteller", "output", "iterations", f"iteration_{current_iteration}")
            os.makedirs(iteration_dir, exist_ok=True)
            charts_dir = os.path.join(iteration_dir, "charts")
            os.makedirs(charts_dir, exist_ok=True)
           
            # 新增：创建Vega-Lite配置目录
            vegalite_dir = os.path.join(iteration_dir, "vegalite_configs")
            os.makedirs(vegalite_dir, exist_ok=True)
            
            # 获取数据集
            dataset_path = node.report.dataset_path
            df = pd.read_csv(dataset_path)

            # 遍历所有章节
            for chapter_idx, chapter in enumerate(child_node.report.chapters):
                print(f"\n📊 正在处理第 {chapter_idx + 1} 章...")
                print(f"章节标题: {getattr(chapter, 'title', f'章节{chapter_idx+1}')}")
                print(f"章节的可视化任务数量: {len(getattr(chapter, 'visualization_tasks', []))}")
                
                # 初始化章节图表列表（如果不存在）
                if not hasattr(chapter, 'charts'):
                    chapter.charts = []
                
                # 收集所有章节的图表用于相似度检查
                all_charts = []
                for ch in child_node.report.chapters:
                    if hasattr(ch, 'charts'):
                        all_charts.extend(ch.charts)
                
                # 遍历章节中的所有可视化任务
                for task in chapter.visualization_tasks:
                    print(f"\n🔍 处理任务:")
                    print(f"- 任务ID: {task.get('task_id', '')}")
                    print(f"- 任务描述: {task.get('task_description', '')}")
                    print(f"- 图表类型: {task.get('chart_type', ['Bar Chart'])[0]}")
                    
                    task_id = task.get('task_id', "")
                    description = task.get('task_description')
                    chart_type = task.get('chart_type', ["Bar Chart"])[0]

                    # 使用任务ID作为文件名，如果为空则使用任务描述
                    file_name = task_id if task_id else description
                    if not file_name:
                        file_name = f"chart_{chapter_idx}_{len(chapter.charts)}"
                    # 清理文件名中的非法字符
                    file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
                    chart_path = os.path.join(charts_dir, f"{file_name}.png")

                    # 创建文本生成器和管理器（在局部作用域内创建，避免序列化问题）
                    from lida.datamodel import Goal, Summary
                    from lida.components.manager import Manager
                    
                    # 创建 Goal 对象
                    goal = Goal(question=task_id, visualization=description, chart_type=chart_type)
                    
                    # 创建 Summary 对象
                    # 读取数据摘要 JSON 文件
                    data_summary = {}
                    json_path = os.path.join("storyteller", "dataset", "data_context.json")
                    print(f"尝试读取数据摘要 JSON: {json_path}")
                    
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data_summary = json.load(f)
                        print("✓ 成功读取数据摘要 JSON")
                    except Exception as e:
                        print(f"✗ 读取数据摘要 JSON 失败: {str(e)}")
                        # 如果无法读取 JSON 文件，使用默认值
                        data_summary = {
                            "name": node.report.original_query,
                            "dataset_description": node.report.data_context,
                            "fields_info": {col: {"dtype": str(dtype)} for col, dtype in zip(df.columns, df.dtypes)}
                        }

                    # 创建 Summary 对象，使用从 JSON 文件中提取的信息
                    summary = Summary(
                        name=data_summary.get("name", "购物数据分析"),
                        file_name=dataset_path,
                        dataset_description=str(data_summary.get("dataset_description", "购物数据集")),
                        field_names=list(data_summary.get("fields_info", {}).keys()) if "fields_info" in data_summary else df.columns.tolist(),
                        fields=[info.get("dtype", "unknown") for info in data_summary.get("fields_info", {}).values()] if "fields_info" in data_summary else [str(dtype) for dtype in df.dtypes.tolist()]
                    )
                    
                    # 创建自定义的文本生成器
                    text_gen = llm(
                        provider="openai", 
                        model="gpt-4-32k"
                    )

                    # 创建 LIDA 管理器
                    manager = Manager(text_gen=text_gen)

                    # 生成可视化
                    print(f"正在为任务 '{description}' 生成可视化图表...")
                    visualization = manager.visualize(summary, goal, library="matplotlib")

                    # 处理可视化结果
                    if isinstance(visualization, list) and len(visualization) > 0:
                        visualization = visualization[0]

                    if hasattr(visualization, 'status') and visualization.status:
                        print("✓ 成功生成可视化结果")

                        # 保存图表
                        if hasattr(visualization, 'savefig'):
                            visualization.savefig(chart_path)
                            print(f"✓ 图表已保存到: {chart_path}")
                            
                            # 生成Vega-Lite配置
                            try:
                                # 使用chart2vega提取Vega-Lite配置
                                chart_config = self._extract_chart_config(visualization, task_id, description, df, llm_kwargs, chart2vega_module)
                                
                                # 保存Vega-Lite配置
                                if "vegalite_config" in chart_config and chart_config["vegalite_config"]:
                                    vegalite_config = chart_config["vegalite_config"]
                                    vegalite_file_name = f"{file_name}.json"
                                    vegalite_path = os.path.join(vegalite_dir, vegalite_file_name)
                                    
                                    with open(vegalite_path, "w", encoding="utf-8") as f:
                                        json.dump(vegalite_config, f, ensure_ascii=False, indent=2)
                                    print(f"✓ Vega-Lite图表配置已保存到: {vegalite_path}")
                                    
                                    # 生成Vega-Lite HTML可视化
                                    try:
                                        if chart2vega_module:
                                            # 创建HTML输出目录
                                            html_dir = os.path.join(iteration_dir, "vegalite_html")
                                            os.makedirs(html_dir, exist_ok=True)
                                            
                                            # 生成HTML文件
                                            html_path = os.path.join(html_dir, f"{file_name}.html")
                                            
                                            # 创建HTML查看器
                                            chart2vega_module.create_html_viewer(vegalite_config, html_path)
                                            print(f"✓ Vega-Lite HTML可视化已保存到: {html_path}")
                                    except Exception as e:
                                        print(f"⚠️ 生成Vega-Lite HTML时出错: {str(e)}")
                                        import traceback
                                        traceback.print_exc()
                            except Exception as e:
                                print(f"⚠️ 生成Vega-Lite配置时出错: {str(e)}")
                                import traceback
                                traceback.print_exc()
                                vegalite_path = None
                                
                            # 额外保存图表数据为CSV，以便后续分析
                            try:
                                csv_dir = os.path.join(os.path.dirname(charts_dir), "chart_data")
                                os.makedirs(csv_dir, exist_ok=True)
                                csv_file_name = f"{file_name}.csv"
                                csv_path = os.path.join(csv_dir, csv_file_name)
                                
                                # 尝试从可视化对象中提取实际使用的数据
                                if hasattr(visualization, '_data') and isinstance(visualization._data, pd.DataFrame):
                                    visualization._data.to_csv(csv_path, index=False)
                                    print(f"✓ 图表数据已保存到: {csv_path}")
                                elif hasattr(visualization, 'data') and isinstance(visualization.data, pd.DataFrame):
                                    visualization.data.to_csv(csv_path, index=False)
                                    print(f"✓ 图表数据已保存到: {csv_path}")
                            except Exception as e:
                                print(f"⚠️ 保存图表数据 CSV 时出错: {str(e)}")
                                traceback.print_exc()
                            
                            # 检查图表相似度
                            if similarity_tool and all_charts:
                                # 收集已有图表的路径列表
                                existing_chart_paths = []
                                for chart in all_charts:
                                    if hasattr(chart, 'url') and chart.url:
                                        existing_chart_paths.append(chart.url)
                                
                                if existing_chart_paths:
                                    # 使用batch_compare计算相似度
                                    is_too_similar, max_similarity, similar_chart_path, all_similarities = similarity_tool.batch_compare(
                                        chart_path, existing_chart_paths, self.similarity_threshold
                                    )
                                    
                                    if is_too_similar:
                                        # 找到最相似的图表对象
                                        similar_chart = None
                                        for chart in all_charts:
                                            if hasattr(chart, 'url') and chart.url == similar_chart_path:
                                                similar_chart = chart
                                                break
                                        
                                        similar_task_id = getattr(similar_chart, 'task_id', '未知任务') if similar_chart else '未知任务'
                                        
                                        print(f"⚠️ 警告: 生成的图表与现有图表相似度过高 ({max_similarity:.4f})")
                                        print(f"   - 相似图表: {similar_task_id}")
                                        
                                        # 创建samechart文件夹
                                        samechart_dir = os.path.join(charts_dir, "samechart")
                                        os.makedirs(samechart_dir, exist_ok=True)
                                        
                                        # 移动相似的图表到samechart文件夹
                                        samechart_path = os.path.join(samechart_dir, f"{file_name}.png")
                                        
                                        try:
                                            import shutil
                                            # 移动图表到samechart目录(而非复制)
                                            shutil.move(chart_path, samechart_path)
                                            print(f"✓ 相似图表已移动到: {samechart_path}")
                                            
                                            # 在控制台输出相似度信息
                                            print(f"📊 图表相似度信息:")
                                            print(f"   - 相似度值: {max_similarity:.4f}")
                                            print(f"   - 相似图表任务: {similar_task_id}")
                                            print(f"   - 当前任务: {task_id}")
                                            
                                            # 标记任务为已完成但图表被跳过
                                            for vis_task in chapter.visualization_tasks:
                                                if vis_task.get('task_id') == task_id:
                                                    vis_task['visualization_success'] = False
                                                    vis_task['skipped_due_to_similarity'] = True
                                                    print(f"⚠️ 任务 '{task_id}' 因图表相似度过高而被跳过")
                                                    break
                                                    
                                            # 跳过当前任务的后续处理
                                            continue
                                            
                                        except Exception as e:
                                            print(f"⚠️ 移动相似图表时出错: {str(e)}")
                                            # 如果移动失败，继续使用原始路径

                        # 创建图表对象
                        print(f"\n📊 创建图表对象:")
                        print(f"- 图表路径: {chart_path}")
                        print(f"- 图表类型: {chart_type}")
                        print(f"- 任务ID: {task_id}")
                        
                        chart = Chart(
                            url=chart_path,
                            caption="",  # 使用空字符串作为初始说明
                            chart_type=chart_type,
                            task_id=task_id  # task_id 实际上就是任务描述
                        )
                        
                        # 存储可视化代码，以便后续修改
                        if hasattr(visualization, 'code'):
                            chart.code = visualization.code
                        
                        # 添加图表到章节
                        if not hasattr(chapter, 'charts'):
                            chapter.charts = []
                            print("初始化章节的图表列表")
                        
                        chapter.charts.append(chart)
                        # 更新所有图表列表
                        all_charts.append(chart)
                        print(f"✓ 图表已添加到章节，当前章节图表数量: {len(chapter.charts)}")
                        
                        # 如果处理成功，也标记为已完成
                        for vis_task in chapter.visualization_tasks:
                            if vis_task.get('task_id') == task_id:
                                vis_task['visualization_success'] = True
                                print(f"✅ 任务 '{task_id}' 已成功完成")
                                break
                    else:
                        print("✗ 生成可视化图表失败")
                        # 即使失败也标记为完成，避免无限循环
                        for vis_task in chapter.visualization_tasks:
                            if vis_task.get('task_id') == task_id:
                                # 确保初始化 visualization_success 字段
                                vis_task['visualization_success'] = False
                                
                                # 新增：保存失败图表的代码（如果有）
                                if hasattr(visualization, 'code'):
                                    # 创建失败图表目录（如果不存在）
                                    failed_code_dir = os.path.join(charts_dir, "failed_code")
                                    os.makedirs(failed_code_dir, exist_ok=True)
                                    
                                    # 保存失败图表代码到文件
                                    code_file_path = os.path.join(failed_code_dir, f"{file_name}_failed.py")
                                    try:
                                        with open(code_file_path, 'w', encoding='utf-8') as f:
                                            f.write(visualization.code)
                                        print(f"✅ 已保存失败图表代码到: {code_file_path}")
                                        
                                        # 在任务中记录代码路径
                                        vis_task['failed_code_path'] = code_file_path
                                        
                                        # 新增: 即使图表生成失败，也创建图表对象并添加到章节中
                                        # 使用临时的占位图片路径或者特殊标记表示这是失败的图表
                                        placeholder_chart = Chart(
                                            url=code_file_path,  # 使用代码文件作为URL（这只是一个标识符）
                                            caption="",
                                            chart_type=chart_type,
                                            task_id=task_id
                                        )
                                        
                                        # 添加代码和失败标记
                                        placeholder_chart.code = visualization.code
                                        placeholder_chart.generation_failed = True  # 添加失败标记
                                        
                                        # 添加图表到章节
                                        if not hasattr(chapter, 'charts'):
                                            chapter.charts = []
                                        
                                        chapter.charts.append(placeholder_chart)
                                        all_charts.append(placeholder_chart)
                                        print(f"✅ 已添加失败图表占位符到章节，以便后续修复")
                                        
                                    except Exception as e:
                                        print(f"❌ 保存失败图表代码或创建占位图表时出错: {str(e)}")
                                
                                print(f"⚠️ 任务 '{description}' 虽然失败但已标记为已完成，避免无限循环")
                                break
            # 设置正确的状态
            child_node.node_type = ReportGenerationState.a3
            return [child_node]

        except Exception as e:
            print(f"❌ 处理节点时出错: {str(e)}")
            traceback.print_exc()
            # 确保即使异常也设置正确的状态
            child_node.node_type = ReportGenerationState.a3
            return [child_node]


    def _extract_chart_config(self, visualization, task_id, description, df, llm_kwargs=None, chart2vega_module=None):
        """从可视化代码中提取图表配置，只使用chart2vega转换为Vega-Lite
        
        参数:
            visualization: 包含可视化代码的对象
            task_id: 任务ID
            description: 任务描述
            df: 数据DataFrame
            llm_kwargs: LLM调用参数
            chart2vega_module: chart2vega模块的实例
            
        返回:
            包含vegalite_config的配置字典
        """
        # 初始化空配置
        result_config = {
            "title": description or "Chart",
            "vegalite_config": None
        }
        
        try:
            # 确保有可视化代码
            if not hasattr(visualization, 'code'):
                raise ValueError("可视化对象没有代码属性")
            
            code = visualization.code
            print("\n📋 分析可视化代码:")
            print("-" * 50)
            print(code)
            print("-" * 50)
            
            # 使用chart2vega直接将Python代码转换为Vega-Lite配置
            if chart2vega_module:
                try:
                    print("\n🚀 使用chart2vega工具生成Vega-Lite配置...")
                    
                    # 确保llm_kwargs参数正确传递
                    if llm_kwargs is None:
                        llm_kwargs = {}
                    else:
                        # 创建副本以避免修改原始对象
                        llm_kwargs = llm_kwargs.copy()
                    
                    # 添加或确保设置了合适的模型
                    if not llm_kwargs.get("model"):
                        llm_kwargs["model"] = "gpt-4-turbo"
                    
                    # 确保API调用参数正确
                    # 检查是否有base_url，如果没有设置，尝试从环境变量获取
                    if not llm_kwargs.get("base_url"):
                        env_base_url = os.environ.get("OPENAI_BASE_URL")
                        if env_base_url:
                            llm_kwargs["base_url"] = env_base_url
                    
                    # 检查是否有api_key，如果没有则尝试从环境变量获取
                    if not llm_kwargs.get("api_key"):
                        env_api_key = os.environ.get("OPENAI_API_KEY")
                        if env_api_key:
                            llm_kwargs["api_key"] = env_api_key
                    
                    # 添加重试逻辑
                    max_retries = 2
                    vegalite_config = None
                    
                    for retry in range(max_retries):
                        try:
                            if retry > 0:
                                print(f"⚠️ 第 {retry+1} 次尝试调用chart2vega...")
                                
                            vegalite_config = chart2vega_module.convert_python_to_vegalite(code, llm_kwargs=llm_kwargs)
                            
                            if vegalite_config:
                                print("✅ 成功使用LLM直接转换代码为Vega-Lite配置")
                                break
                            else:
                                print(f"⚠️ 第 {retry+1} 次尝试失败")
                        except Exception as e:
                            print(f"⚠️ 第 {retry+1} 次尝试时出错: {str(e)}")
                            
                            if retry < max_retries - 1:
                                print("⚠️ 稍后重试...")
                                time.sleep(1)  # 短暂延迟再重试
                    
                    # 检查是否成功获取了Vega-Lite配置
                    if vegalite_config:
                        # 确保设置标题
                        if isinstance(vegalite_config, dict) and (not vegalite_config.get("title") or vegalite_config["title"] == "Chart"):
                            vegalite_config["title"] = description
                            
                        # 保存vegalite_config到结果
                        result_config["vegalite_config"] = vegalite_config
                        
                        # 输出配置信息
                        print(f"\n✓ 成功生成Vega-Lite配置:")
                        if isinstance(vegalite_config.get("mark"), dict):
                            print(f"- 图表类型: {vegalite_config.get('mark', {}).get('type', '')}")
                        else:
                            print(f"- 图表类型: {vegalite_config.get('mark', '')}")
                        print(f"- 图表标题: {vegalite_config.get('title', '')}")
                        
                        if 'encoding' in vegalite_config:
                            encoding = vegalite_config.get('encoding', {})
                            print(f"- X轴字段: {encoding.get('x', {}).get('field', '')}")
                            print(f"- Y轴字段: {encoding.get('y', {}).get('field', '')}")
                    else:
                        print("⚠️ LLM转换Vega-Lite配置失败")
                        
                except Exception as e:
                    print(f"⚠️ 使用chart2vega时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
        except Exception as e:
            print(f"⚠️ 提取图表配置时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return result_config

class ReviseVis(DataStorytellingAction):
    def __init__(self):
        super().__init__("A4", "对所有可视化图表进行Revise判断")
    
    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """修改可视化图表"""
        # 创建子节点
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = self
        child_node.depth = node.depth + 1
        
        try:
            # 遍历所有章节
            for chapter_idx, chapter in enumerate(child_node.report.chapters):
                # 检查章节是否有可视化任务
                if not hasattr(chapter, 'visualization_tasks') or not chapter.visualization_tasks:
                    print(f"⚠️ 章节 {chapter_idx + 1} 没有可视化任务，跳过")
                    continue
                    
                for task in chapter.visualization_tasks:
                    # 检查任务是否是生成成功的或者因相似度跳过的
                    if task.get('visualization_success', False) == True:
                        continue
                        
                    # 检查任务是否因相似度高而被跳过的，如果是则不需要修复
                    if task.get('skipped_due_to_similarity', False) == True:
                        print(f"⚠️ 任务 '{task.get('task_id', '')}' 因相似度过高而被跳过，不需要修复")
                        continue
                        
                    task_id = task.get('task_id', "")
                    description = task.get('task_description', "")
                    
                    print(f"正在修改任务 '{task_id}' 的图表...")
            
                    selected_chart = None
                    print(f"\n🔍 在章节中查找图表:")
                    print(f"- 章节标题: {getattr(chapter, 'title', f'章节{chapter_idx+1}')}")
                    print(f"- 章节中的图表数量: {len(getattr(chapter, 'charts', []))}")
                    
                    for c in chapter.charts:
                        print(f"- 检查图表: task_id={getattr(c, 'task_id', 'None')}")
                        if hasattr(c, 'task_id') and c.task_id == task_id:
                            selected_chart = c
                            print(f"✓ 找到匹配的图表")
                            break
                    
                    # 如果没有找到匹配的图表，跳过此任务
                    if not selected_chart:
                        print(f"⚠️ 找不到与任务 '{task_id}' 匹配的图表，跳过")
                        continue
                
                    try:
                        # 获取数据文件路径
                        dataset_path = node.report.dataset_path
                        
                        # 读取数据
                        df = pd.read_csv(dataset_path)
                        
                        # 在方法内创建LIDA管理器和文本生成器（局部变量）
                        from lida.components.manager import Manager
                        from lida.datamodel import Summary
                        
                        # 创建自定义的文本生成器（作为局部变量）
                        text_gen = llm(provider="openai", model="gpt-4o")
                        manager = Manager(text_gen=text_gen)
                        
                        # 读取数据摘要 JSON 文件
                        data_summary = {}
                        json_path = os.path.join("storyteller", "dataset", "data_context.json")
                        print(f"尝试读取数据摘要 JSON: {json_path}")
                        
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                data_summary = json.load(f)
                            print("✓ 成功读取数据摘要 JSON")
                        except Exception as e:
                            print(f"✗ 读取数据摘要 JSON 失败: {str(e)}")
                            # 如果无法读取 JSON 文件，使用默认值
                            data_summary = {
                                "name": node.report.original_query,
                                "dataset_description": node.report.data_context,
                                "fields_info": {col: {"dtype": str(dtype)} for col, dtype in zip(df.columns, df.dtypes)}
                            }
                        
                        # 创建 Summary 对象，直接从 JSON 文件中提取必要参数
                        summary = Summary(
                            name=data_summary.get("name", "数据分析"),
                            file_name=dataset_path,  # 使用原始数据文件路径
                            dataset_description=str(data_summary.get("dataset_description", "购物数据集")),
                            field_names=list(data_summary.get("fields_info", {}).keys()) if "fields_info" in data_summary else df.columns.tolist(),
                            fields=[info.get("dtype", "unknown") for info in data_summary.get("fields_info", {}).values()] if "fields_info" in data_summary else [str(dtype) for dtype in df.dtypes.tolist()]
                        )
                        
                        # 检查任务描述和图表代码，决定是否需要生成表格而不是图表
                        chart_generation_failed = getattr(selected_chart, 'generation_failed', False)
                        
                        # 判断是否需要将图表转换为表格
                        # 如果图表生成失败，或有其他标记指示应该使用表格
                        if chart_generation_failed:
                            print(f"📊 检测到图表生成失败，尝试生成表格形式展示数据")
                            edit_instruction = f"""
                            请将这个失败的可视化代码转换为生成表格的代码。原始任务描述是: '{description}'
                            
                            请遵循以下指导:
                            1. 仔细分析原始任务描述，确保表格能够展示与原任务相同的数据关系和对比
                                - 分析任务想要展示的变量关系（例如，若要比较两组数据，表格应包含这两组的对比）
                                - 明确任务中的X轴和Y轴变量，并确保这些变量在表格中有明确的列
                                - 保留任务中要求的聚合方式（平均值、总和、计数等）
                             
                            2. 数据处理部分:
                                - 保留原代码中的关键数据筛选、分组和聚合操作
                                - 如果任务需要比较多个类别或组，确保所有类别都在表格中
                             
                            3. 表格设计：
                                - 为表格创建清晰的行和列标签，与原任务的X轴/Y轴命名保持一致
                                - 限制表格中的数据行数（最多显示15行关键数据）
                                - 对数值进行适当的格式化（例如保留2位小数）
                                - 如果原任务是比较不同类别，可以添加百分比差异列
                             
                            4. 表格样式:
                                - 使用matplotlib的plt.table()创建表格
                                - 调整表格颜色和样式，提高可读性和美观度
                                - 根据数据类型设置合适的单元格颜色（例如使用颜色深浅表示数值大小）
                             
                            5. 元数据:
                                - 使用原始任务的标题，并在标题中注明这是表格形式
                             
                            主要目标是确保表格形式能够完整展现原始可视化任务想要传达的数据洞察和关系。
                            最终输出应该是能够直接保存为PNG的matplotlib图像。
                            """
                        else:
                            # 如果不是生成表格，使用普通的图表修改指令
                            edit_instruction = "修改图表错误，比如修改为更合适的图表类型，让图表更加美观，清晰"
                        
                        # 使用 LIDA 的 edit 功能修改图表/生成表格
                        print(f"正在为任务 '{description}' 生成{'表格' if chart_generation_failed else '图表'}...")
                        edited_visualization = manager.edit(
                            code=selected_chart.code,
                            summary=summary,
                            instructions=edit_instruction,
                            library="matplotlib"
                        )
                        
                        # 处理编辑后的可视化结果
                        if edited_visualization is None:
                            print(f"✗ 生成{'表格' if chart_generation_failed else '图表'}失败: 返回结果为None")
                        elif isinstance(edited_visualization, list) and len(edited_visualization) > 0:
                            edited_visualization = edited_visualization[0]
                            print(f"✓ 使用第一个编辑结果进行处理")
                        
                        # 检查是否为有效的编辑结果
                        if hasattr(edited_visualization, 'status') and edited_visualization.status:
                            print(f"✓ 成功生成{'表格' if chart_generation_failed else '图表'}")
                            
                            # 找到当前图表所在的迭代目录
                            original_chart_path = selected_chart.url
                            chart_dir = os.path.dirname(original_chart_path)
                            
                            # 将修改后的图表保存到同一目录下
                            suffix = "_table" if chart_generation_failed else "_edited"
                            edited_chart_name = f"{task_id}{suffix}.png"
                            edited_chart_path = os.path.join(chart_dir, edited_chart_name)
                            
                            # 保存修改后的图表或表格
                            if hasattr(edited_visualization, 'savefig'):
                                edited_visualization.savefig(edited_chart_path)
                                print(f"✓ {'表格' if chart_generation_failed else '图表'}已保存到: {edited_chart_path}")

                                # 生成Vega-Lite配置 (仅对图表执行，表格跳过)
                                if not chart_generation_failed:
                                    try:
                                        # 直接使用提取配置的逻辑，而不是实例化Tasks2Charts
                                        chart_config = self._extract_chart_config(edited_visualization, task_id, description, df, llm_kwargs)
                                        
                                        # 保存Vega-Lite配置
                                        if "vegalite_config" in chart_config and chart_config["vegalite_config"]:
                                            vegalite_config = chart_config["vegalite_config"]
                                            
                                            # 获取Vega-Lite配置目录
                                            vegalite_dir = os.path.join(os.path.dirname(chart_dir), "vegalite_configs")
                                            os.makedirs(vegalite_dir, exist_ok=True)
                                            
                                            # 保存Vega-Lite配置
                                            vegalite_file_name = f"{task_id}_edited.json"
                                            vegalite_path = os.path.join(vegalite_dir, vegalite_file_name)
                                            
                                            with open(vegalite_path, "w", encoding="utf-8") as f:
                                                json.dump(vegalite_config, f, ensure_ascii=False, indent=2)
                                            print(f"✓ Vega-Lite图表配置已保存到: {vegalite_path}")
                                            
                                            # 生成HTML查看器
                                            try:
                                                # 导入chart2vega（局部导入）
                                                from storyteller.algorithm.utils import chart2vega
                                                
                                                # 创建HTML输出目录
                                                html_dir = os.path.join(os.path.dirname(chart_dir), "vegalite_html")
                                                os.makedirs(html_dir, exist_ok=True)
                                                
                                                # 生成HTML文件
                                                html_path = os.path.join(html_dir, f"{task_id}_edited.html")
                                                
                                                # 创建HTML查看器
                                                chart2vega.create_html_viewer(vegalite_config, html_path)
                                                print(f"✓ Vega-Lite HTML可视化已保存到: {html_path}")
                                            except Exception as e:
                                                print(f"⚠️ 生成HTML查看器时出错: {str(e)}")
                                                traceback.print_exc()
                                    except Exception as e:
                                        print(f"⚠️ 生成Vega-Lite配置时出错: {str(e)}")
                                        import traceback
                                        traceback.print_exc()
                                
                                # 额外保存图表数据为CSV，以便后续分析
                                try:
                                    csv_dir = os.path.join(os.path.dirname(chart_dir), "chart_data")
                                    os.makedirs(csv_dir, exist_ok=True)
                                    csv_file_name = f"{task_id}{suffix}.csv"
                                    csv_path = os.path.join(csv_dir, csv_file_name)
                                    
                                    # 尝试从可视化对象中提取实际使用的数据
                                    if hasattr(edited_visualization, '_data') and isinstance(edited_visualization._data, pd.DataFrame):
                                        edited_visualization._data.to_csv(csv_path, index=False)
                                        print(f"✓ {'表格' if chart_generation_failed else '图表'}数据已保存到: {csv_path}")
                                    elif hasattr(edited_visualization, 'data') and isinstance(edited_visualization.data, pd.DataFrame):
                                        edited_visualization.data.to_csv(csv_path, index=False)
                                        print(f"✓ {'表格' if chart_generation_failed else '图表'}数据已保存到: {csv_path}")
                                except Exception as e:
                                    print(f"⚠️ 保存{'表格' if chart_generation_failed else '图表'}数据 CSV 时出错: {str(e)}")
                                    traceback.print_exc()

                            # 创建新的图表对象
                            from storyteller.algorithm.mcts_node import Chart
                            edited_chart = Chart(
                                url=edited_chart_path,
                                caption="",  # 使用空字符串作为初始说明
                                chart_type="table" if chart_generation_failed else selected_chart.chart_type,
                                task_id=task_id  # 使用原始任务ID/描述
                            )
                            edited_chart.needs_caption = True  # 设置需要生成说明文字的标志
                            edited_chart.is_table = chart_generation_failed  # 标记是否为表格
                            
                            # 更新章节中的图表
                            for i, c in enumerate(chapter.charts):
                                if hasattr(c, 'task_id') and c.task_id == task_id:
                                    chapter.charts[i] = edited_chart
                                    # 更新任务状态为成功
                                    for vis_task in chapter.visualization_tasks:
                                        if vis_task.get('task_id') == task_id:
                                            vis_task['visualization_success'] = True
                                            vis_task['converted_to_table'] = chart_generation_failed
                                            print(f"✅ 更新任务 '{task_id}' 状态为成功生成{'表格' if chart_generation_failed else '图表'}")
                                            break
                                    break
                        else:
                            error_msg = edited_visualization.error if hasattr(edited_visualization, 'error') else "未知错误"
                            print(f"✗ 生成{'表格' if chart_generation_failed else '图表'}失败: {error_msg}")
                    except Exception as e:
                        print(f"✗ 为任务 '{task_id}' 生成{'表格' if getattr(selected_chart, 'generation_failed', False) else '图表'}时发生错误: {str(e)}")
                        import traceback
                        traceback.print_exc()
            
            # 设置正确的状态
            child_node.node_type = ReportGenerationState.a4
            return [child_node]
                
        except Exception as e:
            print(f"❌ 处理节点时出错: {str(e)}")
            # 如果没有找到任务，返回空列表
            print("❌ 没有找到待处理的任务")
            # 确保即使异常也设置正确的状态
            child_node.node_type = ReportGenerationState.a4
            return [child_node]
   
    def _extract_chart_config(self, visualization, task_id, description, df, llm_kwargs=None):
        """从可视化代码中提取图表配置，转换为Vega-Lite
        
        参数:
            visualization: 包含可视化代码的对象
            task_id: 任务ID
            description: 任务描述
            df: 数据DataFrame
            llm_kwargs: LLM调用参数
            
        返回:
            包含vegalite_config的配置字典
        """
        # 初始化空配置
        result_config = {
            "title": description or "Chart",
            "vegalite_config": None
        }
        
        try:
            # 确保有可视化代码
            if not hasattr(visualization, 'code'):
                raise ValueError("可视化对象没有代码属性")
            
            code = visualization.code
            print("\n📋 分析可视化代码:")
            print("-" * 50)
            print(code)
            print("-" * 50)
            
            # 导入chart2vega（局部导入）
            try:
                from storyteller.algorithm.utils import chart2vega
                print("\n🚀 使用chart2vega工具生成Vega-Lite配置...")
                
                # 确保llm_kwargs参数正确传递
                if llm_kwargs is None:
                    llm_kwargs = {}
                else:
                    # 创建副本以避免修改原始对象
                    llm_kwargs = llm_kwargs.copy()
                
                # 添加或确保设置了合适的模型
                if not llm_kwargs.get("model"):
                    llm_kwargs["model"] = "gpt-4-turbo"
                
                # 检查是否有base_url，如果没有设置，尝试从环境变量获取
                if not llm_kwargs.get("base_url"):
                    env_base_url = os.environ.get("OPENAI_BASE_URL")
                    if env_base_url:
                        llm_kwargs["base_url"] = env_base_url
                
                # 检查是否有api_key，如果没有则尝试从环境变量获取
                if not llm_kwargs.get("api_key"):
                    env_api_key = os.environ.get("OPENAI_API_KEY")
                    if env_api_key:
                        llm_kwargs["api_key"] = env_api_key
                
                # 添加重试逻辑
                max_retries = 2
                vegalite_config = None
                
                for retry in range(max_retries):
                    try:
                        if retry > 0:
                            print(f"⚠️ 第 {retry+1} 次尝试调用chart2vega...")
                            
                        vegalite_config = chart2vega.convert_python_to_vegalite(code, llm_kwargs=llm_kwargs)
                        
                        if vegalite_config:
                            print("✅ 成功使用LLM直接转换代码为Vega-Lite配置")
                            break
                        else:
                            print(f"⚠️ 第 {retry+1} 次尝试失败")
                        
                    except Exception as e:
                        print(f"⚠️ 第 {retry+1} 次尝试时出错: {str(e)}")
                        
                        if retry < max_retries - 1:
                            print("⚠️ 稍后重试...")
                            time.sleep(1)  # 短暂延迟再重试
                
                # 检查是否成功获取了Vega-Lite配置
                if vegalite_config:
                    # 确保设置标题
                    if isinstance(vegalite_config, dict) and (not vegalite_config.get("title") or vegalite_config["title"] == "Chart"):
                        vegalite_config["title"] = description
                        
                    # 保存vegalite_config到结果
                    result_config["vegalite_config"] = vegalite_config
                    
                    # 输出配置信息
                    print(f"\n✓ 成功生成Vega-Lite配置:")
                    if isinstance(vegalite_config.get("mark"), dict):
                        print(f"- 图表类型: {vegalite_config.get('mark', {}).get('type', '')}")
                    else:
                        print(f"- 图表类型: {vegalite_config.get('mark', '')}")
                    print(f"- 图表标题: {vegalite_config.get('title', '')}")
                    
                    if 'encoding' in vegalite_config:
                        encoding = vegalite_config.get('encoding', {})
                        print(f"- X轴字段: {encoding.get('x', {}).get('field', '')}")
                        print(f"- Y轴字段: {encoding.get('y', {}).get('field', '')}")
                else:
                    print("⚠️ LLM转换Vega-Lite配置失败")
                    
                        
            except Exception as e:
                print(f"⚠️ 使用chart2vega时出错: {str(e)}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"⚠️ 提取图表配置时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return result_config

class Charts2Captions(DataStorytellingAction):
    def __init__(self):
        super().__init__("A5", "根据所有可视化图表生成所有对应Caption")
    
    def _filter_successful_charts(self, chapter):
        """筛选出章节中成功生成的图表
        
        参数:
            chapter: 章节对象
            
        返回:
            successful_charts: 成功生成的图表列表
        """
        successful_charts = []
        
        # 检查章节是否有图表
        if not hasattr(chapter, 'charts') or not chapter.charts:
            return successful_charts
            
        # 遍历章节中的所有图表
        for chart in chapter.charts:
            # 获取图表任务ID
            chart_task_id = getattr(chart, 'task_id', '')
            task_success = False
            
            # 检查图表是否已有caption
            has_caption = hasattr(chart, 'caption') and chart.caption
            
            # 从可视化任务中查找与图表关联的任务状态
            if hasattr(chapter, 'visualization_tasks'):
                for task in chapter.visualization_tasks:
                    if task.get('task_id') == chart_task_id:
                        task_success = task.get('visualization_success', False)
                        break
            
            # 只添加成功生成且没有caption的图表
            if task_success and not has_caption:
                successful_charts.append(chart)
                print(f"✓ 图表 {chart_task_id} 符合处理条件")
            elif not task_success:
                print(f"⚠️ 跳过图表 {chart_task_id}，因为它的生成状态为失败")
            elif has_caption:
                print(f"ℹ️ 跳过图表 {chart_task_id}，因为它已有caption")
                
        return successful_charts
    
    def _get_image_base64(self, image_path: str) -> str:
        """将图片转换为 base64 编码"""
        try:
            with Image.open(image_path) as img:
                # 将图片转换为 bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format=img.format)
                img_byte_arr = img_byte_arr.getvalue()
                # 转换为 base64
                return base64.b64encode(img_byte_arr).decode('utf-8')
        except Exception as e:
            print(f"❌ 图片转换失败: {str(e)}")
            return None

    def call_vision_api(self, prompt, image_base64_list, **kwargs):
        """统一处理视觉API调用，支持单个或多个图像，自动处理限流问题"""
        import os
        import requests
        import json
        import time
        import random
        
        # 获取环境变量
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        
        # 日志记录
        print(f"🔄 环境变量状态: OPENAI_BASE_URL={base_url}, OPENAI_API_KEY={'已设置' if api_key else '未设置'}")
        
        # 构造完整的API URL
        if base_url.endswith('/chat/completions'):
            url = base_url  # 已经是完整URL
        elif base_url.endswith('/v1'):
            url = f"{base_url}/chat/completions"  # 添加chat/completions端点
        else:
            # 确保URL以斜杠结尾
            if not base_url.endswith('/'):
                base_url += '/'
            url = f"{base_url}v1/chat/completions"  # 添加v1/chat/completions路径
            
        print(f"🔄 使用API URL: {url}")
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }
        
        # 准备图像内容
        image_contents = []
        for img_base64 in (image_base64_list if isinstance(image_base64_list, list) else [image_base64_list]):
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}"
                }
            })
        
        # 构建消息
        messages = [
            {"role": "system", "content": "You are a data visualization expert."},
            {"role": "user", "content": [{"type": "text", "text": prompt}, *image_contents]}
        ]
        
        # 设置API调用参数
        model = "gpt-4-turbo"  # 使用固定模型，而不是从kwargs中获取
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 4096)
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        print(f"🔄 调用视觉API，模型: {model}, 温度: {temperature}")
        
        # 配置重试参数
        max_retries = kwargs.get("max_retries", 5)  # 增加最大重试次数
        base_delay = kwargs.get("base_delay", 3)   # 初始等待时间（秒）
        max_delay = kwargs.get("max_delay", 60)    # 最大等待时间（秒）
        timeout = kwargs.get("timeout", 60)        # 请求超时时间
        
        # 实现指数退避重试
        for retry in range(max_retries):
            try:
                # 创建本地会话对象，而不是使用全局会话
                session = requests.Session()
                
                # 发送请求
                response = session.post(url, headers=headers, json=data, timeout=timeout)
                response_json = response.json()
                
                # 关闭会话
                session.close()
                
                # 处理响应
                if 'choices' in response_json and response_json['choices']:
                    return response_json['choices'][0]['message']['content'].strip()
                
                # 检查是否是限流错误 (429)
                if 'error' in response_json:
                    error = response_json['error']
                    error_code = error.get('code', '')
                    error_type = error.get('type', '')
                    error_message = error.get('message', '')
                    
                    # 如果是限流错误，应用指数退避策略
                    if error_code == '429' or '429' in error_message or 'rate limit' in error_message.lower():
                        # 打印限流错误
                        print(f"❌ API返回错误或无响应: {response_json}")
                        
                        # 解析等待时间（如果API提供）
                        wait_time = None
                        import re
                        time_matches = re.findall(r'retry after (\d+)', error_message.lower())
                        if time_matches and len(time_matches) > 0:
                            try:
                                wait_time = int(time_matches[0])
                            except ValueError:
                                pass
                        
                        # 如果没有明确指定等待时间，使用指数退避策略
                        if wait_time is None:
                            # 计算退避时间，加入随机抖动以避免同步请求
                            delay = min(max_delay, base_delay * (2 ** retry)) + random.uniform(0, 2)
                        else:
                            # 使用API返回的等待时间加2秒缓冲
                            delay = wait_time + 2
                            
                        if retry < max_retries - 1:  # 最后一次重试不需要等待
                            print(f"⚠️ API返回限流错误，将在 {delay:.1f} 秒后重试... (尝试 {retry+1}/{max_retries})")
                            time.sleep(delay)
                            continue
                    else:
                        print(f"❌ API返回错误: {error_type} - {error_message}")
                else:
                    print(f"❌ API返回未知格式响应: {response_json}")
                
            except Exception as e:
                # 处理网络异常等其他错误
                print(f"❌ API调用失败: {str(e)}")
                
                # 只有在非最后一次重试时才等待
                if retry < max_retries - 1:
                    # 计算退避时间
                    delay = min(max_delay, base_delay * (2 ** retry)) + random.uniform(0, 2)
                    print(f"⚠️ 将在 {delay:.1f} 秒后重试... (尝试 {retry+1}/{max_retries})")
                    time.sleep(delay)
                    continue
                
                traceback.print_exc()
        
        print(f"❌ 已达到最大重试次数 ({max_retries})，API调用失败")
        return None
    
    def generate_chapter_caption_schemes(self, node, chapter, chapter_idx, charts, num_schemes=3, llm_kwargs=None):
        """为单个章节的所有图表生成多套说明方案，具有重试机制"""
        # 过滤出成功生成的图表
        successful_charts = self._filter_successful_charts(chapter)
        
        # 如果章节内没有成功生成的图表，直接返回空
        if not successful_charts:
            print(f"⚠️ 章节 {chapter_idx+1} 没有成功生成的图表需要处理")
            return []
        
        print(f"\n🔄 为章节 {chapter_idx+1} 生成 {num_schemes} 套说明方案")
        print(f"章节标题: {getattr(chapter, 'title', f'章节{chapter_idx+1}')}")
        print(f"需处理的图表数量: {len(successful_charts)} (从 {len(charts)} 总图表中筛选)")
        
        # 准备图表信息文本和图像
        charts_info = ""
        chart_images = []
        
        for i, chart in enumerate(successful_charts):
            charts_info += f"\n图表{i}:"
            charts_info += f"\n- 类型: {chart.chart_type}"
            charts_info += f"\n- 任务: {chart.task_id}"
            
            # 获取图表图像数据
            image_base64 = self._get_image_base64(chart.url)
            if image_base64:
                chart_images.append(image_base64)
            else:
                print(f"❌ 无法获取图表 {i} 的图像数据")
        
        if not chart_images:
            print("❌ 没有可用的图表图像数据")
            return []
            
        # 实现重试机制
        max_retries = 3
        for retry in range(max_retries):
            try:
                # 使用模板文件生成提示词
                prompt_args = {
                    "QUERY": node.original_query,
                    "CHAPTER_TITLE": getattr(chapter, 'title', f'章节{chapter_idx+1}'),
                    "DATA_CONTEXT": node.report.data_context,
                    "NUM_SCHEMES": str(num_schemes),
                    "CHARTS_INFO": charts_info,
                    "RETRY_NUM": str(retry + 1)  # 告诉模型这是第几次尝试
                }
                
                # 增强提示词
                prompt = get_prompt("chapter_captions", prompt_args)
                if retry > 0:
                    # 对于重试，增加更明确的JSON格式要求
                    prompt += f"\n\n【重要】这是第{retry+1}次尝试，请务必确保返回有效的JSON格式。您的响应必须包含完整的JSON结构，格式如下：\n"
                    prompt += """
{
  "schemes": [
    {
      "scheme_id": 1,
      "captions": [
        {
          "chart_idx": 0,
          "caption": "图表0的说明文字"
        },
        {
          "chart_idx": 1,
          "caption": "图表1的说明文字"
        }
      ]
    },
    {
      "scheme_id": 2,
      "captions": [
        {
          "chart_idx": 0,
          "caption": "另一种图表0的说明文字"
        },
        {
          "chart_idx": 1,
          "caption": "另一种图表1的说明文字"
        }
      ]
    }
  ]
}
"""
                
                # 调用视觉API
                print(f"🔄 正在调用API生成章节 {chapter_idx+1} 的说明方案... (尝试 {retry+1}/{max_retries})")
                # 降低温度，提高确定性
                api_kwargs = llm_kwargs.copy() if llm_kwargs else {}
                api_kwargs['temperature'] = max(0.1, 0.7 - retry * 0.2)  # 逐渐降低温度
                response_text = self.call_vision_api(prompt, chart_images, **api_kwargs)
                
                if not response_text:
                    print(f"❌ 章节 {chapter_idx+1} 没有收到有效响应 (尝试 {retry+1}/{max_retries})")
                    if retry < max_retries - 1:
                        print("将在1秒后重试...")
                        import time
                        time.sleep(1)
                        continue
                    else:
                        return []
                
                # 解析JSON响应
                print(f"🔍 LLM响应片段: {response_text[:200]}...")
                result = self.extract_json_from_text(response_text)
                
                if result and "schemes" in result:
                    schemes = result["schemes"]
                    print(f"✅ 成功为章节 {chapter_idx+1} 生成 {len(schemes)} 套说明方案")
                    return schemes
                
                print(f"❌ 无法解析章节 {chapter_idx+1} 的图表说明方案 (尝试 {retry+1}/{max_retries})")
                if retry < max_retries - 1:
                    print("将在1秒后重试...")
                    import time
                    time.sleep(5)
                else:
                    print("已达到最大重试次数，无法生成有效的说明方案")
                    return []
                    
            except Exception as e:
                print(f"❌ 生成章节图表说明方案出错: {str(e)} (尝试 {retry+1}/{max_retries})")
                traceback.print_exc()
                if retry < max_retries - 1:
                    print("将在1秒后重试...")
                    import time
                    time.sleep(5)
                else:
                    print("已达到最大重试次数，无法生成有效的说明方案")
                    return []
        
        # 所有重试都失败
        return []
    
    def extract_json_from_text(self, text):
        """从LLM响应中提取JSON，具有更强的容错能力"""
        try:
            # 先尝试查找JSON块
            match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if match:
                json_str = match.group(1)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON块解析失败: {str(e)}，尝试修复并重新解析")
                    # 尝试修复常见的JSON格式问题
                    json_str = self._fix_json(json_str)
                    return json.loads(json_str)
            
            # 如果没有JSON块，尝试寻找整个文本中的JSON对象
            match = re.search(r'(\{[\s\S]*\})', text)
            if match:
                json_str = match.group(1)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON对象解析失败: {str(e)}，尝试修复并重新解析")
                    # 尝试修复常见的JSON格式问题
                    json_str = self._fix_json(json_str)
                    return json.loads(json_str)
            
            # 如果上述方法都失败，尝试从文本中提取schemes部分
            schemes_match = re.search(r'"schemes"\s*:\s*(\[[\s\S]*?\])', text)
            if schemes_match:
                schemes_str = schemes_match.group(1)
                print(f"✓ 提取到schemes数组，尝试构建完整JSON")
                try:
                    # 构建一个新的JSON
                    new_json = f'{{"schemes": {schemes_str}}}'
                    return json.loads(new_json)
                except json.JSONDecodeError as e:
                    print(f"⚠️ 提取的schemes解析失败: {str(e)}")
            
            # 如果没有找到完整结构，尝试手动提取每个caption
            captions = re.findall(r'(?:chart_idx|图表索引)["\s:]+(\d+)[\s"]*(?:,|\})[\s\S]*?(?:caption|说明文字)["\s:]+([^"]*?)[",$}]', text)
            if captions:
                print(f"✓ 手动提取到 {len(captions)} 个caption条目")
                manual_scheme = {
                    "scheme_id": 1,
                    "captions": []
                }
                
                for chart_idx_str, caption in captions:
                    try:
                        chart_idx = int(chart_idx_str)
                        manual_scheme["captions"].append({
                            "chart_idx": chart_idx,
                            "caption": caption.strip()
                        })
                    except ValueError:
                        pass
                
                if manual_scheme["captions"]:
                    return {"schemes": [manual_scheme]}
            
            return None
        except Exception as e:
            print(f"❌ JSON解析错误: {str(e)}")
            traceback.print_exc()
            return None
    
    def _fix_json(self, json_str):
        """修复常见的JSON格式问题"""
        # 修复缺少逗号的问题
        json_str = re.sub(r'}\s*{', '},{', json_str)
        json_str = re.sub(r']\s*\[', '],[', json_str)
        
        # 修复多余的逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # 确保属性名有引号
        json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)
        
        # 修复转义问题
        json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
        
        return json_str
    
    def generate_combined_nodes(self, node, all_chapter_schemes, all_chapter_groups=None, max_nodes=3):
        """生成子节点组合 - 使用简单策略：全部章节使用第n套方案"""
        if not all_chapter_schemes:
            return []
        
        children_nodes = []
        
        # 计算每个章节最多有几套方案
        max_schemes = max([len(chapter_data["schemes"]) for chapter_data in all_chapter_schemes], default=0)
        
        # 策略：所有章节使用同一套方案编号（全部用方案1，全部用方案2...）
        for scheme_idx in range(min(max_schemes, max_nodes)):
            try:
                # 在 try 块中进行深拷贝操作，捕获可能的序列化错误
                child_node = copy.deepcopy(node)
                child_node.parent_node = node
                child_node.parent_action = self
                child_node.depth = node.depth + 1
                child_node.node_type = ReportGenerationState.a5  # 正确设置节点状态为a5
                print(f"📌 创建方案{scheme_idx+1}的子节点，设置状态为: {child_node.node_type}")
                
                caption_applied = False  # 跟踪是否应用了任何说明
                
                # 对每个章节应用相同编号的方案
                for chapter_data in all_chapter_schemes:
                    chapter_idx = chapter_data["chapter_idx"]
                    schemes = chapter_data["schemes"]
                    
                    # 如果此章节有对应编号的方案
                    if 0 <= scheme_idx < len(schemes):
                        scheme = schemes[scheme_idx]
                        
                        # 安全地获取章节
                        if 0 <= chapter_idx < len(child_node.report.chapters):
                            chapter = child_node.report.chapters[chapter_idx]
                            
                            print(f"🔄 为子节点{scheme_idx+1}应用章节{chapter_idx+1}的方案{scheme.get('scheme_id', scheme_idx+1)}")
                            
                            # 如果有分组信息，也添加到章节对象中
                            if all_chapter_groups and chapter_idx in all_chapter_groups:
                                # 将分组信息存储到章节对象
                                chapter.chart_groups = all_chapter_groups[chapter_idx]
                                print(f"✅ 为章节{chapter_idx+1}添加{len(chapter.chart_groups)}个图表组信息")
                            
                            # 应用此方案中的所有图表说明
                            for caption_info in scheme.get("captions", []):
                                chart_idx = caption_info.get("chart_idx")
                                caption = caption_info.get("caption", "")
                                
                                if hasattr(chapter, 'charts') and 0 <= chart_idx < len(chapter.charts):
                                    chart = chapter.charts[chart_idx]
                                    chart.caption = caption
                                    chart.needs_caption = False
                                    caption_applied = True
                                    
                                    # 更新任务状态
                                    if hasattr(chapter, 'visualization_tasks'):
                                        for task in chapter.visualization_tasks:
                                            if task.get('task_id') == chart.task_id:
                                                task['status'] = 'completed'
                                                task['caption_generated'] = True
                                                break
                
                if caption_applied:  # 只有当应用了说明时才添加节点
                    child_node.caption_strategy = f"统一方案{scheme_idx+1}"
                    # 再次确认状态设置正确
                    child_node.node_type = ReportGenerationState.a5
                    children_nodes.append(child_node)
                    print(f"✅ 成功创建子节点 {scheme_idx+1}，使用统一方案 {scheme_idx+1}，最终状态为: {child_node.node_type}")
                else:
                    print(f"⚠️ 子节点 {scheme_idx+1} 未应用任何caption，跳过此节点")

            except Exception as e:
                print(f"❌ 创建方案 {scheme_idx+1} 的子节点时出错: {str(e)}")
                traceback.print_exc()
                continue
        
        # 最后一次确认所有子节点状态正确
        for i, child in enumerate(children_nodes):
            if child.node_type != ReportGenerationState.a5:
                print(f"⚠️ 检测到子节点 {i+1} 状态不正确，正在修复...")
                child.node_type = ReportGenerationState.a5
        
        if children_nodes:
            print(f"📊 生成了 {len(children_nodes)} 个子节点，所有节点状态设置为: {ReportGenerationState.a5}")
        
        return children_nodes

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """为图表生成说明文字，使用新的评估和分组方法为组图表生成关联性caption"""
        print("\n🔄 开始处理图表说明生成任务 (A5)...")
        
        # 收集需要处理的章节及其图表
        chapters_with_charts = []
        for chapter_idx, chapter in enumerate(node.report.chapters):
            # 筛选出成功生成且需要caption的图表
            successful_charts = self._filter_successful_charts(chapter)
            
            if successful_charts:
                chapters_with_charts.append({
                    "chapter_idx": chapter_idx,
                    "chapter": chapter,
                    "charts": successful_charts
                })
                print(f"✅ 章节 {chapter_idx+1} 有 {len(successful_charts)} 个图表需要生成说明")
        
        if not chapters_with_charts:
            # 没有需要处理的图表，返回原节点
            print("没有需要生成说明的图表，返回原节点")
            child_node = copy.deepcopy(node)  # 创建一个副本
            child_node.parent_node = node
            child_node.parent_action = self
            child_node.depth = node.depth + 1
            child_node.node_type = ReportGenerationState.a5  # 确保正确设置状态为a5
            print(f"⚠️ 没有图表需要处理，设置节点状态为: {child_node.node_type}")
            return [child_node]
        
        # 对每个章节生成说明
        all_chapter_schemes = []
        all_chapter_groups = {}  # 存储每个章节的图表分组信息
        
        for chapter_info in chapters_with_charts:
            chapter_idx = chapter_info["chapter_idx"]
            chapter = chapter_info["chapter"]
            charts = chapter_info["charts"]
            
            # 尝试新的批量评估和分组方式
            try:
                print(f"\n🔄 使用新方法处理章节 {chapter_idx+1}")
                
                # 批量评估和分组图表
                evaluation_result = self.evaluate_and_group_charts(node, chapter, charts)
                
                if evaluation_result and "chart_groups" in evaluation_result:
                    # 使用新方法 - 为每组图表生成关联性caption
                    chart_groups = evaluation_result["chart_groups"]
                    print(f"✅ 章节 {chapter_idx+1} 的图表已分为 {len(chart_groups)} 组")
                    
                    # 保存分组信息
                    all_chapter_groups[chapter_idx] = chart_groups
                    
                    # 为每组图表生成caption
                    chapter_schemes = self.generate_group_captions(node, chapter, chart_groups, charts)
                    
                    if chapter_schemes:
                        all_chapter_schemes.append({
                            "chapter_idx": chapter_idx,
                            "schemes": chapter_schemes
                        })
                        print(f"✅ 章节 {chapter_idx+1} 成功生成 {len(chapter_schemes)} 套关联性说明方案")
                        continue
                    else:
                        print(f"⚠️ 章节 {chapter_idx+1} 的组级caption生成失败，将尝试回退到传统方法")
                else:
                    print(f"⚠️ 章节 {chapter_idx+1} 的评估和分组失败，将尝试回退到传统方法")
            except Exception as e:
                print(f"❌ 使用新方法处理章节 {chapter_idx+1} 时出错: {str(e)}")
                print("⚠️ 将尝试回退到传统方法")
                traceback.print_exc()
            
            # 回退策略：使用传统方法为每个图表单独生成caption
            print(f"🔄 使用传统方法处理章节 {chapter_idx+1}")
            traditional_schemes = self.generate_chapter_caption_schemes(
                node,
                chapter, 
                chapter_idx,
                charts, 
                num_schemes=3,
                llm_kwargs=llm_kwargs
            )
            
            if traditional_schemes:
                all_chapter_schemes.append({
                    "chapter_idx": chapter_idx,
                    "schemes": traditional_schemes
                })
                print(f"✅ 章节 {chapter_idx+1} 成功使用传统方法生成 {len(traditional_schemes)} 套说明方案")
            else:
                print(f"❌ 章节 {chapter_idx+1} 的说明生成完全失败")
        
        # 生成子节点组合
        children_nodes = self.generate_combined_nodes(node, all_chapter_schemes, all_chapter_groups)
        
        if not children_nodes:
            # 如果没有成功生成子节点，创建一个基本节点
            print("❌ 无法生成有效的子节点组合，将返回基本节点")
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = self
            child_node.depth = node.depth + 1
            child_node.node_type = ReportGenerationState.a5  # 确保正确设置状态为a5
            print(f"⚠️ 无法生成有效子节点，设置节点状态为: {child_node.node_type}")
            return [child_node]
        
        # 确保所有子节点状态都设置为a5
        for child_node in children_nodes:
            child_node.node_type = ReportGenerationState.a5
            
        print(f"✅ 成功生成 {len(children_nodes)} 个子节点，所有节点状态设置为: {ReportGenerationState.a5}")
        return children_nodes

    def evaluate_and_group_charts(self, node, chapter, charts):
        """批量评估章节内所有图表并进行分组
        
        参数:
            node: MCTS节点
            chapter: 章节对象
            charts: 图表列表
            
        返回:
            result: 包含评估结果和分组信息的字典，如果失败则返回None
        """
        try:
            # 收集图表图像和信息
            chart_images = []
            charts_info = ""
            
            for i, chart in enumerate(charts):
                image_base64 = self._get_image_base64(chart.url)
                if image_base64:
                    chart_images.append(image_base64)
                    charts_info += f"\n图表{i}: 类型: {chart.chart_type}, 任务: {chart.task_id}"
                else:
                    print(f"❌ 无法获取图表 {i} ({chart.task_id}) 的图像数据")
            
            if not chart_images:
                print("❌ 没有可用的图表图像数据")
                return None
                
            # 构建评估和分组提示词
            chapter_title = getattr(chapter, 'title', f'未命名章节')
            prompt_args = {
                "CHAPTER_TITLE": chapter_title,
                "CHARTS_INFO": charts_info,
                "CHARTS_COUNT": len(charts),
                "QUERY": node.original_query,
                "DATA_CONTEXT": node.report.data_context
            }
            
            prompt = get_prompt("chart_evaluation_grouping", prompt_args)
            
            # 实现重试机制
            max_retries = 3
            for retry in range(max_retries):
                try:
                    # 调用API进行批量评估和分组
                    print(f"🔄 正在评估和分组章节 \"{chapter_title}\" 的 {len(charts)} 个图表... (尝试 {retry+1}/{max_retries})")
                    
                    # 调整温度参数，随着重试次数增加降低温度以获得更一致的结果
                    temperature = max(0.2, 0.7 - retry * 0.2)
                    response = self.call_vision_api(prompt, chart_images, temperature=temperature)
                    
                    if not response:
                        print(f"❌ API返回为空 (尝试 {retry+1}/{max_retries})")
                        if retry < max_retries - 1:
                            print("将在2秒后重试...")
                            import time
                            time.sleep(2)
                            continue
                        return None
                        
                    # 解析结果
                    print(f"🔍 LLM响应片段: {response[:200]}...")
                    result = self.extract_json_from_text(response)
                    
                    if result and "chart_evaluations" in result and "chart_groups" in result:
                        # 记录评估结果
                        evaluations = result["chart_evaluations"]
                        print(f"✅ 成功评估 {len(evaluations)} 个图表")
                        for eval_info in evaluations:
                            chart_idx = eval_info.get("chart_idx")
                            if 0 <= chart_idx < len(charts):
                                has_insight = eval_info.get("has_insight", False)
                                insight_score = eval_info.get("insight_score", 0)
                                status = "✅ 有价值" if has_insight else "⚠️ 无价值"
                                print(f"  图表 {chart_idx}: {status} (分数: {insight_score})")
                        
                        # 记录分组结果
                        groups = result["chart_groups"]
                        print(f"✅ 成功将图表分为 {len(groups)} 组")
                        for group in groups:
                            group_id = group.get("group_id")
                            theme = group.get("theme", "未命名主题")
                            chart_indices = group.get("chart_indices", [])
                            print(f"  - 组 {group_id}: {theme} (包含 {len(chart_indices)} 个图表: {chart_indices})")
                        
                        return result
                    else:
                        # 格式错误，提供重试提示
                        error_msg = "解析结果不完整" if result else "未能解析出有效的JSON结果"
                        print(f"❌ {error_msg} (尝试 {retry+1}/{max_retries})")
                        
                        if retry < max_retries - 1:
                            print("将在2秒后重试...")
                            import time
                            time.sleep(2)
                        else:
                            print("已达到最大重试次数，评估分组失败")
                            return None
                            
                except Exception as e:
                    print(f"❌ API调用或解析出错: {str(e)} (尝试 {retry+1}/{max_retries})")
                    if retry < max_retries - 1:
                        print("将在2秒后重试...")
                        import time
                        time.sleep(2)
                    else:
                        print("已达到最大重试次数，评估分组失败")
                        traceback.print_exc()
                        return None
                        
        except Exception as e:
            print(f"❌ 评估和分组图表时出错: {str(e)}")
            traceback.print_exc()
            return None

    def generate_group_captions(self, node, chapter, chart_groups, charts):
        """为每组图表生成关联性caption
        
        参数:
            node: MCTS节点
            chapter: 章节对象
            chart_groups: 图表分组信息
            charts: 图表列表
            
        返回:
            schemes: 包含caption方案的列表，如果失败则返回空列表
        """
        try:
            # 存储所有生成的方案
            schemes = []
            
            # 获取章节标题
            chapter_title = getattr(chapter, 'title', '未命名章节')
            print(f"\n🔄 为章节 \"{chapter_title}\" 的图表组生成caption")
            
            # 处理每个图表组
            for group in chart_groups:
                # 跳过无价值图表组
                group_theme = group.get("theme", "")
                if "无价值" in group_theme.lower() or "无洞察" in group_theme.lower():
                    print(f"⚠️ 跳过无价值图表组: {group_theme}")
                    continue
                    
                # 获取组ID和关系描述
                group_id = group.get("group_id", 0)
                group_relationship = group.get("relationship", "这些图表展示了相关的数据")
                
                # 获取该组所有图表索引
                chart_indices = group.get("chart_indices", [])
                if not chart_indices:
                    print(f"⚠️ 组 {group_id} 没有图表，跳过")
                    continue
                
                print(f"🔄 处理组 {group_id}: {group_theme} (包含 {len(chart_indices)} 个图表)")
                
                # 收集组内图表图像
                group_charts = []
                group_images = []
                
                for idx in chart_indices:
                    if 0 <= idx < len(charts):
                        chart = charts[idx]
                        group_charts.append(chart)
                        
                        image_base64 = self._get_image_base64(chart.url)
                        if image_base64:
                            group_images.append(image_base64)
                        else:
                            print(f"❌ 无法获取组 {group_id} 中图表 {idx} 的图像数据")
                
                if not group_images:
                    print(f"❌ 组 {group_id} 没有可用的图表图像，跳过")
                    continue
                
                # 构建组级caption提示词
                prompt_args = {
                    "QUERY": node.original_query,
                    "CHAPTER_TITLE": chapter_title,
                    "GROUP_THEME": group_theme,
                    "GROUP_RELATIONSHIP": group_relationship,
                    "CHARTS_COUNT": len(group_charts),
                    "DATA_CONTEXT": node.report.data_context
                }
                
                prompt = get_prompt("group_captions", prompt_args)
                
                # 实现重试机制
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        # 调用API生成caption
                        print(f"🔄 为组 {group_id} 生成caption... (尝试 {retry+1}/{max_retries})")
                        
                        # 调整温度参数，随着重试次数增加降低温度
                        temperature = max(0.2, 0.7 - retry * 0.2)
                        response = self.call_vision_api(prompt, group_images, temperature=temperature)
                        
                        if not response:
                            print(f"❌ 组 {group_id} 的API返回为空 (尝试 {retry+1}/{max_retries})")
                            if retry < max_retries - 1:
                                print("将在2秒后重试...")
                                import time
                                time.sleep(2)
                                continue
                            break
                            
                        # 解析结果
                        print(f"🔍 LLM响应片段: {response[:200]}...")
                        caption_result = self.extract_json_from_text(response)
                        
                        if caption_result and "captions" in caption_result:
                            # 创建caption方案
                            scheme = {
                                "scheme_id": len(schemes) + 1,
                                "theme": caption_result.get("theme", group_theme),
                                "captions": []
                            }
                            
                            # 处理每个图表的caption
                            captions = caption_result["captions"]
                            print(f"✅ 成功为组 {group_id} 生成 {len(captions)} 个caption")
                            
                            for i, chart_idx in enumerate(chart_indices):
                                if i < len(captions):
                                    caption_entry = captions[i]
                                    # 提取caption文本，优先使用chart_position匹配
                                    caption_text = ""
                                    
                                    # 查找是否有position匹配的caption
                                    for entry in captions:
                                        if entry.get("chart_position") == i:
                                            caption_text = entry.get("caption", "")
                                            break
                                    
                                    # 如果没找到，使用顺序匹配
                                    if not caption_text:
                                        caption_text = caption_entry.get("caption", "")
                                    
                                    scheme["captions"].append({
                                        "chart_idx": chart_idx,
                                        "caption": caption_text
                                    })
                                    
                            # 添加到方案列表
                            schemes.append(scheme)
                            # 成功生成，跳出重试循环
                            break
                            
                        else:
                            # 格式错误，提供重试提示
                            error_msg = "解析结果不完整" if caption_result else "未能解析出有效的JSON结果"
                            print(f"❌ {error_msg} (尝试 {retry+1}/{max_retries})")
                            
                            if retry < max_retries - 1:
                                print("将在2秒后重试...")
                                import time
                                time.sleep(2)
                            else:
                                print(f"❌ 已达到最大重试次数，组 {group_id} 的caption生成失败")
                                
                    except Exception as e:
                        print(f"❌ 组 {group_id} 的caption生成出错: {str(e)} (尝试 {retry+1}/{max_retries})")
                        if retry < max_retries - 1:
                            print("将在2秒后重试...")
                            import time
                            time.sleep(2)
                        else:
                            print(f"❌ 已达到最大重试次数，组 {group_id} 的caption生成失败")
                            traceback.print_exc()
            
            # 返回所有生成的方案
            if schemes:
                print(f"✅ 成功为 {len(schemes)} 个图表组生成caption方案")
            else:
                print("⚠️ 未能为任何图表组生成caption方案")
                
            return schemes
                
        except Exception as e:
            print(f"❌ 生成组级caption时出错: {str(e)}")
            traceback.print_exc()
            return []


class Captions2Summaries(DataStorytellingAction):
    def __init__(self):
        super().__init__("A6", "根据每个章节的Caption生成每个章节的总结")
        self.use_unified_framework = True  # 是否使用统一框架
    
    def generate_summary_prompt(self, node, chapter_idx=None, **kwargs):
        """生成章节总结提示词"""
        # 如果指定了章节索引，生成特定章节的提示词
        if chapter_idx is not None and 0 <= chapter_idx < len(node.report.chapters):
            chapter = node.report.chapters[chapter_idx]
            chapter_title = getattr(chapter, 'title', f"章节{chapter_idx+1}") if not isinstance(chapter, dict) else chapter.get('title', f"章节{chapter_idx+1}")
            
            # 收集本章节所有图表及其说明
            visualization_tasks = []
            if hasattr(chapter, 'visualization_tasks'):
                for task in chapter.visualization_tasks:
                    task_info = {
                        'description': task.get('task_description', ''),
                        'charts': []
                    }
                    
                    # 检查章节是否有图表
                    if hasattr(chapter, 'charts') and chapter.charts:
                        # 查找与任务关联的图表
                        for chart in chapter.charts:
                            if hasattr(chart, 'task_id') and chart.task_id == task.get('task_id'):
                                # 检查该图表任务是否成功完成
                                task_success = False
                                for t in chapter.visualization_tasks:
                                    if t.get('task_id') == chart.task_id and t.get('visualization_success', False):
                                        task_success = True
                                        break
                                
                                if task_success:
                                    caption = getattr(chart, 'caption', '无说明文字')
                                    task_info['charts'].append({
                                        'caption': caption
                                    })
                    
                    # 只添加有图表的任务
                    if task_info['charts']:
                        visualization_tasks.append(task_info)
            
            # 准备提示词参数
            prompt_args = {
                "QUERY": node.original_query,
                "CHAPTER_TITLE": chapter_title,
                "visualization_tasks": json.dumps(visualization_tasks, ensure_ascii=False, indent=2)
            }
            
            return get_prompt("chapter_summary", prompt_args)
        
        # 如果没有指定章节，返回基本信息
        return {
            "QUERY": node.report.clarified_query if node.report.clarified_query else node.report.original_query,
            "DATA_CONTEXT": node.report.data_context
        }
    
    def apply_summaries(self, node, action, cluster, **kwargs):
        """将章节总结应用到子节点"""
        # 创建子节点
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = action
        child_node.depth = node.depth + 1
        
        try:
            # 从聚类中获取每个章节的总结
            if "chapter_summaries" in cluster:
                chapter_summaries = cluster["chapter_summaries"]
                
                # 应用章节总结
                success_count = 0
                for chapter_summary in chapter_summaries:
                    chapter_idx = chapter_summary.get("chapter_idx", -1)
                    summary = chapter_summary.get("summary", "")
                    
                    if 0 <= chapter_idx < len(child_node.report.chapters):
                        chapter = child_node.report.chapters[chapter_idx]
                        chapter.summary = summary
                        success_count += 1
                        print(f"✅ 已应用第 {chapter_idx + 1} 章的总结")
                
                # 设置节点状态
                if success_count > 0:
                    child_node.node_type = ReportGenerationState.FINALIZED
                    return [child_node]
            
            # 如果没有从聚类中获取到总结，尝试自行处理
            print("⚠️ 未从聚类中获取到章节总结，尝试自行处理...")
            success = self.process_all_chapters(child_node, **kwargs)
            
            if success:
                # 设置节点状态
                child_node.node_type = ReportGenerationState.FINALIZED
                return [child_node]
            else:
                print("❌ 处理章节总结失败")
                return None
                
        except Exception as e:
            print(f"❌ 应用章节总结时出错: {str(e)}")
            traceback.print_exc()
            return None
    
    def generate_chapter_summaries(self, node, llm_kwargs, n=3):
        """为每个章节生成多个候选总结"""
        all_chapter_summaries = []
        
        # 遍历所有章节
        for chapter_idx, chapter in enumerate(node.report.chapters):
            # 安全地获取章节标题
            chapter_title = getattr(chapter, 'title', f"章节{chapter_idx+1}") if not isinstance(chapter, dict) else chapter.get('title', f"章节{chapter_idx+1}")
            
            print(f"\n📑 正在为第 {chapter_idx + 1} 章生成多个候选总结...")
            print(f"章节标题: {chapter_title}")
            
            # 检查该章节是否有图表及说明
            has_captions = False
            if hasattr(chapter, 'charts') and chapter.charts:
                for chart in chapter.charts:
                    if hasattr(chart, 'caption') and chart.caption:
                        has_captions = True
                        break
            
            if not has_captions:
                print(f"⚠️ 章节 {chapter_idx + 1} 没有图表或说明文字，跳过")
                continue
                
            # 生成该章节的提示词
            prompt = self.generate_summary_prompt(node, chapter_idx=chapter_idx)
            
            # 收集该章节的多个候选总结
            chapter_summaries = []
            
            for i in range(n):
                # 为每个候选使用不同的温度
                llm_kwargs_temp = llm_kwargs.copy()
                llm_kwargs_temp['temperature'] = 0.3 + i * 0.2  # 0.3, 0.5, 0.7
                
                print(f"🔄 生成第 {chapter_idx + 1} 章的候选总结 {i+1}/{n} (温度: {llm_kwargs_temp['temperature']})")
                
                responses = call_openai(prompt, **llm_kwargs_temp)
                if responses:
                    summary = responses[0].strip()
                    
                    # 收集候选总结
                    chapter_summaries.append({
                        "chapter_idx": chapter_idx,
                        "summary": summary,
                        "variant_id": i
                    })
                    
                    print(f"✅ 成功生成第 {chapter_idx + 1} 章的候选总结 {i+1}")
                else:
                    print(f"❌ 第 {chapter_idx + 1} 章的候选总结 {i+1} 生成失败")
            
            # 如果成功生成了候选总结，添加到列表中
            if chapter_summaries:
                all_chapter_summaries.append({
                    "chapter_idx": chapter_idx,
                    "chapter_title": chapter_title,
                    "candidate_summaries": chapter_summaries
                })
        
        return all_chapter_summaries
    
    def cluster_chapter_summaries(self, all_chapter_summaries, llm_kwargs):
        """对每个章节的候选总结进行聚类，并选择最优总结"""
        if not all_chapter_summaries:
            return []
        
        try:
            # 准备聚类数据
            formatting_data = []
            for chapter_data in all_chapter_summaries:
                chapter_idx = chapter_data["chapter_idx"]
                chapter_title = chapter_data["chapter_title"]
                candidates = chapter_data["candidate_summaries"]
                
                # 转换为聚类所需的格式
                formatted_candidates = [
                    {
                        "index": candidate["variant_id"],
                        "chapter_idx": chapter_idx,
                        "summary": candidate["summary"]
                    }
                    for candidate in candidates
                ]
                
                formatting_data.append({
                    "chapter_idx": chapter_idx,
                    "chapter_title": chapter_title,
                    "candidates": formatted_candidates
                })
            
            # 使用模板文件生成聚类提示词
            prompt_args = {
                "CHAPTER_SUMMARIES_DATA": json.dumps(formatting_data, ensure_ascii=False, indent=2)
            }
            
            clustering_prompt = get_prompt("chapter_summary_clustering", prompt_args)
            
            # 调用 LLM 进行聚类
            print("\n🔍 正在对章节总结进行聚类分析...")
            responses = call_openai(clustering_prompt, **llm_kwargs)
            
            if not responses:
                print("❌ 聚类分析没有收到有效响应")
                return []
            
            # 解析响应
            clustering_response = responses[0]
            
            # 提取 JSON 部分
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', clustering_response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = clustering_response
            
            try:
                # 解析 JSON
                clustering_result = json.loads(json_str)
                
                # 检查是否有有效的聚类结果
                if "clusters" in clustering_result and clustering_result["clusters"]:
                    print(f"✅ 成功获取 {len(clustering_result['clusters'])} 个聚类")
                    return clustering_result["clusters"]
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析错误: {str(e)}")
                print(f"❌ 原始响应:\n{clustering_response}")
        
        except Exception as e:
            print(f"❌ 聚类章节总结时出错: {str(e)}")
            traceback.print_exc()
        
        return []
    
    def process_all_chapters(self, node, **kwargs):
        """处理所有章节，为每个章节生成总结"""
        llm_kwargs = kwargs.get("llm_kwargs", {})
        
        try:
            # 如果是使用统一框架并且有多个候选总结
            if self.use_unified_framework:
                # 为每个章节生成多个候选总结
                all_chapter_summaries = self.generate_chapter_summaries(node, llm_kwargs)
                
                if not all_chapter_summaries:
                    print("❌ 没有成功生成任何章节的候选总结")
                    return False
                
                # 对候选总结进行聚类并选择最优总结
                clusters = self.cluster_chapter_summaries(all_chapter_summaries, llm_kwargs)
                
                if not clusters:
                    print("❌ 没有获取到有效的聚类结果")
                    return False
                
                # 应用第一个聚类的结果
                cluster = clusters[0]
                print(f"✅ 应用聚类 {cluster.get('cluster_id', '未知')} 的总结结果")
                
                # 应用章节总结
                chapter_summaries = cluster.get("chapter_summaries", [])
                success_count = 0
                
                for chapter_summary in chapter_summaries:
                    chapter_idx = chapter_summary.get("chapter_idx", -1)
                    summary = chapter_summary.get("summary", "")
                    
                    if 0 <= chapter_idx < len(node.report.chapters):
                        chapter = node.report.chapters[chapter_idx]
                        chapter.summary = summary
                        success_count += 1
                        print(f"✅ 已应用第 {chapter_idx + 1} 章的总结")
                
                return success_count > 0
            else:
                # 原有的逻辑（未使用统一框架）
                success_count = 0

                # 遍历所有章节
                for chapter_idx, chapter in enumerate(node.report.chapters):
                    # 安全地获取章节标题
                    chapter_title = getattr(chapter, 'title', f"章节{chapter_idx+1}") if not isinstance(chapter, dict) else chapter.get('title', f"章节{chapter_idx+1}")
                    
                    print(f"\n📑 正在处理第 {chapter_idx + 1} 章: {chapter_title}")
                    
                    # 检查章节是否有可视化任务
                    if not hasattr(chapter, 'visualization_tasks') or not chapter.visualization_tasks:
                        print(f"⚠️ 章节 {chapter_idx + 1} 没有可视化任务，跳过")
                        continue
                    
                    # 收集本章节所有图表及其说明
                    visualization_tasks = []
                    for task in chapter.visualization_tasks:
                        task_info = {
                            'description': task.get('task_description', ''),
                            'charts': []
                        }
                        
                        # 检查章节是否有图表
                        if not hasattr(chapter, 'charts') or not chapter.charts:
                            continue
                            
                        # 查找与任务关联的图表
                        for chart in chapter.charts:
                            if hasattr(chart, 'task_id') and chart.task_id == task.get('task_id'):
                                caption = getattr(chart, 'caption', '无说明文字')
                                task_info['charts'].append({
                                    'caption': caption
                                })
                        
                        # 只添加有图表的任务
                        if task_info['charts']:
                            visualization_tasks.append(task_info)
                    
                    # 如果没有收集到任何有效的可视化任务，跳过此章节
                    if not visualization_tasks:
                        print(f"⚠️ 章节 {chapter_idx + 1} 没有有效的可视化任务图表，跳过")
                        continue
                    
                    # 准备 prompt
                    prompt_args = {
                        "QUERY": node.original_query,
                        "CHAPTER_TITLE": chapter_title,
                        "visualization_tasks": json.dumps(visualization_tasks, ensure_ascii=False, indent=2)
                    }
                    
                    prompt = get_prompt("chapter_summary", prompt_args)
                    
                    # 调用 LLM 生成摘要
                    responses = call_openai(prompt, **llm_kwargs)
                    if not responses:
                        print(f"❌ 章节 {chapter_idx + 1} 没有收到有效响应")
                        continue
                    
                    summary = responses[0].strip()
                    
                    print(f"\n📝 第 {chapter_idx + 1} 章的摘要:")
                    print("-" * 50)
                    print(summary)
                    print("-" * 50)
                    
                    # 保存摘要到章节
                    chapter.summary = summary
                    print(f"✅ 已生成第 {chapter_idx + 1} 章的摘要")
                    success_count += 1

                return success_count > 0
                
        except Exception as e:
            print(f"❌ 生成章节摘要时出错: {str(e)}")
            traceback.print_exc()
            return False
                
    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        if self.use_unified_framework:
            # 为每个章节生成多个候选总结
            all_chapter_summaries = self.generate_chapter_summaries(node, llm_kwargs)
            
            if not all_chapter_summaries:
                print("❌ 没有成功生成任何章节的候选总结，创建默认节点")
                child_node = copy.deepcopy(node)
                child_node.parent_node = node
                child_node.parent_action = self
                child_node.depth = node.depth + 1
                child_node.node_type = ReportGenerationState.FINALIZED
                return [child_node]
            
            # 对候选总结进行聚类并选择最优总结
            clusters = self.cluster_chapter_summaries(all_chapter_summaries, llm_kwargs)
            
            if not clusters:
                print("❌ 没有获取到有效的聚类结果，创建默认节点")
                child_node = copy.deepcopy(node)
                child_node.parent_node = node
                child_node.parent_action = self
                child_node.depth = node.depth + 1
                child_node.node_type = ReportGenerationState.FINALIZED
                return [child_node]
            
            # 为每个聚类创建一个子节点
            children_nodes = []
            
            for cluster_idx, cluster in enumerate(clusters):
                cluster_id = cluster.get("cluster_id", f"cluster_{cluster_idx+1}")
                
                print(f"🔄 正在为聚类 {cluster_id} 创建子节点")
                
                # 创建子节点
                child_node = copy.deepcopy(node)
                child_node.parent_node = node
                child_node.parent_action = self
                child_node.depth = node.depth + 1
                
                # 应用章节总结
                chapter_summaries = cluster.get("chapter_summaries", [])
                success_count = 0
                
                for chapter_summary in chapter_summaries:
                    chapter_idx = chapter_summary.get("chapter_idx", -1)
                    summary = chapter_summary.get("summary", "")
                    
                    if 0 <= chapter_idx < len(child_node.report.chapters):
                        chapter = child_node.report.chapters[chapter_idx]
                        chapter.summary = summary
                        success_count += 1
                        print(f"✅ 为聚类 {cluster_id} 应用第 {chapter_idx + 1} 章的总结")
                
                if success_count > 0:
                    # 设置节点状态
                    child_node.node_type = ReportGenerationState.a6
                    child_node.summary_cluster_id = cluster_id
                    children_nodes.append(child_node)
                    print(f"✅ 成功创建聚类 {cluster_id} 的子节点")
            
            # 如果没有创建任何子节点，创建一个默认节点
            if not children_nodes:
                print("❌ 没有创建任何有效的子节点，创建默认节点")
                child_node = copy.deepcopy(node)
                child_node.parent_node = node
                child_node.parent_action = self
                child_node.depth = node.depth + 1
                child_node.node_type = ReportGenerationState.a6
                return [child_node]
            
            return children_nodes
        else:
            # 原有实现（保留以便兼容）
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = self
            child_node.depth = node.depth + 1
            
            # 处理所有章节的总结
            self.process_all_chapters(child_node, llm_kwargs=llm_kwargs)
        
        # 设置最终状态
        child_node.node_type = ReportGenerationState.a6
        
        return [child_node]
    
class ReviseNarrativeStrategy(DataStorytellingAction):
    def __init__(self):
        super().__init__("NarrativeStrategy", "调整报告叙事策略，重新排序章节")
        self.use_unified_framework = True  # 使用统一框架
    
    def generate_narrative_prompt(self, node, **kwargs):
        """生成叙事策略提示词"""
        # 准备章节信息
        chapters_info = []
        for i, chapter in enumerate(node.report.chapters):
            chapter_info = {
                "index": i,
                "title": getattr(chapter, 'title', f"章节{i+1}"),
                "summary": getattr(chapter, 'summary', "") if hasattr(chapter, 'summary') else ""
            }
            chapters_info.append(chapter_info)
        
        # 使用模板生成提示词
        prompt_args = {
            "QUERY": node.report.clarified_query if node.report.clarified_query else node.report.original_query,
            "CHAPTERS": json.dumps(chapters_info, ensure_ascii=False, indent=2)
        }
        
        return get_prompt("revise_narrative", prompt_args)
    
    def apply_narrative_strategy(self, node, action, cluster, **kwargs):
        """将叙事策略应用到子节点"""
        try:
            # 创建子节点
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = action
            child_node.depth = node.depth + 1
            
            # 获取叙事策略和章节顺序
            cluster_id = cluster.get("cluster_id", "未知")
            strategy = cluster.get("strategy", "")
            strategy_reason = cluster.get("strategy_reason", "")
            chapter_order = cluster.get("chapter_order", [])
            
            if not chapter_order:
                print(f"⚠️ 聚类 {cluster_id} 没有章节顺序信息，跳过")
                return None
            
            print(f"📘 应用聚类 {cluster_id} 的叙事策略方案")
            print(f"   策略: {strategy}")
            print(f"   原因: {strategy_reason}")
            
            # 验证章节顺序
            if len(chapter_order) != len(node.report.chapters):
                print(f"⚠️ 章节数量不匹配: 期望 {len(node.report.chapters)}, 实际 {len(chapter_order)}")
                return None
                
            # 根据新顺序重排章节
            new_chapters = []
            for chapter_info in chapter_order:
                original_index = chapter_info.get("original_index")
                if not isinstance(original_index, int) or original_index < 0 or original_index >= len(node.report.chapters):
                    print(f"⚠️ 无效的章节索引: {original_index}")
                    continue
                
                new_chapters.append(copy.deepcopy(node.report.chapters[original_index]))
                print(f"   - 移动章节 '{chapter_info.get('title', '')}' 到新位置")
                print(f"     原因: {chapter_info.get('reason', '未提供')}")
            
            # 如果没有成功重排所有章节，跳过此聚类
            if len(new_chapters) != len(node.report.chapters):
                print(f"⚠️ 章节重排不完整，跳过此聚类")
                return None
            
            # 更新报告的章节顺序和叙事策略
            child_node.report.chapters = new_chapters
            child_node.report.narrative_strategy = {
                "strategy": strategy,
                "strategy_reason": strategy_reason,
                "cluster_id": cluster_id
            }
            
            # 设置节点状态
            child_node.node_type = ReportGenerationState.REVISECHAPTERSORDERS
            
            print(f"✅ 成功应用聚类 {cluster_id} 的叙事策略方案")
            return [child_node]
            
        except Exception as e:
            print(f"❌ 应用叙事策略时出错: {str(e)}")
            traceback.print_exc()
            return None
    
    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """生成多个叙事策略方案并聚类选择最优方案"""
        return unified_generation_framework(
            node=node,
            action=self,
            llm_kwargs=llm_kwargs,
            action_type="narrative",
            prompt_generator=self.generate_narrative_prompt,
            node_applier=self.apply_narrative_strategy,
            n=3  # 生成3个不同的叙事策略方案
        )



class TransitionAction(DataStorytellingAction):
    def __init__(self):
        super().__init__("Transition", "添加章节间过渡文本，提高报告连贯性")
        self.use_unified_framework = True  # 使用统一框架
    
    def generate_transition_prompt(self, node, **kwargs):
        """生成过渡文本提示词"""
        # 准备章节信息
        chapters_info = []
        for i, chapter in enumerate(node.report.chapters):
            chapter_info = {
                "index": i,
                "title": getattr(chapter, 'title', f"章节{i+1}"),
                "summary": getattr(chapter, 'summary', "") if hasattr(chapter, 'summary') else "",
                "charts_captions": [
                    getattr(chart, 'caption', "") for chart in getattr(chapter, 'charts', [])
                ]
            }
            chapters_info.append(chapter_info)
        
        # 使用模板生成提示词
        prompt_args = {
            "QUERY": node.report.clarified_query if node.report.clarified_query else node.report.original_query,
            "CHAPTERS": json.dumps(chapters_info, ensure_ascii=False, indent=2),
            "NARRATIVE_STRATEGY": json.dumps(getattr(node.report, 'narrative_strategy', {}), ensure_ascii=False, indent=2)
        }
        
        return get_prompt("add_transitions", prompt_args)
    
    def apply_transitions(self, node, action, cluster, **kwargs):
        """将过渡文本应用到子节点"""
        try:
            # 创建子节点
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = action
            child_node.depth = node.depth + 1
            
            # 获取过渡文本方案
            cluster_id = cluster.get("cluster_id", "未知")
            transitions = cluster.get("transitions", [])
            
            if not transitions:
                print(f"⚠️ 聚类 {cluster_id} 没有过渡文本信息，跳过")
                return None
            
            print(f"📝 应用聚类 {cluster_id} 的过渡文本方案")
            
            # 应用过渡文本
            success_count = 0
            for transition in transitions:
                chapter_idx = transition.get("chapter_idx")
                transition_text = transition.get("transition_text", "")
                
                if not isinstance(chapter_idx, int) or chapter_idx < 0 or chapter_idx >= len(child_node.report.chapters):
                    print(f"⚠️ 无效的章节索引: {chapter_idx}")
                    continue
                
                # 添加过渡文本到章节
                chapter = child_node.report.chapters[chapter_idx]
                if not hasattr(chapter, 'transition'):
                    chapter.transition = ""
                
                chapter.transition = transition_text
                success_count += 1
                print(f"   ✅ 为第 {chapter_idx + 1} 章添加过渡文本")
            
            # 如果没有成功添加任何过渡文本，跳过此聚类
            if success_count == 0:
                print(f"⚠️ 没有成功添加任何过渡文本，跳过此聚类")
                return None
            
            # 设置节点状态
            child_node.node_type = ReportGenerationState.FINALIZED
            
            print(f"✅ 成功应用聚类 {cluster_id} 的过渡文本方案，共 {success_count} 个过渡")
            return [child_node]
            
        except Exception as e:
            print(f"❌ 应用过渡文本时出错: {str(e)}")
            traceback.print_exc()
            return None
    
    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """生成多个过渡文本方案并聚类选择最优方案"""
        return unified_generation_framework(
            node=node,
            action=self,
            llm_kwargs=llm_kwargs,
            action_type="transition",
            prompt_generator=self.generate_transition_prompt,
            node_applier=self.apply_transitions,
            n=3  # 生成3个不同的过渡文本方案
        )

    

# 修正 save_chart 方法，将其作为类方法而不是独立函数
class ChartUtils:
    @staticmethod
    def save_chart(node: MCTSNode, chart_data: dict) -> str:
        """保存图表并返回URL"""
        # 获取当前迭代号，添加调试信息
        current_iteration = node.report.current_iteration
        print(f"Debug: 保存图表时的迭代号: {current_iteration}")
        print(f"Debug: 节点类型: {node.node_type}")
        print(f"Debug: 节点深度: {node.depth}")
        
        # 确保使用正确的迭代号
        if current_iteration is None or current_iteration < 1:
            print("警告: current_iteration 无效，使用默认值 1")
            current_iteration = 1
        
        # 构建保存路径
        iteration_dir = os.path.join("storyteller", "output", "iterations", f"iteration_{current_iteration}")
        charts_dir = os.path.join(iteration_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        print(f"Debug: 图表将保存到: {charts_dir}")
        
        return charts_dir

    def get_current_iteration_dir(self):
        """获取当前迭代的输出目录"""
        try:
            # 检查是否有当前迭代目录属性
            if hasattr(self, 'current_iteration_dir') and self.current_iteration_dir:
                return self.current_iteration_dir
            
            # 检查是否有输出根目录属性
            if hasattr(self, 'output_dir') and self.output_dir:
                # 找到最新的迭代目录
                iteration_dirs = glob.glob(os.path.join(self.output_dir, "iteration_*"))
                if iteration_dirs:
                    # 按创建时间排序，获取最新的
                    latest_dir = max(iteration_dirs, key=os.path.getctime)
                    return latest_dir
            
            # 如果没有设置输出目录，使用默认的输出目录
            default_output_dir = os.path.join("output", "mcts")
            os.makedirs(default_output_dir, exist_ok=True)
            
            # 查找最新的迭代目录
            iteration_dirs = glob.glob(os.path.join(default_output_dir, "iteration_*"))
            if iteration_dirs:
                latest_dir = max(iteration_dirs, key=os.path.getctime)
                return latest_dir
            
            # 如果没有找到迭代目录，创建一个新的
            new_dir = os.path.join(default_output_dir, f"iteration_{int(time.time())}")
            os.makedirs(new_dir, exist_ok=True)
            return new_dir
            
        except Exception as e:
            print(f"⚠️ 获取当前迭代目录时出错: {str(e)}")
            # 返回临时目录
            temp_dir = os.path.join("output", "temp_charts")
            os.makedirs(temp_dir, exist_ok=True)
            return temp_dir




# 将字典定义保留为模块级变量
NODE_TYPE_TO_VALID_ACTIONS = {
    ReportGenerationState.EMPTY: [
        Query2Chapters
    ],
    ReportGenerationState.a1: [
        Chapters2Tasks,
    ],
    ReportGenerationState.a2: [
        Tasks2Charts
    ],
    ReportGenerationState.a3: [
        ReviseVis,
        Charts2Captions
    ],
    ReportGenerationState.a4: [
        Charts2Captions
    ],
    ReportGenerationState.a5: [
        Captions2Summaries,
    ],
    ReportGenerationState.a6: [
        ReviseNarrativeStrategy,
        TransitionAction
    ],
    ReportGenerationState.REVISECHAPTERSORDERS: [
        TransitionAction
    ], 
    ReportGenerationState.FINALIZED: []  # 终止状态，添加过渡后的最终状态
}



