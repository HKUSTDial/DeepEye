import json
import copy
import traceback
import re
from typing import Dict, List, Any, Optional, Tuple, Callable
from storyteller.llm_call.openai_llm import call_openai
from storyteller.llm_call.prompt_factory import get_prompt
from storyteller.algorithm.utils.universalsc import run_universal_self_consistency
from storyteller.algorithm.mcts_node import Chapter, ReportGenerationState

def process_response(response_text: str, action_type: str) -> Any:
    """处理LLM响应，根据不同的行动类型进行处理
    
    参数:
        response_text: LLM返回的原始响应
        action_type: 行动类型，如"chapters"或"tasks"
        
    返回:
        处理后的响应对象
    """
    try:
        if action_type == "chapters":
            # 处理章节响应
            # 清理响应文本，提取JSON部分
            # 移除Markdown代码块标记
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            # 解析JSON
            return json.loads(response_text)
        elif action_type == "tasks":
            # 处理任务响应
            # 清理响应文本，提取JSON部分
            # 移除Markdown代码块标记
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            # 解析JSON
            return json.loads(response_text)
        else:
            print(f"⚠️ 未知的行动类型: {action_type}")
            return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {str(e)}")
        print(f"原始响应: {response_text}")
        return None
    except Exception as e:
        print(f"❌ 处理响应时出错: {str(e)}")
        traceback.print_exc()
        return None

def get_clustering_config(action_type: str) -> Dict[str, Any]:
    """获取不同行动类型的聚类配置
    
    参数:
        action_type: 行动类型，如"chapters"或"tasks"
        
    返回:
        聚类配置字典
    """
    if action_type == "chapters":
        return {
            "item_type": "章节结构方案",
            "response_key": "chapters",
            "cluster_key": "chapters",
            "similarity_criteria": "- 相似或重新措辞但覆盖相同分析维度的章节\n- 相同分析主题的细微重新排序",
            "difference_criteria": "- 完全不同的分析维度\n- 通过不同的逻辑框架构建分析"
        }
    elif action_type == "tasks":
        return {
            "item_type": "整体任务方案",
            "response_key": "chapters",  # 原始响应中的章节键
            "cluster_key": "chapters",   # 聚类结果应使用的键
            "similarity_criteria": "- 对相同章节分配了类似数据分析任务\n- 使用相似的可视化类型和设计策略\n- 关注相同的数据特征或维度",
            "difference_criteria": "- 对章节分配了不同的数据分析任务\n- 使用不同的可视化类型和设计策略\n- 关注不同的数据特征或维度"
        }
    elif action_type == "transition":
        return {
            "item_type": "过渡文本方案",
            "response_key": "transitions",
            "cluster_key": "transitions",
            "similarity_criteria": "- 相似的过渡逻辑\n- 强调相同的章节连接点\n- 采用类似的写作风格",
            "difference_criteria": "- 不同的过渡逻辑\n- 强调不同的章节连接点\n- 采用不同的写作风格"
        }
    elif action_type == "narrative":
        return {
            "item_type": "叙事策略方案",
            "response_key": "chapter_order",
            "cluster_key": "chapter_order",
            "similarity_criteria": "- 相似的章节排序逻辑\n- 相似的叙事框架",
            "difference_criteria": "- 不同的章节排序逻辑\n- 不同的叙事框架"
        }
    else:
        print(f"⚠️ 未知的行动类型: {action_type}")
        return {
            "item_type": "方案",
            "response_key": "items",
            "cluster_key": "items",
            "similarity_criteria": "- 内容相似但表述不同\n- 关注相同的维度",
            "difference_criteria": "- 内容截然不同\n- 关注不同的维度"
        }

def format_responses_for_clustering(responses: List[Any], action_type: str) -> List[Dict[str, Any]]:
    """格式化响应用于聚类
    
    参数:
        responses: 生成的响应列表
        action_type: 行动类型，如"chapters"或"tasks"
        
    返回:
        格式化后的响应列表
    """
    formatted_responses = []
    config = get_clustering_config(action_type)
    response_key = config.get("response_key", "")
    
    if action_type == "tasks":
        # 对于任务方案，将整个响应作为一个整体方案处理
        for i, response in enumerate(responses):
            if isinstance(response, dict) and response_key in response:
                formatted_responses.append({
                    "index": i,
                    "content": response  # 传递整个响应，包含所有章节和任务
                })
            else:
                print(f"⚠️ 响应 {i} 格式不正确，跳过")
    else:
        # 其他类型使用原有逻辑
        for i, response in enumerate(responses):
            if isinstance(response, dict) and response_key in response:
                formatted_responses.append({
                    "index": i,
                    "content": response[response_key]
                })
            else:
                print(f"⚠️ 响应 {i} 格式不正确，跳过")
    
    return formatted_responses

def build_clustering_prompt(formatted_responses: List[Dict[str, Any]], action_type: str, **kwargs) -> str:
    """构建聚类提示
    
    参数:
        formatted_responses: 格式化后的响应列表
        action_type: 行动类型，如"chapters"或"tasks"
        **kwargs: 其他参数，包括QUERY和DATA_CONTEXT
        
    返回:
        聚类提示字符串
    """
    config = get_clustering_config(action_type)
    
    query = kwargs.get("QUERY", "未提供查询")
    data_context = kwargs.get("DATA_CONTEXT", "未提供数据上下文")
    
    # 根据类型调整提示内容
    if action_type == "tasks":
        # 对于任务方案的特定提示
        response_contents = []
        for i, resp in enumerate(formatted_responses):
            # 为每个整体任务方案创建更友好的摘要
            resp_content = resp["content"]
            chapters = resp_content.get("chapters", [])
            
            chapters_summary = []
            for chapter in chapters:
                chapter_title = chapter.get("title", "未命名章节")
                task_count = len(chapter.get("tasks", []))
                task_types = set()
                for task in chapter.get("tasks", []):
                    chart_types = task.get("chart_type", [])
                    if isinstance(chart_types, list) and chart_types:
                        task_types.add(chart_types[0])
                    elif isinstance(chart_types, str):
                        task_types.add(chart_types)
                
                chapters_summary.append(f"  - 章节「{chapter_title}」: {task_count}个任务, 图表类型: {', '.join(task_types)}")
            
            summary = f"方案索引: {resp['index']}\n章节和任务概况:\n" + "\n".join(chapters_summary)
            response_contents.append(summary)
        
        # 构建特定于任务方案的提示
        prompt = f"""
你是一位专业的数据分析和可视化专家。请帮助我对多个整体任务方案进行聚类分析。

# 用户查询
{query}

# 数据上下文
{data_context}

# 候选整体任务方案
以下是多个候选整体任务方案的概况，每个方案都包含多个章节及其任务:

{chr(10).join(response_contents)}

# 聚类标准
请根据以下标准对候选整体任务方案进行聚类:

## 相似性标准（同一聚类）
{config['similarity_criteria']}

## 差异性标准（不同聚类）
{config['difference_criteria']}

# 任务
1. 分析每个候选整体任务方案的章节分配和任务特点
2. 根据相似性标准将相似的整体任务方案分组到同一聚类
3. 确保不同聚类之间具有明显的差异
4. 为每个聚类提供一个唯一的ID和简短描述
5. 从每个聚类中选择最具代表性的整体任务方案

# 输出格式
请以JSON格式输出结果，包含以下结构:
```json
{{
  "clusters": [
    {{
      "cluster_id": "唯一聚类ID",
      "description": "聚类简短描述",
      "indices": [候选方案的索引数组],
      "best_index": 最优方案的索引,
      "reason": "选择该方案作为最优的原因"
    }}
    // 更多聚类...
  ]
}}
```

注意:
- 每个候选整体任务方案必须且只能属于一个聚类
- 聚类数量应根据内容差异自然确定，不需要强制指定
- 请确保选择的最优方案(best_index)存在于该聚类的indices数组中

请确保输出为有效的JSON格式。
"""
    else:
        # 原有的通用提示
        prompt = f"""
你是一位专业的数据分析和聚类专家。请帮助我对多个{config['item_type']}进行聚类分析。

# 用户查询
{query}

# 数据上下文
{data_context}

# 候选{config['item_type']}
以下是多个候选{config['item_type']}，每个都有索引和内容:
{json.dumps(formatted_responses, ensure_ascii=False, indent=2)}

# 聚类标准
请根据以下标准对候选{config['item_type']}进行聚类:

## 相似性标准（同一聚类）
{config['similarity_criteria']}

## 差异性标准（不同聚类）
{config['difference_criteria']}

# 任务
1. 分析每个候选{config['item_type']}的内容和结构
2. 根据相似性标准将相似的{config['item_type']}分组到同一聚类
3. 确保不同聚类之间具有明显的差异
4. 为每个聚类提供一个唯一的ID和简短描述
5. 从每个聚类中选择最具代表性的内容

# 输出格式
请以JSON格式输出结果，包含以下结构:
```json
{{
  "clusters": [
    {{
      "cluster_id": "唯一聚类ID",
      "description": "聚类简短描述",
      "indices": [候选方案的索引数组],
      "{config['cluster_key']}": [代表性内容]
    }},
    // 更多聚类...
  ]
}}
```

注意:
- 每个候选{config['item_type']}必须且只能属于一个聚类
- 聚类数量应根据内容差异自然确定，不需要强制指定
- 代表性内容应该是聚类中最清晰、最全面的内容

请确保输出为有效的JSON格式。
"""
    
    return prompt

def cluster_responses(formatted_responses: List[Dict[str, Any]], action_type: str, llm_kwargs: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
    """对响应进行聚类
    
    参数:
        formatted_responses: 格式化后的响应列表
        action_type: 行动类型，如"chapters"或"tasks"
        llm_kwargs: LLM调用参数
        **kwargs: 其他参数
        
    返回:
        聚类结果列表
    """
    # 构建聚类提示
    prompt = build_clustering_prompt(formatted_responses, action_type, **kwargs)
    
    # 调用LLM进行聚类
    responses = call_openai(prompt, **llm_kwargs)
    if not responses:
        print(f"❌ 聚类时没有收到有效响应")
        return []
    
    # 处理聚类结果
    try:
        response_text = responses[0]
        print(f"收到原始聚类响应: \n{response_text}...")  # 打印前100个字符用于调试
        
        # 增强的JSON提取
        # 1. 尝试查找JSON代码块
        json_pattern = r'```(?:json)?\s*({[\s\S]*?})\s*```'
        json_matches = re.findall(json_pattern, response_text)
        
        if json_matches:
            # 使用第一个找到的JSON块
            json_text = json_matches[0]
            print(f"从响应中提取到JSON块，长度: {len(json_text)}")
        else:
            # 如果没有找到JSON代码块，尝试寻找可能的JSON对象
            curly_pattern = r'({[\s\S]*})'
            curly_matches = re.findall(curly_pattern, response_text)
            
            if curly_matches:
                potential_jsons = []
                for match in curly_matches:
                    try:
                        # 尝试解析每个潜在的JSON
                        json.loads(match)
                        potential_jsons.append(match)
                    except:
                        pass
                
                if potential_jsons:
                    # 使用找到的最长的有效JSON
                    json_text = max(potential_jsons, key=len)
                    print(f"从响应中提取到可能的JSON对象，长度: {len(json_text)}")
                else:
                    # 如果没有找到有效的JSON，回退到原始清理方法
                    json_text = response_text.replace("```json", "").replace("```", "").strip()
                    print("未找到明确的JSON块，使用清理后的完整响应")
            else:
                # 如果没有找到任何花括号，回退到原始清理方法
                json_text = response_text.replace("```json", "").replace("```", "").strip()
                print("未找到任何JSON格式内容，使用清理后的完整响应")
        
        # 尝试解析提取的JSON文本
        clustering_result = json.loads(json_text)
        
        # 提取聚类
        if "clusters" in clustering_result:
            clusters = clustering_result["clusters"]
            print(f"成功解析到 {len(clusters)} 个聚类")
            
            # 特殊处理任务聚类结果
            if action_type == "tasks":
                # 对于任务方案，需要从原始响应中提取完整的任务方案
                for cluster in clusters:
                    if "best_index" in cluster:
                        best_index = cluster["best_index"]
                        # 查找这个索引对应的原始响应
                        for resp in formatted_responses:
                            if resp["index"] == best_index:
                                # 将完整的原始响应放入聚类结果中
                                cluster["chapters"] = resp["content"]["chapters"]
                                print(f"为聚类 {cluster.get('cluster_id', 'unknown')} 应用最优方案 (索引: {best_index})")
                                break
                    else:
                        # 如果没有指定best_index，使用第一个索引
                        indices = cluster.get("indices", [])
                        if indices:
                            best_index = indices[0]
                            for resp in formatted_responses:
                                if resp["index"] == best_index:
                                    cluster["chapters"] = resp["content"]["chapters"]
                                    print(f"为聚类 {cluster.get('cluster_id', 'unknown')} 应用第一个方案 (索引: {best_index})")
                                    break
            
            return clusters
        else:
            print(f"❌ 聚类结果中没有找到clusters键")
            return []
    except json.JSONDecodeError as e:
        print(f"❌ 聚类结果JSON解析错误: {str(e)}")
        print(f"原始响应: {response_text}")
        
        # 尝试更灵活的方式提取JSON
        try:
            # 使用正则表达式查找以"clusters"开始的JSON数组部分
            clusters_pattern = r'"clusters"\s*:\s*(\[[\s\S]*?\])'
            clusters_match = re.search(clusters_pattern, response_text)
            
            if clusters_match:
                clusters_text = "{" + f'"clusters":{clusters_match.group(1)}' + "}"
                clusters_json = json.loads(clusters_text)
                print(f"使用正则表达式成功提取clusters部分")
                
                # 如果是任务聚类，需要额外处理
                if action_type == "tasks":
                    for cluster in clusters_json["clusters"]:
                        if "best_index" in cluster:
                            best_index = cluster["best_index"]
                            for resp in formatted_responses:
                                if resp["index"] == best_index:
                                    cluster["chapters"] = resp["content"]["chapters"]
                                    break
                
                return clusters_json["clusters"]
        except Exception as nested_e:
            print(f"二次尝试解析也失败: {str(nested_e)}")
        
        return []
    except Exception as e:
        print(f"❌ 处理聚类结果时出错: {str(e)}")
        traceback.print_exc()
        return []

def create_fallback_node(node, action, depth_increment=1):
    """创建后备节点，用于错误处理情况
    
    参数:
        node: 原始节点
        action: 父行动
        depth_increment: 深度增量
        
    返回:
        后备节点
    """
    fallback_node = copy.deepcopy(node)
    fallback_node.parent_node = node
    fallback_node.parent_action = action
    fallback_node.depth = node.depth + depth_increment
    
    # 设置节点状态
    if action.__class__.__name__ == "Query2Chapters":
        fallback_node.node_type = ReportGenerationState.a1
    elif action.__class__.__name__ == "Chapters2Tasks":
        fallback_node.node_type = ReportGenerationState.a2
    
    return fallback_node

def generate_diverse_responses(prompt: str, llm_kwargs: Dict[str, Any], n: int = 4) -> List[Any]:
    """生成多样化的响应
    
    参数:
        prompt: 提示字符串
        llm_kwargs: LLM调用参数
        n: 生成响应的数量
        
    返回:
        处理后的响应列表
    """
    # 复制LLM参数以便修改
    llm_kwargs_copy = llm_kwargs.copy()
    
    responses = []
    for i in range(n):
        # 为每次生成调整温度参数
        llm_kwargs_copy['temperature'] = 0.3 + (i * 0.2)  # 0.3, 0.5, 0.7, 0.9
        
        print(f"🔄 生成响应 {i+1}/{n} (温度: {llm_kwargs_copy['temperature']})")
        
        # 调用LLM生成响应
        response_texts = call_openai(prompt, **llm_kwargs_copy)
        if not response_texts:
            print(f"⚠️ 生成 {i+1} 没有收到有效响应")
            continue
        
        response_text = response_texts[0]
        
        try:
            # 清理响应文本，提取JSON部分
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            # 解析JSON
            response_json = json.loads(response_text)
            responses.append(response_json)
            
            print(f"✅ 生成 {i+1} 成功")
        except json.JSONDecodeError as e:
            print(f"❌ 生成 {i+1} JSON解析错误: {str(e)}")
            print(f"原始响应: {response_text}")
        except Exception as e:
            print(f"❌ 生成 {i+1} 处理出错: {str(e)}")
    
    return responses

def unified_generation_framework(node, action, llm_kwargs: Dict[str, Any], 
                               action_type: str, 
                               prompt_generator: Callable, 
                               node_applier: Callable,
                               n: int = 4, 
                               **kwargs) -> List[Any]:
    """统一的生成框架，用于生成和聚类多样本
    
    参数:
        node: 当前节点
        action: 行动对象
        llm_kwargs: LLM调用参数
        action_type: 行动类型，如"chapters"或"tasks"
        prompt_generator: 提示生成函数，接收节点和其他参数，返回提示字符串
        node_applier: 节点应用函数，接收节点、聚类结果和其他参数，返回更新后的节点
        n: 生成样本数量
        **kwargs: 其他参数
        
    返回:
        子节点列表
    """
    try:
        # 获取必要的参数
        query = node.report.clarified_query if node.report.clarified_query else node.report.original_query
        data_context = node.report.data_context
        
        print(f"🔍 正在生成{action_type}...")
        
        # 生成prompt
        prompt = prompt_generator(node, **kwargs)
        
        # 检查是否应该使用UniversalSC方法
        if action_type == "chapters" and hasattr(node.report, "use_usc") and node.report.use_usc:
            print("🔄 使用UniversalSC方法生成章节...")
            clusters = run_universal_self_consistency(query, data_context, llm_kwargs, n=n)
            print(f"✅ 完成章节聚类，得到 {len(clusters)} 个聚类")
        else:
            # 生成多样化响应
            responses = generate_diverse_responses(prompt, llm_kwargs, n=n)
            print(f"✅ 生成了 {len(responses)} 个有效响应")
            
            if not responses:
                print("⚠️ 没有生成任何有效响应，返回后备节点")
                return [create_fallback_node(node, action)]
            
            # 格式化响应用于聚类
            formatted_responses = format_responses_for_clustering(responses, action_type)
            print(f"✅ 格式化了 {len(formatted_responses)} 个响应用于聚类")
            
            if len(formatted_responses) < 2:
                print("⚠️ 可聚类的响应数量不足，使用单一响应")
                # 如果只有一个有效响应，直接使用它
                if formatted_responses:
                    if action_type == "tasks":
                        # 对于任务，直接使用完整的响应
                        response_idx = formatted_responses[0]["index"]
                        content = formatted_responses[0]["content"]
                        
                        # 创建一个聚类结构
                        clusters = [{
                            "cluster_id": "cluster_1",
                            "description": "唯一任务方案",
                            "indices": [response_idx],
                            "chapters": content["chapters"]
                        }]
                    else:
                        # 其他类型使用原有逻辑
                        config = get_clustering_config(action_type)
                        response_idx = formatted_responses[0]["index"]
                        content = formatted_responses[0]["content"]
                        
                        clusters = [{
                            "cluster_id": "cluster_1",
                            config.get("cluster_key", "items"): content
                        }]
                else:
                    print("❌ 没有可用的响应，返回后备节点")
                    return [create_fallback_node(node, action)]
            else:
                # 对响应进行聚类
                # 添加查询和数据上下文到聚类参数
                clustering_kwargs = {
                    "QUERY": query,
                    "DATA_CONTEXT": data_context,
                    **kwargs
                }
                
                clusters = cluster_responses(formatted_responses, action_type, llm_kwargs, **clustering_kwargs)
                print(f"✅ 聚类完成，得到 {len(clusters)} 个聚类")
        
        if not clusters:
            print("⚠️ 没有生成任何有效聚类，返回后备节点")
            return [create_fallback_node(node, action)]
        
        # 创建子节点
        nodes = []
        for cluster_idx, cluster in enumerate(clusters):
            # 使用节点应用函数将聚类结果应用到节点
            child_nodes = node_applier(node, action, cluster, **kwargs)
            if child_nodes:
                nodes.extend(child_nodes)
                print(f"✅ 成功应用聚类 {cluster_idx+1}/{len(clusters)}")
            else:
                print(f"⚠️ 应用聚类 {cluster_idx+1}/{len(clusters)} 失败")
        
        if not nodes:
            print("⚠️ 没有生成任何有效节点，返回后备节点")
            return [create_fallback_node(node, action)]
            
        return nodes
    
    except Exception as e:
        print(f"❌ 统一生成框架出错: {str(e)}")
        traceback.print_exc()
        return [create_fallback_node(node, action)] 