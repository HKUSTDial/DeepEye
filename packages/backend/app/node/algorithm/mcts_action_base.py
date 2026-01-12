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
import io
from openai import OpenAI
from .utils.html2image import convert_html_file_to_image




class DataStorytellingAction:
    def __init__(self, action_id: str, description: str):
        self.action_id = action_id
        self.description = description# 默认的下一个状态
        
        # 添加 MCTS 统计属性
        self.Q = 0.0  # 累积奖励
        self.N = 0    # 访问次数
    
    # def update_node_state(self, node: "MCTSNode") -> None:
    #     """根据动作ID和执行结果更新节点状态"""
    #     if self.next_state:
    #         node.node_type = self.next_state
        # 如果没有设置默认的下一个状态，则保持当前状态不变

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = self
        child_node.depth = node.depth + 1
        
        raise NotImplementedError

    # def is_applicable(self, node: "MCTSNode") -> bool:
    #     """默认可用，子类可以 override 实现顺序约束"""
    #     return True


# class QueryDataProcessorAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("A1", "解析用户查询，准备数据集", 
#                          [ReportGenerationState.EMPTY], 
#                          ReportGenerationState.EMPTY)
#         self.dataset_generator = None  # 初始化为 None

#     def is_applicable(self, node: MCTSNode) -> bool:
#         """检查是否可以执行数据处理动作"""
#         # 检查是否已经处理过数据
#         if node.data_processed:
#             return False
#         # 检查是否在正确的状态
#         if node.node_type != ReportGenerationState.EMPTY:
#             return False
#         return True

#     def create_children_nodes(self, node: MCTSNode, llm_kwargs: Dict[str, Any]) -> List[MCTSNode]:
#         """执行数据处理动作，创建子节点"""
#         # 在这里初始化 dataset_generator，使用传入的配置
#         if self.dataset_generator is None:
#             self.dataset_generator = DatasetContextGenerator(
#                 api_key=llm_kwargs.get("api_key"),
#                 base_url=llm_kwargs.get("base_url")
#             )
        
#         nodes = []

#         # 1️⃣ **调用 DatasetContextGenerator 解析数据集**
#         dataset_info = self.dataset_generator.generate_context(node.report.dataset_path, dataset_description=node.report.dataset_description)

#         # 2️⃣ **更新 MCTS 报告对象**
#         node.report.data_context = dataset_info["dataset_summary"]  # 生成的数据集摘要
#         node.report.full_column_names = dataset_info["full_column_names"]  # LLM 生成的完整列名

#         # 3️⃣ **生成 LLM 提示（用于 Query 处理）**
#         query_prompt = get_prompt("query_processor", {"QUERY": node.report.original_query})
#         query_responses = call_openai(query_prompt, **llm_kwargs)

#         # 4️⃣ **遍历 LLM 响应，为每个 Query 解析结果创建子节点**
#         if not query_responses:
#             # 添加默认节点，避免空响应导致搜索中断
#             child_node = copy.deepcopy(node)
#             child_node.node_type = ReportGenerationState.CHAPTER_DEFINED  
#             child_node.parent_node = node
#             child_node.parent_action = self
#             child_node.depth = node.depth + 1
#             child_node.report.clarified_query = node.report.original_query  # 使用原始查询
#             child_node.Q = 0
#             nodes.append(child_node)
#         else:
#             for query_response in query_responses:
#                 child_node = copy.deepcopy(node)
#                 child_node.node_type = ReportGenerationState.CHAPTER_DEFINED  
#                 child_node.parent_node = node
#                 child_node.parent_action = self
#                 child_node.depth = node.depth + 1
#                 child_node.report.clarified_query = query_response.strip()
#                 child_node.Q = 0  # 先设为 0，延迟评估
#                 nodes.append(child_node)
        
#         # 在返回前更新状态
#         for child_node in nodes:
#             child_node.node_type = ReportGenerationState.EMPTY
        
#         # 创建新节点
#         child_node = copy.deepcopy(node)
#         child_node.data_processed = True  # 标记数据已处理
#         child_node.node_type = ReportGenerationState.EMPTY  # 保持在 EMPTY 状态
        
#         return [child_node]
    

# class ChapterDivisionAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("A2", "定义章节结构", 
#                          [ReportGenerationState.EMPTY], 
#                          ReportGenerationState.CHAPTER_DEFINED)  # 不改变状态

#     def is_applicable(self, node):
#             # 如果所有章节已经有任务了，就不该再执行
#             if not node.report.chapters:
#                 return True
#             print("❌ 所有章节都有任务就不再生成")
#             return False  # 有章节就不再生成

#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         """
#         根据用户查询和数据上下文，将查询按不同维度分解成章节形式
        
#         例如：
#         - 原始查询："不同消费者的消费偏好有什么不同？"
#         - 可能的章节划分：
#           1. 不同年龄段的消费者的消费偏好有什么不同？
#           2. 不同性别的消费者的消费偏好有什么不同？
#           3. 会员和非会员消费者消费偏好有什么不同？
          
#         或者按消费偏好维度划分：
#           1. 消费金额有什么不同？
#           2. 消费的物品类别有什么不同？
#           3. 消费频率有什么不同？
#         """
#         # 使用 clarified_query（如果有）或原始查询
#         query = node.report.clarified_query if node.report.clarified_query else node.report.original_query
        
#         # 构建提示，包含查询和数据上下文
#         prompt = get_prompt("chapter_division", {
#             "QUERY": query,
#             "DATA_CONTEXT": node.report.data_context
#         })
        
#         # 调用 LLM 生成章节划分方案
#         responses = call_openai(prompt, **llm_kwargs)
#         nodes = []
        
#         # 如果响应为空，返回当前节点作为子节点，防止流程中断
#         if not responses:
#             child_node = copy.deepcopy(node)
#             child_node.parent_node = node
#             child_node.parent_action = self
#             child_node.depth = node.depth + 1
#             child_node.node_type = ReportGenerationState.CHAPTER_DEFINED
            
#             # 如果没有章节，添加一个默认章节
#             if not child_node.report.chapters:
#                 child_node.report.add_chapter(Chapter(title=query))
            
#             nodes.append(child_node)
#             return nodes
        
#         # 处理每个响应，创建子节点
#         for response in responses:
#             try:
#                 # 清理响应，移除 Markdown 代码块标记
#                 cleaned_response = self._clean_json_response(response)
                
#                 #print(f"原始响应: {response}")
#                 print(f"清理后的响应: {cleaned_response}")
                
#                 # 解析 JSON 响应
#                 chapter_data = json.loads(cleaned_response)
                
#                 # 创建子节点
#                 child_node = copy.deepcopy(node)
#                 child_node.parent_node = node
#                 child_node.parent_action = self
#                 child_node.depth = node.depth + 1
                
#                 # 清空现有章节（如果有）
#                 child_node.report.chapters = []
                
#                 # 添加章节
#                 if "chapters" in chapter_data:
#                     # 新格式：包含章节标题和描述
#                     for chapter_info in chapter_data["chapters"]:
#                         title = chapter_info["title"]
#                         summary = chapter_info.get("summary", "")
#                         child_node.report.add_chapter(Chapter(title=title, summary=summary))
#                 elif "chapter_titles" in chapter_data:
#                     # 旧格式：只有章节标题
#                     for title in chapter_data["chapter_titles"]:
#                         child_node.report.add_chapter(Chapter(title=title))
                
#                 # 添加到节点列表
#                 nodes.append(child_node)
                
#             except json.JSONDecodeError as e:
#                 print(f"无法解析 JSON 响应: {response}")
#                 print(f"错误详情: {e}")
#                 continue
#             except Exception as e:
#                 print(f"处理章节划分响应时出错: {e}")
#                 continue
        
#         # 如果处理完所有响应后节点列表仍为空，添加默认节点
#         if not nodes:
#             child_node = copy.deepcopy(node)
#             child_node.parent_node = node
#             child_node.parent_action = self
#             child_node.depth = node.depth + 1
            
#             # 如果没有章节，添加一个默认章节
#             if not child_node.report.chapters:
#                 child_node.report.add_chapter(Chapter(title=query))
            
#             nodes.append(child_node)
        
#         # 状态变
#         for child_node in nodes:
#             child_node.node_type = ReportGenerationState.CHAPTER_DEFINED
        
#         return nodes

#     def _clean_json_response(self, response: str) -> str:
#         """
#         清理 LLM 返回的 JSON 响应，移除 Markdown 代码块标记
        
#         参数:
#             response: LLM 返回的原始响应
            
#         返回:
#             清理后的 JSON 字符串
#         """
#         # 移除 Markdown 代码块开始标记（```json 或 ```）
#         response = re.sub(r'^```(?:json)?\s*', '', response)
        
#         # 移除 Markdown 代码块结束标记（```）
#         response = re.sub(r'\s*```$', '', response)
        
#         # 移除可能的前导和尾随空白字符
#         response = response.strip()
        
#         return response


class Query2Chapters(DataStorytellingAction):
    def __init__(self):
        super().__init__("A1", "定义章节结构") 


    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """
        根据用户查询和数据上下文，尝试不同的章节划分策略
        """
        # 使用 clarified_query（如果有）或原始查询
        query = node.report.clarified_query if node.report.clarified_query else node.report.original_query
        
        # 构建提示，包含查询和数据上下文
        prompt = get_prompt("Query2Chapters", {
            "QUERY": query,
            "DATA_CONTEXT": node.report.data_context
        })
        
        # 调用 LLM 生成章节划分方案
        responses = call_openai(prompt, **llm_kwargs)
        nodes = []
        
        # 如果响应为空，返回当前节点作为子节点，防止流程中断
        if not responses:
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = self
            child_node.depth = node.depth + 1
            
            # 如果没有章节，添加一个默认章节
            if not child_node.report.chapters:
                child_node.report.add_chapter(Chapter(title=query))
            
            nodes.append(child_node)
            return nodes
        
        # 处理每个响应，创建子节点
        for response in responses:
            try:
                # 清理响应，移除 Markdown 代码块标记
                cleaned_response = self._clean_json_response(response)
                
                #print(f"原始响应: {response}")
                print(f"清理后的响应: {cleaned_response}")
                
                # 解析 JSON 响应
                chapter_data = json.loads(cleaned_response)
                
                # 创建子节点
                child_node = copy.deepcopy(node)
                child_node.parent_node = node
                child_node.parent_action = self
                child_node.depth = node.depth + 1
                
                # 清空现有章节（如果有）
                child_node.report.chapters = []
                
                # 添加章节
                if "chapters" in chapter_data:
                    # 新格式：包含章节标题和描述
                    for title in chapter_data["chapters"]:
                        child_node.report.add_chapter(Chapter(title=title))
                
                # 添加到节点列表
                nodes.append(child_node)
                
            except json.JSONDecodeError as e:
                print(f"无法解析 JSON 响应: {response}")
                print(f"错误详情: {e}")
                continue
            except Exception as e:
                print(f"处理章节划分响应时出错: {e}")
                continue
        
        # 如果处理完所有响应后节点列表仍为空，添加默认节点
        if not nodes:
            child_node = copy.deepcopy(node)
            child_node.parent_node = node
            child_node.parent_action = self
            child_node.depth = node.depth + 1
            
            # 如果没有章节，添加一个默认章节
            if not child_node.report.chapters:
                child_node.report.add_chapter(Chapter(title=query))
            
            nodes.append(child_node)
        
        return nodes

    def _clean_json_response(self, response: str) -> str:
        """
        清理 LLM 返回的 JSON 响应，移除 Markdown 代码块标记
        
        参数:
            response: LLM 返回的原始响应
            
        返回:
            清理后的 JSON 字符串
        """
        # 移除 Markdown 代码块开始标记（```json 或 ```）
        response = re.sub(r'^```(?:json)?\s*', '', response)
        
        # 移除 Markdown 代码块结束标记（```）
        response = re.sub(r'\s*```$', '', response)
        
        # 移除可能的前导和尾随空白字符
        response = response.strip()
        
        return response


# class ChapterVisTaskAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("A3", "生成可视化任务", 
#                          [ReportGenerationState.CHAPTER_DEFINED], 
#                          ReportGenerationState.CHAPTER_DEFINED)  # 不改变状态

#     def is_applicable(self, node):
#         # 如果没有任务，则执行
#         for chapter in node.report.chapters:
#             if not chapter.visualization_tasks:
#                 return True
#         print("❌ 所有章节都有任务就不再生成")
#         return False  # 所有章节都有任务就不再生成

#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         """为每个章节生成可视化任务"""
#         # 创建子节点
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         try:
#             # 获取数据集信息
#             data_context = node.report.data_context
            
#             # 生成 LLM 提示词
#             prompt_text = get_prompt("chapter_vistask", {
#                 "QUERY": node.original_query,
#                 "DATA_CONTEXT": data_context,
#                 "CHAPTERS": json.dumps([{"title": chapter.title} for chapter in node.report.chapters], ensure_ascii=False)
#             })
            
#             # 调用 LLM 生成可视化任务
#             responses = call_openai(prompt_text, **llm_kwargs)
#             if not responses:
#                 print("❌ 没有收到有效响应")
#                 return [child_node]
                
#             response_text = responses[0]
            
#             # 尝试解析 JSON
#             try:
#                 # 清理响应文本，提取 JSON 部分
#                 json_text = self.extract_json_from_text(response_text)
#                 print(f"原始响应: {json_text}")
                
#                 # 解析 JSON
#                 response_json = json.loads(json_text)
                
#                 # 处理每个章节的可视化任务
#                 if "chapters" in response_json:
#                     # 创建章节标题到索引的映射
#                     chapter_title_to_index = {}
#                     for i, chapter in enumerate(child_node.report.chapters):
#                         chapter_title_to_index[chapter.title.lower()] = i
                    
#                     # 处理每个章节
#                     for chapter_info in response_json["chapters"]:
#                         title = chapter_info.get("title", "")
#                         tasks = chapter_info.get("tasks", [])
                        
#                         # 查找匹配的章节
#                         chapter_idx = -1
#                         title_lower = title.lower()
                        
#                         # 精确匹配
#                         if title_lower in chapter_title_to_index:
#                             chapter_idx = chapter_title_to_index[title_lower]
#                         else:
#                             # 模糊匹配
#                             for i, chapter in enumerate(child_node.report.chapters):
#                                 if title_lower in chapter.title.lower() or chapter.title.lower() in title_lower:
#                                     chapter_idx = i
#                                     break
                        
#                         if chapter_idx >= 0 and chapter_idx < len(child_node.report.chapters):
#                             chapter = child_node.report.chapters[chapter_idx]
                            
#                             # 关键修复：清空现有任务列表，避免累加
#                             chapter.visualization_tasks = []
                            
#                             # 添加任务
#                             for task in tasks:
#                                 description = task.get("description", "")
#                                 chart_type = task.get("chart_type", ["Bar Chart"])
                                
#                                 # 创建任务对象
#                                 task_obj = {
#                                     "task_id": description,  # 直接使用描述作为ID
#                                     "description": description,
#                                     "chart_type": chart_type,
#                                     "relevant_columns": [],
#                                     "status": "pending"  # 添加状态字段
#                                 }
                                
#                                 # 添加到章节的任务列表
#                                 chapter.visualization_tasks.append(task_obj)
                                
#                                 # 打印任务状态
#                                 print(f"   - 任务: '{description}' | 状态: {task_obj.get('status')}")
                            
#                             # 打印调试信息
#                             print(f"✅ 为章节 {chapter_idx+1} ({chapter.title}) 生成了 {len(tasks)} 个可视化任务")
#                             print(f"   章节现在有 {len(chapter.visualization_tasks)} 个任务")
#                         else:
#                             print(f"❌ 找不到匹配的章节: {title}")
                
#                 # 检查所有章节是否都有任务
#                 for i, chapter in enumerate(child_node.report.chapters):
#                     if not hasattr(chapter, 'visualization_tasks') or not chapter.visualization_tasks:
#                         print(f"⚠️ 章节 {i+1} ({chapter.title}) 没有任务")
#                     else:
#                         print(f"✓ 章节 {i+1} ({chapter.title}) 有 {len(chapter.visualization_tasks)} 个任务")
                
#             except json.JSONDecodeError as e:
#                 print(f"❌ JSON 解析错误: {str(e)}")
#                 print("⚠️ 无法解析 JSON，请检查模板和 LLM 响应")
            
#             # 更新节点状态
#             child_node.node_type = ReportGenerationState.CHAPTER_DEFINED
            
#             return [child_node]
            
#         except Exception as e:
#             print(f"❌ 生成可视化任务时出错: {str(e)}")
#             import traceback
#             traceback.print_exc()
        
#         # 确保即使出错也返回子节点
#         return [child_node]
    
#     def extract_json_from_text(self, response_text):
#         """从文本中提取 JSON 部分"""
#         try:
#             # 尝试直接解析整个响应
#             json.loads(response_text)
#             return response_text
#         except:
#             # 如果直接解析失败，尝试提取 JSON 部分
#             import re
            
#             # 移除 markdown 代码块标记
#             response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
#             response_text = re.sub(r'\s*```$', '', response_text)
            
#             # 查找 JSON 对象
#             json_pattern = r'\{.*\}'
#             json_match = re.search(json_pattern, response_text, re.DOTALL)
            
#             if json_match:
#                 return json_match.group(0)
            
#             return response_text

class Chapters2Tasks(DataStorytellingAction):
    def __init__(self):
        super().__init__("A2", "根据章节方案划分章节任务方案")  # 不改变状态


    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """为每个章节生成可视化任务"""
        # 创建子节点
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = self
        child_node.depth = node.depth + 1
        
        try:
            # 获取数据集信息
            data_context = node.report.data_context
            
            # 生成 LLM 提示词
            prompt_text = get_prompt("Chapters2Tasks", {
                "QUERY": node.original_query,
                "DATA_CONTEXT": data_context,
                "CHAPTERS": json.dumps([{"title": chapter.title} for chapter in node.report.chapters], ensure_ascii=False)
        })
        
        # 调用 LLM 生成可视化任务
            responses = call_openai(prompt_text, **llm_kwargs)
            if not responses:
                print("❌ 没有收到有效响应")
                return [child_node]
        
            response_text = responses[0]
            
            # 尝试解析 JSON
            try:
                # 清理响应文本，提取 JSON 部分
                json_text = self.extract_json_from_text(response_text)
                print(f"原始响应: {json_text}")
                
                # 解析 JSON
                response_json = json.loads(json_text)
                
                # 处理每个章节的可视化任务
                if "chapters" in response_json:
                    # 创建章节标题到索引的映射
                    chapter_title_to_index = {}
                    for i, chapter in enumerate(child_node.report.chapters):
                        chapter_title_to_index[chapter.title.lower()] = i
                    
                    # 处理每个章节
                    for chapter_info in response_json["chapters"]:
                        title = chapter_info.get("title", "")
                        tasks = chapter_info.get("tasks", [])
                        
                        # 查找匹配的章节
                        chapter_idx = -1
                        title_lower = title.lower()
                        
                        # 精确匹配
                        if title_lower in chapter_title_to_index:
                            chapter_idx = chapter_title_to_index[title_lower]
                        else:
                            # 模糊匹配
                            for i, chapter in enumerate(child_node.report.chapters):
                                if title_lower in chapter.title.lower() or chapter.title.lower() in title_lower:
                                    chapter_idx = i
                                break
                        
                        if chapter_idx >= 0 and chapter_idx < len(child_node.report.chapters):
                            chapter = child_node.report.chapters[chapter_idx]
                            
                            # 关键修复：清空现有任务列表，避免累加
                            chapter.visualization_tasks = []
                            
                            # 添加任务
                            for task in tasks:
                                task_id = task.get("task_id", "")
                                description = task.get("description", "")
                                chart_type = task.get("chart_type", ["Bar Chart"])
                                
                                # 创建任务对象
                                task_obj = {
                                    "task_id": task_id,
                                    "task_description": description,  # 直接使用描述作为ID
                                    "chart_type": chart_type,
                                    "status": "pending"  # 添加状态字段
                                }
                                
                                # 添加到章节的任务列表
                                chapter.visualization_tasks.append(task_obj)
                                
                                # 打印任务状态
                                print(f"   - 任务: '{description}' | 状态: {task_obj.get('status')}")
                            
                            # 打印调试信息
                            print(f"✅ 为章节 {chapter_idx+1} ({chapter.title}) 生成了 {len(tasks)} 个可视化任务")
                            print(f"   章节现在有 {len(chapter.visualization_tasks)} 个任务")
                        else:
                            print(f"❌ 找不到匹配的章节: {title}")
                
                # 检查所有章节是否都有任务
                for i, chapter in enumerate(child_node.report.chapters):
                    if not hasattr(chapter, 'visualization_tasks') or not chapter.visualization_tasks:
                        print(f"⚠️ 章节 {i+1} ({chapter.title}) 没有任务")
                    else:
                        print(f"✓ 章节 {i+1} ({chapter.title}) 有 {len(chapter.visualization_tasks)} 个任务")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析错误: {str(e)}")
                print("⚠️ 无法解析 JSON，请检查模板和 LLM 响应")
            
            return [child_node]
            
        except Exception as e:
            print(f"❌ 生成可视化任务时出错: {str(e)}")
    # 确保即使出错也返回子节点
        return [child_node]

    def extract_json_from_text(self, response_text):
        """从文本中提取 JSON 部分"""
        try:
            # 尝试直接解析整个响应
            json.loads(response_text)
            return response_text
        except:
            # 如果直接解析失败，尝试提取 JSON 部分
            import re
            
            # 移除 markdown 代码块标记
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            # 查找 JSON 对象
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                return json_match.group(0)
            
            return response_text




# class SelectNextVisualizationTaskAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("A4", "选择下一个需要可视化的任务", 
#                          [ReportGenerationState.CHAPTER_DEFINED, 
#                          ReportGenerationState.CHAPTER_IN_PROGRESS],
#                          ReportGenerationState.CHAPTER_IN_PROGRESS)

#     def is_applicable(self, node: "MCTSNode") -> bool:
#         """检查是否可以选择下一个可视化任务"""
#         # 首先检查当前选中的任务是否需要生成 caption
#         selected = getattr(node, 'selected_task', None)
#         if selected:
#             chapter_idx = selected.get('chapter_idx')
#             task_id = selected.get('task_id')
#             if chapter_idx is not None and task_id:
#                 chapter = node.report.chapters[chapter_idx]
#                 # 检查任务状态
#                 for task in chapter.visualization_tasks:
#                     if task.get('task_id') == task_id:
#                         if task.get('status') == 'needs_caption':
#                             print(f"❌ 当前任务 '{task['description']}' 需要生成 caption")
#                             return False
#                         elif task.get('status') == 'needs_vis':
#                             print(f"❌ 当前任务 '{task['description']}' 需要生成可视化")
#                             return False
#                         break

#         # 如果当前任务已完成或没有选中的任务，检查是否有其他待处理任务
#         has_pending_task = False
#         has_task_in_progress = False
        
#         for chapter in node.report.chapters:
#             if not hasattr(chapter, 'visualization_tasks'):
#                 continue
                
#             for task in chapter.visualization_tasks:
#                 status = task.get('status', 'pending')
#                 if status == 'pending':
#                     has_pending_task = True
#                 elif status in ['needs_vis', 'needs_caption']:
#                     task_id = task.get('task_id')
#                     print(f"❌ 有任务正在处理中: {task_id}")
#                     has_task_in_progress = True
                    
#         if has_task_in_progress:
#             return False
            
#         if has_pending_task:
#             print("✅ 有待处理的任务")
#             return True
            
#         print("❌ 没有待处理的任务")
#         return False

#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         """选择下一个可视化任务"""
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         try:
#             # 查找待处理的任务
#             selected_task = None
            
#             for chapter_idx, chapter in enumerate(child_node.report.chapters):
#                 if not hasattr(chapter, 'visualization_tasks'):
#                     continue
                    
#                 for task_idx, task in enumerate(chapter.visualization_tasks):
#                     if task.get('status') == 'pending':
#                         # 找到一个待处理的任务
#                         selected_task = {
#                             'chapter_idx': chapter_idx,
#                             'chapter_title': chapter.title,
#                             'task_idx': task_idx,
#                             'task_id': task.get('task_id'),
#                             'description': task.get('description'),
#                             'chart_type': task.get('chart_type', []),
#                             'relevant_columns': task.get('relevant_columns', [])
#                         }
#                         # 更新任务状态为 needs_vis
#                         task['status'] = 'needs_vis'
#                         print(f"✅ 选中任务: {task.get('description')} (章节 {chapter_idx + 1})")
#                         break
                        
#                 if selected_task:
#                     break
                    
#             if selected_task:
#                 # 将选中的任务保存到节点中
#                 child_node.selected_task = selected_task
#                 child_node.node_type = ReportGenerationState.CHAPTER_IN_PROGRESS
#             else:
#                 # 如果没有找到待处理的任务，检查是否所有任务都已完成
#                 all_completed = True
#                 for chapter in child_node.report.chapters:
#                     if hasattr(chapter, 'visualization_tasks'):
#                         for task in chapter.visualization_tasks:
#                             if task.get('status') != 'completed':
#                                 all_completed = False
#                                 break
                
#                 if all_completed:
#                     child_node.node_type = ReportGenerationState.ALL_OF_CHAPTERS_COMPLETED
#                     print("✅ 所有可视化任务都已完成，状态更新为 ALL_OF_CHAPTERS_COMPLETED")
#                 else:
#                     print("⚠️ 没有找到待处理的任务，但仍有未完成的任务")
                    
#         except Exception as e:
#             print(f"❌ 选择任务时出错: {str(e)}")
            
#         return [child_node]



# class GenerateVisualizationAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("A5", "生成可视化", 
#                          [ReportGenerationState.CHAPTER_IN_PROGRESS], 
#                          ReportGenerationState.CHAPTER_IN_PROGRESS)

#     def is_applicable(self, node: "MCTSNode") -> bool:
#         """检查是否可以生成可视化图表"""
#         # 检查是否有选中的任务
#         selected = getattr(node, 'selected_task', None)
#         if not selected:
#             print("❌ 没有选中的任务")
#             return False
            
#         # 获取章节和任务
#         chapter_idx = selected.get('chapter_idx')
#         if chapter_idx is None or chapter_idx >= len(node.report.chapters):
#             print("❌ 无效的章节索引")
#             return False
            
#         chapter = node.report.chapters[chapter_idx]
#         task_id = selected.get('task_id')
        
#         # 检查任务状态
#         for task in chapter.visualization_tasks:
#             if task.get('task_id') == task_id:
#                 if task.get('status') == 'needs_vis':
#                     print(f"✅ 任务 '{selected.get('description')}' 需要生成可视化")
#                     return True
#                 else:
#                     print(f"❌ 任务 '{selected.get('description')}' 状态不是 needs_vis: {task.get('status')}")
#                     return False
                    
#         print(f"❌ 找不到任务 ID: {task_id}")
#         return False
        
#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         try:
#             # 获取选中的任务
#             selected_task = getattr(node, 'selected_task', None)
#             if not selected_task:
#                 print("❌ 没有选中的任务")
#                 return [child_node]
                
#             # 获取章节和任务信息
#             chapter_idx = selected_task.get('chapter_idx')
#             task_id = selected_task.get('task_id')
#             description = selected_task.get('description')
            
#             if chapter_idx is None or chapter_idx >= len(child_node.report.chapters):
#                 print("❌ 无效的章节索引")
#                 return [child_node]
                
#             chapter = child_node.report.chapters[chapter_idx]
            
#             # 生成可视化图表
#             dataset_path = node.report.dataset_path
#             df = pd.read_csv(dataset_path)
            
#             # 检查数据集中的类别值
#             if 'Category' in df.columns:
#                 print(f"数据集中的类别值: {df['Category'].unique()}")
            
#             if 'Gender' in df.columns:
#                 print(f"数据集中的性别值: {df['Gender'].unique()}")
            
#             # 确定当前迭代号
#             current_iteration = node.report.current_iteration or 1
#             iteration_dir = os.path.join("storyteller", "output", "iterations", f"iteration_{current_iteration}")
#             os.makedirs(iteration_dir, exist_ok=True)
#             charts_dir = os.path.join(iteration_dir, "charts")
#             os.makedirs(charts_dir, exist_ok=True)

#             # 保存图表
#             chart_path = os.path.join(charts_dir, f"chart_{task_id}.png")

            
#             from lida.datamodel import Goal, Summary
#             from lida.components.manager import Manager
#             # 创建 Goal 对象 - 使用 description 替代 task_name
#             chart_type = selected_task.get("chart_type", ["Bar Chart"])[0] if selected_task.get("chart_type") else "Bar Chart"
#             goal = Goal(question=description, visualization=chart_type, rationale=description)
            
#             # 创建 Summary 对象
#             summary = Summary(
#                 name="购物数据分析",
#                 file_name=dataset_path,
#                 dataset_description=node.report.data_context,
#                 field_names=df.columns.tolist(),
#                 fields=[str(dtype) for dtype in df.dtypes.tolist()]
#             )
            
#             # 创建 LIDA 管理器
#             manager = Manager()
            
#             # 生成可视化
#             print(f"正在为任务 '{description}' 生成可视化图表...")
#             visualization = manager.visualize(summary, goal, library="matplotlib")
            
#             # 处理可视化结果
#             if isinstance(visualization, list) and len(visualization) > 0:
#                 visualization = visualization[0]
            
#             visualization_success = False
            
#             if hasattr(visualization, 'status') and visualization.status:
#                 print("✓ 成功生成可视化结果")
                
#                 # 保存图表
#                 if hasattr(visualization, 'savefig'):
#                     visualization.savefig(chart_path)
#                     print(f"✓ 图表已保存到: {chart_path}")
                    
#                     # 获取章节
#                     chapter_idx = selected_task.get('chapter_idx')
#                     chapter = child_node.report.chapters[chapter_idx]
                    
#                     # 创建图表对象
#                     chart = Chart(
#                         url=chart_path,
#                         caption="",  # 使用空字符串作为初始说明
#                         chart_type=chart_type,
#                         task_id=task_id  # task_id 实际上就是任务描述
#                     )
#                     chart.needs_caption = True  # 设置需要生成说明文字的标志
                    
#                     # 添加图表到章节
#                     chapter.charts.append(chart)
                    
#                     # 更新任务状态，标记为需要生成 caption
#                     for task in chapter.visualization_tasks:
#                         if task['task_id'] == task_id:
#                             task['status'] = 'needs_caption'  # 更新状态
#                             task['visualization_generated'] = True
#                             print(f"✅ 任务 '{description}' 已生成图表，等待生成 caption")
#                             break
                        
#                     print(f"⏳ 图表已标记为需要生成说明文字")
#                     visualization_success = True
#                 else:
#                     print("❌ 可视化对象没有 savefig 方法")
#                     # 即使失败也标记为完成，避免无限循环
#                     chapter_idx = selected_task.get('chapter_idx')
#                     chapter = child_node.report.chapters[chapter_idx]
#                     for task in chapter.visualization_tasks:
#                         if task.get('task_id') == task_id:
#                             task['status'] = 'completed'  # 标记为完成
#                             task['visualization_success'] = False
#                             print(f"⚠️ 任务 '{description}' 虽然失败但已标记为已完成，避免无限循环")
#                             break
#             else:
#                 print("✗ 生成可视化图表失败")
#                 # 即使失败也标记为完成，避免无限循环
#                 chapter_idx = selected_task.get('chapter_idx')
#                 chapter = child_node.report.chapters[chapter_idx]
#                 for task in chapter.visualization_tasks:
#                     if task.get('task_id') == task_id:
#                         task['status'] = 'completed'  # 标记为完成
#                         task['visualization_success'] = False
#                         print(f"⚠️ 任务 '{description}' 虽然失败但已标记为已完成，避免无限循环")
#                         break
    
#         except Exception as e:
#             print(f"❌ 生成可视化图表时出错: {str(e)}")
            
#         return [child_node]


class Tasks2Charts(DataStorytellingAction):
    def __init__(self):
        super().__init__("A3", "生成可视化")

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = self
        child_node.depth = node.depth + 1

        try:
            # 获取数据集
            dataset_path = node.report.dataset_path
            df = pd.read_csv(dataset_path)
            
            # 遍历所有章节
            for chapter_idx, chapter in enumerate(child_node.report.chapters):
                # 遍历章节中的所有可视化任务
                for task in chapter.visualization_tasks:
                    task_id = task.get('task_id', "")
                    description = task.get('task_description')
                    chart_type = task.get('chart_type', ["Bar Chart"])[0]
                    
                    # 确定当前迭代号和保存路径
                    current_iteration = node.report.current_iteration or 1
                    iteration_dir = os.path.join("storyteller", "output", "iterations", f"iteration_{current_iteration}")
                    os.makedirs(iteration_dir, exist_ok=True)
                    charts_dir = os.path.join(iteration_dir, "charts")
                    os.makedirs(charts_dir, exist_ok=True)

                    # 保存图表
                    chart_path = os.path.join(charts_dir, f"{description}.png")

                    
                    from lida.datamodel import Goal, Summary
                    from lida.components.manager import Manager
                    # 创建 Goal 对象 - 使用 description 替代 task_name
                    goal = Goal(question=task_id, visualization=chart_type, rationale=description)

                    # 创建 Summary 对象
                    summary = Summary(
                        name="购物数据分析",
                        file_name=dataset_path,
                        dataset_description=node.report.data_context,
                        field_names=df.columns.tolist(),
                        fields=[str(dtype) for dtype in df.dtypes.tolist()]
                    )
                    
                    # 创建 LIDA 管理器
                    manager = Manager()

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
                            
                        # 创建图表对象
                            chart = Chart(
                                url=chart_path,
                                caption="",  # 使用空字符串作为初始说明
                                chart_type=chart_type,
                                task_id=task_id  # task_id 实际上就是任务描述
                                )
                                
                                # 添加图表到章节
                            chapter.charts.append(chart)
                    else:
                        print("✗ 生成可视化图表失败")
                        # 即使失败也标记为完成，避免无限循环
                        chapter_idx = task.get('chapter_idx')
                        chapter = child_node.report.chapters[chapter_idx]
                        for task in chapter.visualization_tasks:
                            if task.get('task_id') == task_id:
                                task['visualization_success'] = False
                                print(f"⚠️ 任务 '{description}' 虽然失败但已标记为已完成，避免无限循环")
                                break
            return [child_node]
                            
        except Exception as e:
            print(f"❌ 处理节点时出错: {str(e)}")
            return [child_node]


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
        

        # 遍历所有章节
        for chapter_idx, chapter in enumerate(child_node.report.chapters):
            for task in chapter.visualization_tasks:
                if task['visualization_success'] == True:
                    continue
                task_id = task.get('task_id', "")
                description = task.get('task_description')
                
                print(f"正在修改任务 '{description}' 的图表...")
        
                for c in chapter.charts:
                    if hasattr(c, 'task_id') and c.task_id == task_id:
                        selected_chart = c

                    try:
                        # 获取数据文件路径
                        dataset_path = node.report.dataset_path
                        
                        # 读取数据
                        df = pd.read_csv(dataset_path)
                        
                        # 创建 LIDA 管理器
                        from lida.components.manager import Manager
                        from lida.datamodel import Summary
                        
                        manager = Manager()
                        
                        # 读取数据摘要 JSON 文件
                        data_summary = {}
                        json_path = os.path.join(os.path.dirname(dataset_path), "data_context.json")
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
                            dataset_description=data_summary.get("dataset_description", "购物数据集"),
                            field_names=list(data_summary.get("fields_info", {}).keys()) if "fields_info" in data_summary else df.columns.tolist(),
                            fields=[info.get("dtype", "unknown") for info in data_summary.get("fields_info", {}).values()] if "fields_info" in data_summary else [str(dtype) for dtype in df.dtypes.tolist()]
                        )
                        
                        # 生成编辑指令
                        edit_instruction = "让图表更加美观，清晰"
                        #print(f"生成的编辑指令: {edit_instruction}")
                        
                        # 使用 LIDA 的 edit 功能修改图表
                        print(f"正在修改任务 '{description}' 的图表...")
                        edited_visualization = manager.edit(
                            code=selected_chart.code,
                            summary=summary,
                            instructions=edit_instruction,
                            library="matplotlib"
                        )
                        
                        # 处理编辑后的可视化结果
                        if edited_visualization is None:
                            print("✗ 编辑可视化图表失败: 返回结果为None")
                        elif isinstance(edited_visualization, list) and len(edited_visualization) > 0:
                            edited_visualization = edited_visualization[0]
                            print("✓ 使用第一个编辑结果进行处理")
                        
                        # 检查是否为有效的编辑结果
                        if hasattr(edited_visualization, 'status') and edited_visualization.status:
                            print("✓ 成功修改可视化图表")
                            
                            # 找到当前图表所在的迭代目录
                            original_chart_path = selected_chart.url
                            chart_dir = os.path.dirname(original_chart_path)
                            
                            # 将修改后的图表保存到同一目录下
                            edited_chart_name = f"{task_id}_edited.png"
                            edited_chart_path = os.path.join(chart_dir, edited_chart_name)
                            
                            
                                        # 保存修改后的图表
                            if hasattr(edited_visualization, 'savefig'):
                                            edited_visualization.savefig(edited_chart_path)
                                            print(f"✓ 修改后的图表已保存到: {edited_chart_path}")
                            
                            # 创建新的图表对象
                            from storyteller.algorithm.mcts_node import Chart
                            edited_chart = Chart(
                                            url=edited_chart_path,
                                            caption="",  # 使用空字符串作为初始说明
                                            chart_type=selected_chart.chart_type,
                                            task_id=task_id  # 使用原始任务ID/描述
                                        )
                            edited_chart.needs_caption = True  # 设置需要生成说明文字的标志
                            
                            # 更新章节中的图表
                            for i, c in enumerate(chapter.charts):
                                if hasattr(c, 'task_id') and c.task_id == task_id:
                                    chapter.charts[i] = edited_chart
                                    break
                                else:
                                    error_msg = edited_visualization.error if hasattr(edited_visualization, 'error') else "未知错误"
                                    print(f"✗ 修改可视化图表失败: {error_msg}")
                        else:
                            print("✗ 编辑可视化图表失败: 返回结果无效")

                    except Exception as e:
                        print(f"✗ 修改可视化图表时发生错误: {str(e)}")
                        import traceback
                        traceback.print_exc()
 
                        
                            
            return [child_node]         
        # 如果没有找到任务，返回空列表
        print("❌ 没有找到待处理的任务")
        return []
    
   
# class ReviseVisualizationAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("A6", "修改可视化图表", 
#                          [ReportGenerationState.CHAPTER_IN_PROGRESS])
    

#     def is_applicable(self, node: "MCTSNode") -> bool:
#         """检查是否可以修改可视化图表"""
#         # 检查是否有选中的任务
#         selected = getattr(node, 'selected_task', None)
#         if not selected:
#             print("❌ 没有选中的任务")
#             return False
            
#         # 获取章节索引并检查其有效性
#         chapter_idx = selected.get('chapter_idx')
#         if chapter_idx is None or chapter_idx >= len(node.report.chapters):
#             print("❌ 无效的章节索引")
#             return False
            
#         chapter = node.report.chapters[chapter_idx]
#         task_id = selected.get('task_id')
        
#         # 检查任务状态 - 只有在任务不是 needs_caption 状态时才可以修改图表
#         for task in chapter.visualization_tasks:
#             if task.get('task_id') == task_id:
#                 if task.get('status') == 'needs_caption':
#                     print(f"❌ 任务 '{selected.get('description')}' 需要先生成 caption")
#                     return False
                    
#                 # 检查是否有图表可以修改
#                 has_chart = False
#                 for chart in getattr(chapter, 'charts', []):
#                     if chart.task_id == task_id:
#                         has_chart = True
#                 break
        
#                 if not has_chart:
#                     print(f"❌ 找不到与任务关联的图表")
#                     return False
                    
#                 print(f"✅ 可以修改任务 '{selected.get('description')}' 的图表")
#                 return True
                
#         print(f"❌ 找不到任务 ID: {task_id}")
#         return False

#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         """修改可视化图表"""
#         # 创建子节点
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         # 获取当前选中的任务
#         if hasattr(node, 'selected_task') and node.selected_task:
#             selected_task = node.selected_task
#             chapter_idx = selected_task.get('chapter_idx')
            
#             if chapter_idx is not None:
#                 chapter = child_node.report.chapters[chapter_idx]
                
#                 # 直接从 selected_task 中获取任务属性
#                 task_id = selected_task.get("task_id", "")
#                 description = selected_task.get("description", "")
                
#                 # 查找对应的图表
#                 selected_chart = None
#                 for c in chapter.charts:
#                     if hasattr(c, 'task_id') and c.task_id == task_id:
#                         selected_chart = c
#                         break
                
#                 if selected_chart is None:
#                     print(f"❌ 找不到任务 '{description}' 对应的图表")
#                     return [child_node]
                
#                 print(f"正在修改任务 '{description}' 的图表...")
        
#         try:
#             # 获取数据文件路径
#             dataset_path = node.report.dataset_path
            
#             # 读取数据
#             df = pd.read_csv(dataset_path)
            
#             # 创建 LIDA 管理器
#             from lida.components.manager import Manager
#             from lida.datamodel import Summary
            
#             manager = Manager()
            
#             # 读取数据摘要 JSON 文件
#             data_summary = {}
#             json_path = os.path.join(os.path.dirname(dataset_path), "data_context.json")
#             print(f"尝试读取数据摘要 JSON: {json_path}")
            
#             try:
#                 with open(json_path, 'r', encoding='utf-8') as f:
#                     data_summary = json.load(f)
#                 print("✓ 成功读取数据摘要 JSON")
#             except Exception as e:
#                 print(f"✗ 读取数据摘要 JSON 失败: {str(e)}")
#                 # 如果无法读取 JSON 文件，使用默认值
#                 data_summary = {
#                     "name": node.report.original_query,
#                     "dataset_description": node.report.data_context,
#                     "fields_info": {col: {"dtype": str(dtype)} for col, dtype in zip(df.columns, df.dtypes)}
#                 }
            
#             # 创建 Summary 对象，直接从 JSON 文件中提取必要参数
#             summary = Summary(
#                         name=data_summary.get("name", "数据分析"),
#                 file_name=dataset_path,  # 使用原始数据文件路径
#                 dataset_description=data_summary.get("dataset_description", "购物数据集"),
#                 field_names=list(data_summary.get("fields_info", {}).keys()) if "fields_info" in data_summary else df.columns.tolist(),
#                 fields=[info.get("dtype", "unknown") for info in data_summary.get("fields_info", {}).values()] if "fields_info" in data_summary else [str(dtype) for dtype in df.dtypes.tolist()]
#             )
            
#             # 生成编辑指令
#                     edit_instruction = "让图表更加美观，清晰"
#             print(f"生成的编辑指令: {edit_instruction}")
            
#             # 使用 LIDA 的 edit 功能修改图表
#                     print(f"正在修改任务 '{description}' 的图表...")
#             edited_visualization = manager.edit(
#                         code=selected_chart.code,
#                 summary=summary,
#                 instructions=edit_instruction,
#                 library="matplotlib"
#             )
            
#             # 处理编辑后的可视化结果
#                     if edited_visualization is None:
#                         print("✗ 编辑可视化图表失败: 返回结果为None")
#                     elif isinstance(edited_visualization, list) and len(edited_visualization) > 0:
#                 edited_visualization = edited_visualization[0]
#                 print("✓ 使用第一个编辑结果进行处理")
            
#             # 检查是否为有效的编辑结果
#             if hasattr(edited_visualization, 'status') and edited_visualization.status:
#                 print("✓ 成功修改可视化图表")
                
#                             # 找到当前图表所在的迭代目录
#                             original_chart_path = selected_chart.url
#                             chart_dir = os.path.dirname(original_chart_path)
                            
#                             # 将修改后的图表保存到同一目录下
#                             edited_chart_name = f"chart_{task_id}_edited.png"
#                             edited_chart_path = os.path.join(chart_dir, edited_chart_name)
                            
#                             # 如果是图表在根目录的charts下，则需要将它修改到迭代目录下
#                             if "iterations" not in edited_chart_path:
#                                 # 确定当前迭代号
#                                 current_iteration = node.report.current_iteration or 1
#                                 iteration_dir = os.path.join("storyteller", "output", "iterations", f"iteration_{current_iteration}")
#                                 os.makedirs(iteration_dir, exist_ok=True)
#                                 charts_dir = os.path.join(iteration_dir, "charts")
#                                 os.makedirs(charts_dir, exist_ok=True)
#                                 edited_chart_path = os.path.join(charts_dir, edited_chart_name)
                            
#                             # 保存修改后的图表
#                 if hasattr(edited_visualization, 'savefig'):
#                                 edited_visualization.savefig(edited_chart_path)
#                                 print(f"✓ 修改后的图表已保存到: {edited_chart_path}")
                
#                 # 创建新的图表对象
#                 from storyteller.algorithm.mcts_node import Chart
#                 edited_chart = Chart(
#                                 url=edited_chart_path,
#                                 caption="",  # 使用空字符串作为初始说明
#                                 chart_type=selected_chart.chart_type,
#                                 task_id=task_id  # 使用原始任务ID/描述
#                             )
#                             edited_chart.needs_caption = True  # 设置需要生成说明文字的标志
                
#                 # 更新章节中的图表
#                             for i, c in enumerate(chapter.charts):
#                                 if hasattr(c, 'task_id') and c.task_id == task_id:
#                                     chapter.charts[i] = edited_chart
#                                     break
                
#                             print(f"✓ 成功修改任务 '{description}' 的图表")
#             else:
#                 error_msg = edited_visualization.error if hasattr(edited_visualization, 'error') else "未知错误"
#                 print(f"✗ 修改可视化图表失败: {error_msg}")
#                     else:
#                         print("✗ 编辑可视化图表失败: 返回结果无效")
        
#         except Exception as e:
#             print(f"✗ 修改可视化图表时发生错误: {str(e)}")
#             import traceback
#             traceback.print_exc()
        
#                 # 检查是否所有任务都已完成
#                 all_tasks_completed = True
#                 for chapter in child_node.report.chapters:
#                     if hasattr(chapter, 'visualization_tasks') and chapter.visualization_tasks:
#                         for task in chapter.visualization_tasks:
#                             task_id = task.get('task_id')
#                             if hasattr(chapter, 'tasks_status'):
#                                 if task_id and chapter.tasks_status.get(task_id) != "completed":
#                                     all_tasks_completed = False
#                                     break
#         else:
#                                 if task.get('status') != 'completed':
#                                     all_tasks_completed = False
#                                     break
                
#                 if all_tasks_completed:
#                     child_node.node_type = ReportGenerationState.ALL_OF_CHAPTERS_COMPLETED
#                     print("✅ 所有章节的可视化任务都已完成，状态更新为 ALL_OF_CHAPTERS_COMPLETED")
#                 else:
#                     child_node.node_type = ReportGenerationState.CHAPTER_IN_PROGRESS
#                     print("⚠️ 还有未完成的任务，状态保持为 CHAPTER_IN_PROGRESS")
                
#                 return [child_node]
        
#         # 如果没有找到任务，返回空列表
#         print("❌ 没有找到待处理的任务")
#         return []
   
class Charts2Captions(DataStorytellingAction):
    def __init__(self):
        super().__init__("A5", "根据所有可视化图表生成所有对应Caption")
    
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

    def clean_response(self, response: str) -> str:
        """清理 API 返回的响应内容"""
        # 如果响应包含完整的 HTML 文档，说明可能是错误的响应
        if '<!doctype html>' in response.lower():
            return ""
        
        # 移除任何 HTML 标签
        import re
        clean_text = re.sub(r'<[^>]+>', '', response)
        
        # 清理多余的空白字符
        clean_text = ' '.join(clean_text.split())
        
        return clean_text.strip()

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        """为图表生成说明文字"""
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = self
        child_node.depth = node.depth + 1
        
        try:
            selected = getattr(node, 'selected_task', None)
            chapter = child_node.report.chapters[selected['chapter_idx']]
            
            # 为需要生成 caption 的图表生成说明文字
            for chart in chapter.charts:
                if (chart.task_id == selected['task_id'] and 
                    getattr(chart, 'needs_caption', False)):
                    
                    print(f"\n📊 正在为图表生成说明文字...")
                    print(f"📌 任务描述: {selected['description']}")
                    print(f"📍 图表路径: {chart.url}")
                    
                    # 获取图片的 base64 编码
                    base64_image = self._get_image_base64(chart.url)
                    if not base64_image:
                        print("❌ 图片处理失败，跳过该图表")
                        continue

                    # 准备 prompt
                    prompt_args = {
                        "QUERY": node.original_query,
                        "CHAPTER_TITLE": chapter.title,
                        "CHART_TYPE": chart.chart_type,
                        "TASK_DESCRIPTION": selected['description'],
                        "DATA_CONTEXT": node.report.data_context
                    }
                    prompt = get_prompt("chart_caption", prompt_args)
                    
                    try:
                        client = OpenAI(
                            api_key=llm_kwargs.get("api_key"),
                            base_url=llm_kwargs.get("base_url")
                        )
                        
                        response = client.chat.completions.create(
                            model=llm_kwargs.get("model", "gpt-4o"),
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a data visualization expert. Your task is to analyze this chart and provide insight with the following information."
                                },
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/png;base64,{base64_image}"
                                            }
                                        }
                                    ]
                                }
                            ],
                            temperature=0.3
                        )
                        
                        # 处理响应
                        if isinstance(response, str):
                            caption = response.strip()
                        else:
                            caption = response.choices[0].message.content.strip()
                        
                        # 清理响应内容
                        clean_caption = self.clean_response(caption)
                        
                        print("\n🧹 清理后的说明文字:")
                        print("-" * 50)
                        print(clean_caption)
                        print("-" * 50)
                        
                        if clean_caption:  # 只有在有效的说明文字时才更新
                            # 更新图表说明
                            chart.caption = clean_caption
                            chart.needs_caption = False
                            
                            # 更新任务状态
                            for task in chapter.visualization_tasks:
                                if task['task_id'] == selected['task_id']:
                                    task['status'] = 'completed'
                                    task['caption_generated'] = True
                                    print(f"\n✅ 任务 '{selected['description']}' 的图表说明已生成，任务完成")
                                    break
                            
                            print("✅ 成功生成图表说明文字")
                        else:
                            print("\n❌ 生成的说明文字无效，跳过更新")
                            
                    except Exception as e:
                        print(f"\n❌ API 调用失败: {str(e)}")
                        traceback.print_exc()
                        
        except Exception as e:
            print(f"\n❌ 生成说明文字时出错: {str(e)}")
            traceback.print_exc()
            
        return [child_node]

# class GenerateCaptionAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("A7", "为图表生成说明文字", 
#                          [ReportGenerationState.CHAPTER_IN_PROGRESS])
    
#     def is_applicable(self, node: "MCTSNode") -> bool:
#         # 检查是否有选中的任务
#         selected = getattr(node, 'selected_task', None)
#         if not selected:
#             print("❌ 没有选中的任务")
#             return False
        
#         # 获取章节索引并检查其有效性
#         chapter_idx = selected.get('chapter_idx')
#         if chapter_idx is None:
#             print("❌ 选中的任务没有章节索引")
#             return False
        
#         if chapter_idx >= len(node.report.chapters):
#             print(f"❌ 无效的章节索引: {chapter_idx}")
#             return False
        
#         # 获取章节
#         chapter = node.report.chapters[chapter_idx]
        
#         # 检查任务状态是否为 needs_caption
#         task_id = selected.get('task_id')
#         if not task_id:
#             print("❌ 选中的任务没有 task_id")
#             return False
            
#         for task in chapter.visualization_tasks:
#             if task.get('task_id') == task_id:
#                 if task.get('status') == 'needs_caption':
#                     # 检查是否有图表需要生成说明文字
#                     for chart in getattr(chapter, 'charts', []):
#                         if chart.task_id == task_id:
#                             print(f"✅ 发现需要生成说明文字的图表")
#                             return True
                            
#                     print("❌ 找不到与任务关联的图表")
#                     return False
#                 else:
#                     print(f"❌ 任务 '{selected.get('description')}' 状态不是 needs_caption: {task.get('status')}")
#                     return False
                    
#         print(f"❌ 找不到任务 ID: {task_id}")
#         return False
    
#     def _get_image_base64(self, image_path: str) -> str:
#         """将图片转换为 base64 编码"""
#         try:
#             with Image.open(image_path) as img:
#                 # 将图片转换为 bytes
#                 img_byte_arr = io.BytesIO()
#                 img.save(img_byte_arr, format=img.format)
#                 img_byte_arr = img_byte_arr.getvalue()
#                 # 转换为 base64
#                 return base64.b64encode(img_byte_arr).decode('utf-8')
#         except Exception as e:
#             print(f"❌ 图片转换失败: {str(e)}")
#             return None

#     def clean_response(self, response: str) -> str:
#         """清理 API 返回的响应内容"""
#         # 如果响应包含完整的 HTML 文档，说明可能是错误的响应
#         if '<!doctype html>' in response.lower():
#             return ""
        
#         # 移除任何 HTML 标签
#         import re
#         clean_text = re.sub(r'<[^>]+>', '', response)
        
#         # 清理多余的空白字符
#         clean_text = ' '.join(clean_text.split())
        
#         return clean_text.strip()

#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         """为图表生成说明文字"""
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         try:
#             selected = getattr(node, 'selected_task', None)
#             chapter = child_node.report.chapters[selected['chapter_idx']]
            
#             # 为需要生成 caption 的图表生成说明文字
#             for chart in chapter.charts:
#                 if (chart.task_id == selected['task_id'] and 
#                     getattr(chart, 'needs_caption', False)):
                    
#                     print(f"\n📊 正在为图表生成说明文字...")
#                     print(f"📌 任务描述: {selected['description']}")
#                     print(f"📍 图表路径: {chart.url}")
                    
#                     # 获取图片的 base64 编码
#                     base64_image = self._get_image_base64(chart.url)
#                     if not base64_image:
#                         print("❌ 图片处理失败，跳过该图表")
#                         continue

#                     # 准备 prompt
#                     prompt_args = {
#                         "QUERY": node.original_query,
#                         "CHAPTER_TITLE": chapter.title,
#                         "CHART_TYPE": chart.chart_type,
#                         "TASK_DESCRIPTION": selected['description'],
#                         "DATA_CONTEXT": node.report.data_context
#                     }
#                     prompt = get_prompt("chart_caption", prompt_args)
#                     try:
#                         client = OpenAI(
#                             api_key=llm_kwargs.get("api_key"),
#                             base_url=llm_kwargs.get("base_url")
#                         )
            
#             response = client.chat.completions.create(
#                             model=llm_kwargs.get("model", "gpt-4o"),
#                 messages=[
#                                 {
#                                     "role": "system",
#                                     "content": "You are a data visualization expert. Your task is to analyze this chart and provide insight with the following information."
#                                 },
#                                 {
#                                     "role": "user",
#                                     "content": [
#                                         {"type": "text", "text": prompt},
#                                         {
#                                             "type": "image_url",
#                                             "image_url": {
#                                                 "url": f"data:image/png;base64,{base64_image}"
#                                             }
#                                         }
#                                     ]
#                                 }
#                 ],
#                 temperature=0.3
#             )
            
#                         # 处理响应
#                         if isinstance(response, str):
#                             caption = response.strip()
#                         else:
#             caption = response.choices[0].message.content.strip()
            
#                         # 清理响应内容
#                         clean_caption = self.clean_response(caption)
                        
#                         print("\n🧹 清理后的说明文字:")
#                         print("-" * 50)
#                         print(clean_caption)
#                         print("-" * 50)
                        
#                         if clean_caption:  # 只有在有效的说明文字时才更新
#                             # 更新图表说明
#                             chart.caption = clean_caption
#                             chart.needs_caption = False
                            
#                             # 更新任务状态
#                             for task in chapter.visualization_tasks:
#                                 if task['task_id'] == selected['task_id']:
#                                     task['status'] = 'completed'
#                                     task['caption_generated'] = True
#                                     print(f"\n✅ 任务 '{selected['description']}' 的图表说明已生成，任务完成")
#                                     break
                            
#                             print("✅ 成功生成图表说明文字")
#                         else:
#                             print("\n❌ 生成的说明文字无效，跳过更新")
        
#         except Exception as e:
#                         print(f"\n❌ API 调用失败: {str(e)}")
#             traceback.print_exc()
        
#         except Exception as e:
#             print(f"\n❌ 生成说明文字时出错: {str(e)}")
#             traceback.print_exc()
            
#         return [child_node]

class Captions2Summaries(DataStorytellingAction):
    def __init__(self):
        super().__init__("A6", "根据每个章节的Caption生成每个章节的总结")

    def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
        child_node = copy.deepcopy(node)
        child_node.parent_node = node
        child_node.parent_action = self
        child_node.depth = node.depth + 1
        
        try:
            # 遍历所有章节
            for chapter_idx, chapter in enumerate(child_node.report.chapters):
                print(f"\n📑 正在处理第 {chapter_idx + 1} 章: {chapter.title}")
                
                # 收集本章节所有图表及其说明
                visualization_tasks = []
                for task in chapter.visualization_tasks:
                    task_info = {
                        'description': task.get('task_description', ''),
                        'charts': []
                    }
                    
                    # 查找与任务关联的图表
                    for chart in getattr(chapter, 'charts', []):
                        if chart.task_id == task.get('task_id'):
                            task_info['charts'].append({
                                'caption': getattr(chart, 'caption', '无说明文字')
                            })
                    
                    visualization_tasks.append(task_info)
                
                # 准备 prompt
                prompt_args = {
                    "QUERY": node.original_query,
                    "CHAPTER_TITLE": chapter.title,
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
            
        except Exception as e:
            print(f"❌ 生成章节摘要时出错: {str(e)}")
            traceback.print_exc()
        
        return [child_node]

# class ReviseChapterTitleAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("R1", "修改章节标题", 
#                          [ReportGenerationState.ALL_OF_CHAPTERS_COMPLETED],
#                          ReportGenerationState.OPTIMIZED)
    
#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         """
#         R1 负责修改章节标题，使其更加合理、专业和吸引人
#         """
#         # ✅ 获取当前章节信息
#         selected_task = node.selected_task
#         chapter_idx = selected_task["chapter_idx"]
#         chapter = node.report.chapters[chapter_idx]
        
#         # ✅ 创建子节点
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         try:
#             # ✅ 获取章节摘要，如果没有，则使用图表说明
#             chapter_summary = chapter.summary if getattr(chapter, "summary", "") else ""
#             if not chapter_summary:
#                 chart_captions = [chart.caption for chart in chapter.charts if getattr(chart, "caption", "")]
#                 chapter_summary = " ".join(chart_captions) if chart_captions else "无摘要"
            
#             # ✅ 生成 LLM 提示词
#             prompt_args = {
#                 "QUERY": node.original_query,
#                 "CHAPTER_TITLE": chapter.title,
#                 "CHAPTER_SUMMARY": chapter_summary
#             }
#             prompt = get_prompt("revise_chapter_title", prompt_args)
            
#             print(f"正在修改章节 '{chapter.title}' 的标题...")
            
#             # ✅ 调用 LLM 生成新的章节标题
#             responses = call_openai(prompt, **llm_kwargs)
#             if responses:
#                 new_title = responses[0].strip()
#                 print(f"✓ 成功生成新标题: '{new_title}'")
                
#                 # ✅ 更新章节标题
#                 old_title = child_node.report.chapters[chapter_idx].title
#                 child_node.report.chapters[chapter_idx].title = new_title
#                 print(f"✓ 成功更新章节标题: '{old_title}' -> '{new_title}'")
#             else:
#                 print(f"✗ 修改章节标题失败: 没有收到有效响应")
        
#         except Exception as e:
#             print(f"✗ 修改章节标题时发生错误: {str(e)}")
#             import traceback
#             traceback.print_exc()
        
#         # ✅ 状态转换逻辑
#         child_node.node_type = ReportGenerationState.OPTIMIZED
        
#         return [child_node]  # ✅ 确保返回 `child_node`

# class ReviseNarrativeStrategyAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("R2", "调整报告叙事策略", 
#                          [ReportGenerationState.ALL_OF_CHAPTERS_COMPLETED], 
#                          ReportGenerationState.OPTIMIZED)
    
#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         """
#         R2 负责调整报告的叙事策略，重新排序章节
#         """
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         try:
#             # 准备章节信息
#             chapters_info = []
#             for i, chapter in enumerate(node.report.chapters):
#                 chapter_info = {
#                     "index": i,
#                     "title": chapter.title,
#                     "summary": chapter.summary if hasattr(chapter, 'summary') and chapter.summary else ""
#                 }
#                 chapters_info.append(chapter_info)
            
#             # 使用模板生成提示词
#             prompt_args = {
#                 "QUERY": node.original_query,
#                 "CHAPTERS": json.dumps(chapters_info, ensure_ascii=False, indent=2)
#             }
            
#             prompt = get_prompt("revise_narrative", prompt_args)
#             print("正在分析报告叙事策略...")
            
#             # 使用 call_openai 调用 LLM
#             responses = call_openai(prompt, **llm_kwargs)
            
#             if responses and len(responses) > 0:
#                 response_text = responses[0].strip()
#                 print(f"LLM 响应:\n{response_text}")
                
#                 try:
#                     # 尝试清理响应文本，移除可能的 markdown 标记
#                     if response_text.startswith("```json"):
#                         response_text = response_text.replace("```json", "").replace("```", "")
#                     response_text = response_text.strip()
                    
#                     # 解析 JSON
#                     result = json.loads(response_text)
                    
#                     # 验证 JSON 结构
#                     if not all(key in result for key in ["strategy", "strategy_reason", "chapter_order"]):
#                         raise ValueError("JSON 响应缺少必要的字段")
                    
#                     # 获取选择的叙事策略
#                     strategy = result.get("strategy", "")
#                     strategy_reason = result.get("strategy_reason", "")
#                     chapter_order = result.get("chapter_order", [])
                    
#                     print(f"✓ 选择的叙事策略: {strategy}")
#                     print(f"  原因: {strategy_reason}")
                    
#                     # 验证章节顺序
#                     if len(chapter_order) != len(node.report.chapters):
#                         raise ValueError(f"章节数量不匹配: 期望 {len(node.report.chapters)}, 实际 {len(chapter_order)}")
                    
#                     # 根据新顺序重排章节
#                     new_chapters = []
#                     for chapter_info in chapter_order:
#                         original_index = chapter_info["original_index"]
#                         if not isinstance(original_index, int):
#                             raise ValueError(f"无效的章节索引: {original_index}")
#                         if original_index < 0 or original_index >= len(node.report.chapters):
#                             raise ValueError(f"章节索引超出范围: {original_index}")
#                         new_chapters.append(copy.deepcopy(node.report.chapters[original_index]))
#                         print(f"  - 移动章节 '{chapter_info['title']}' 到新位置")
#                         print(f"    原因: {chapter_info['reason']}")
                    
#                     # 更新报告的章节顺序
#                     child_node.report.chapters = new_chapters
#                     child_node.report.narrative_strategy = result
#                     print("✓ 成功调整章节顺序")
                    
#                 except json.JSONDecodeError as e:
#                     print(f"✗ JSON 解析错误: {str(e)}")
#                     print(f"问题响应文本: {response_text}")
#                 except Exception as e:
#                     print(f"✗ 处理响应时发生错误: {str(e)}")
#             else:
#                 print("✗ 没有收到有效响应")
                
#         except Exception as e:
#             print(f"✗ 调整叙事策略时发生错误: {str(e)}")
#             import traceback
#             traceback.print_exc()
        
#         # 状态转换为 OPTIMIZED
#         child_node.node_type = ReportGenerationState.OPTIMIZED
        
#         return [child_node]

# class GenerateReportSummaryAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("R3", "生成报告摘要", 
#                          [ReportGenerationState.OPTIMIZED], 
#                          ReportGenerationState.FINALIZED)
    
#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         try:
#             # 收集所有章节的信息
#             chapters_info = []
#             for chapter in node.report.chapters:
#                 chapter_info = {
#                     "title": chapter.title,
#                     "summary": chapter.summary
#                 }
#                 chapters_info.append(chapter_info)
            
#             # 准备 prompt
#             prompt_args = {
#                 "QUERY": node.original_query,
#                 "CHAPTERS": json.dumps(chapters_info, ensure_ascii=False, indent=2)
#             }
            
#             prompt = get_prompt("report_summary", prompt_args)
            
#             # 调用 LLM 生成摘要
#             responses = call_openai(prompt, **llm_kwargs)
#             if not responses:
#                 print("❌ 没有收到有效响应")
#                 return [child_node]
            
#             # 解析 JSON 响应
#                 response_text = responses[0].strip()
#                     if response_text.startswith("```json"):
#                         response_text = response_text.replace("```json", "").replace("```", "")
#                     response_text = response_text.strip()
                    
#                     result = json.loads(response_text)
                    
#             # 分别保存摘要和总结
#             child_node.report.key_abstract = result["key_abstract"]  # 重点摘要
#             child_node.report.brief_conclusion = result["brief_conclusion"]  # 简要总结
            
#             # 更新状态
#             child_node.node_type = ReportGenerationState.FINALIZED
            
#                 except Exception as e:
#             print(f"❌ 生成报告摘要时出错: {str(e)}")
#             traceback.print_exc()
        
#         return [child_node]
    
# class FinalizedAction(DataStorytellingAction):
#     def __init__(self):
#         super().__init__("R5", "终止搜索，报告完成", 
#                          [ReportGenerationState.OPTIMIZED], 
#                          ReportGenerationState.FINALIZED)
    
#     def create_children_nodes(self, node: "MCTSNode", llm_kwargs: Dict[str, Any]) -> List["MCTSNode"]:
#         # 创建子节点
#         child_node = copy.deepcopy(node)
#         child_node.parent_node = node
#         child_node.parent_action = self
#         child_node.depth = node.depth + 1
        
#         # 状态转换为 FINALIZED
#         child_node.node_type = ReportGenerationState.FINALIZED
        
#         print("✓ 报告已完成，搜索终止")
        
#         return [child_node]
    
class ReportGenerationState(Enum):
    EMPTY = "Empty"  
    # 📌 初始状态：报告尚未开始处理，等待数据预处理

    QUERY2CHAPTERS = "Query2Chapters"
    # 📌 已定义章节结构：章节已经划分，但未开始生成具体内容

    CHAPTERS2TASKS = "Chapters2Tasks"
    # 📌 章节进行中：某个章节正在被处理（但章节未完成，且可能有多个章节未完成）

    TASKS2CHARTS = "Tasks2Charts"
    # 📌 部分章节生成完整内容

    REVISEVIS = "ReviseVis"

    CHARTS2CAPTIONS = "Charts2Captions"

    CAPTIONS2SUMMARIES = "Captions2Summaries"

    REVISECHAPTERSTITLES = "ReviseChaptersTitles"
    # 📌 整体报告优化完成：调整了叙事逻辑，所有章节信息结构优化完毕

    REVISECHAPTERSORDERS = "ReviseChaptersOrders"

    REVISEREPORTSMODULES = "ReviseReportsModules"

    ABSTRACTANDCONCLUSION = "Abstract&Conclusion"

    FINALIZED = "Finalized"
    # 📌 最终报告生成完成：搜索终止，报告完成，可以导出



    NODE_TYPE_TO_VALID_ACTIONS = {
        ReportGenerationState.EMPTY: [
            Query2Chapters
        ],
        ReportGenerationState.Query2Chapters: [
            Chapters2Tasks,
            Tasks2Charts
        ],
        ReportGenerationState.Chapters2Tasks: [
            Tasks2Charts
        ],

        ReportGenerationState.Tasks2Charts: [
            ReviseVis,
            Charts2Captions
        ],
        ReportGenerationState.ReviseVis: [
            Charts2Captions
        ],
        ReportGenerationState.Charts2Captions: [
            Captions2Summaries
        ],
        ReportGenerationState.FINALIZED: []  # 终止状态
    }

    def save_chart(self, node: MCTSNode, chart_data: dict) -> str:
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

