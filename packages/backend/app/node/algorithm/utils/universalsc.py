import json, os
import re
from typing import List, Dict, Any, Callable, Optional
from storyteller.llm_call.openai_llm import call_openai  # 假设你有类似的调用封装
from storyteller.llm_call.prompt_factory import get_prompt

def generate_diverse_responses(
    prompt_template: str, 
    prompt_params: Dict[str, Any],
    llm_kwargs: Dict[str, Any], 
    n: int = 6,
    response_processor: Optional[Callable] = None
) -> List[Any]:
    """
    通用多样性响应生成函数，可用于不同类型的响应生成
    
    参数:
        prompt_template: 提示词模板名称
        prompt_params: 提示词参数
        llm_kwargs: LLM调用参数
        n: 生成的响应数量
        response_processor: 自定义的响应处理函数
    
    返回:
        处理后的响应列表
    """
    # 使用模板生成提示词
    prompt = get_prompt(prompt_template, prompt_params)
    
    # 创建临时参数，去掉n参数
    llm_kwargs_temp = llm_kwargs.copy()
    if 'n' in llm_kwargs_temp:
        del llm_kwargs_temp['n']
    
    # 存储所有响应
    all_raw_responses = []
    
    # 使用config中的temperature，如果未指定则使用默认值0.7
    base_temperature = llm_kwargs_temp.get('temperature', 0.7)
    
    # 多次独立调用API以获取多个响应
    print(f"🔄 通过 {n} 次独立API调用获取多样化响应")
    
    for i in range(n):
        # 为每次调用添加微小扰动以增加多样性
        temp_kwargs = llm_kwargs_temp.copy()
        # 在基础温度上增加少量随机扰动
        temp_variation = (i % 3 - 1) * 0.05  # -0.05, 0, +0.05 循环变化
        temp_kwargs['temperature'] = max(0.1, min(1.0, base_temperature + temp_variation))
        
        print(f"  调用 {i+1}/{n} (temperature={temp_kwargs['temperature']:.2f})")
        
        try:
            # 单次调用API获取一个响应
            response = call_openai(prompt, **temp_kwargs)
            if response and len(response) > 0:
                all_raw_responses.append(response[0])
                print(f"  ✓ 获取到响应 (长度: {len(response[0])})")
            else:
                print(f"  ✗ 未获取到有效响应")
        except Exception as e:
            print(f"  ✗ API调用失败: {str(e)}")
            continue
    
    # 输出汇总信息
    print(f"获取到 {len(all_raw_responses)} 个原始响应")
    
    # 处理响应
    if response_processor:
        # 使用自定义处理器
        processed_responses = []
        for i, r in enumerate(all_raw_responses):
            try:
                processed = response_processor(r)
                if processed:
                    processed_responses.append(processed)
                    print(f"响应 {i+1}: 成功处理")
                else:
                    print(f"响应 {i+1}: 处理结果为空，已跳过")
            except Exception as e:
                print(f"响应 {i+1}: 处理异常 - {str(e)}")
                continue
        return processed_responses
    else:
        # 默认处理：清理JSON并解析
        processed_responses = []
        for i, r in enumerate(all_raw_responses):
            try:
                cleaned = clean_json_response(r)
                parsed = json.loads(cleaned)
                processed_responses.append(parsed)
                print(f"响应 {i+1}: 成功解析JSON")
            except Exception as e:
                print(f"响应 {i+1}: 处理异常 - {str(e)}")
                continue
        return processed_responses


def clean_json_response(response: str) -> str:
    """
    清理 LLM 返回的 JSON 响应，移除 Markdown 代码块标记。
    """
    response = re.sub(r'^```(?:json)?\s*', '', response)
    response = re.sub(r'\s*```$', '', response)
    return response.strip()


def build_clustering_prompt(
    responses: List[Any],
    clustering_config: Dict[str, Any],
    context_info: Dict[str, Any]
) -> str:
    """
    构建聚类提示词，适用于各种类型的响应聚类
    
    参数:
        responses: 响应列表
        clustering_config: 聚类配置(包含响应格式化函数、聚类标准等)
        context_info: 上下文信息(查询、数据上下文等)
    
    返回:
        聚类提示词
    """
    # 获取格式化函数，或使用默认格式化
    format_func = clustering_config.get("format_func", lambda x, i: f"方案{i+1}: {json.dumps(x, ensure_ascii=False)}")
    
    # 格式化响应
    responses_str = "\n\n".join([
        format_func(resp, i) for i, resp in enumerate(responses)
    ])
    
    # 获取聚类标准
    similarity_criteria = clustering_config.get("similarity_criteria", 
        "- 如果它们分析相同的数据维度或特征\n"
        "- 如果它们采用相似的分析结构或框架\n"
        "- 如果它们关注相同的数据关系或模式"
    )
    
    difference_criteria = clustering_config.get("difference_criteria",
        "- 如果它们关注完全不同的数据维度\n"
        "- 如果它们使用不同的分析框架或逻辑\n"
        "- 如果它们解决查询的不同方面"
    )
    
    # 明确可用的索引范围
    valid_indices = list(range(len(responses)))
    max_index = len(responses) - 1
    
    # 构建提示词
    prompt = f"""
您正在评估几个候选{clustering_config.get('item_type', '方案')}，它们都是针对同一数据分析查询的。

=== 候选{clustering_config.get('item_type', '方案')} ===
{responses_str}

=== 任务信息 ===
查询: {context_info.get('query', '')}
{f"数据上下文: {context_info.get('data_context', '')}" if 'data_context' in context_info else ''}

### 指引:

您的任务是将这些{clustering_config.get('item_type', '方案')}分组成不同的、互不重叠的聚类，基于它们的基本分析方法。这一点非常重要:

1. 每个方案必须且只能属于一个聚类。
2. 两个方案应该在同一聚类中，当且仅当它们代表本质上相同的分析框架，即使使用不同的措辞。
3. 聚类应该代表根本不同的分析方法或结构。

相似{clustering_config.get('item_type', '方案')}的标准(应归为同一聚类):
{similarity_criteria}

不同{clustering_config.get('item_type', '方案')}的标准(应归为不同聚类):
{difference_criteria}

### 重要约束:
- 每个响应索引(0, 1, 2等)必须出现在且仅出现在一个聚类中
- 有效的响应索引仅为: {valid_indices} (从0到{max_index})
- 不要创建在response_indices上有重叠的聚类
- 确保所有响应索引都包含在恰好一个聚类中
- 不要使用任何大于{max_index}或小于0的索引

### 输出:
请返回如下JSON:
```json
{{
  "type": "multiple",
  "results": [
    {{
      "cluster_id": 1,
      "response_indices": [0, 2],  // 每个响应属于且只属于一个聚类
      "top_index": 0,              // 该聚类中最具代表性的响应
      "content": object            // 代表性响应的内容(视响应类型而定)
    }},
    {{
      "cluster_id": 2, 
      "response_indices": [1, 3],  // 注意: 与其他聚类的索引没有重叠
      "top_index": 1,
      "content": object
    }}
  ]
}}
```

请记住：最重要的规则是每个响应索引必须出现在且仅出现在一个聚类中。没有响应应该在多个聚类中，每个响应必须在某个聚类中。

请记住：您只能使用0到{max_index}之间的索引(包括0和{max_index})。不要使用任何超出此范围的索引！

请仅返回JSON输出。
    """
    return prompt


def run_universal_self_consistency(
    responses_config: Dict[str, Any],
    clustering_config: Dict[str, Any],
    context_info: Dict[str, Any],
    llm_kwargs: Dict[str, Any],
    response_processor: Optional[Callable] = None,
    content_extractor: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    通用USC流程，适用于各种类型的响应生成和聚类
    
    参数:
        responses_config: 响应生成配置
        clustering_config: 聚类配置
        context_info: 上下文信息
        llm_kwargs: LLM调用参数
        response_processor: 响应处理函数
        content_extractor: 从聚类结果中提取内容的函数
    
    返回:
        聚类结果列表
    """
    from storyteller.llm_call.openai_llm import call_openai
    
    # 使用配置生成多样化响应
    prompt_template = responses_config.get("prompt_template")
    prompt_params = responses_config.get("prompt_params", {})
    n = responses_config.get("n", 6)
    
    # 生成响应
    responses = generate_diverse_responses(
        prompt_template=prompt_template,
        prompt_params=prompt_params,
        llm_kwargs=llm_kwargs,
        n=n,
        response_processor=response_processor
    )
    
    print(f"📋 共获取到 {len(responses)} 个有效响应")
    
    # 如果响应数量不够，无法聚类
    if len(responses) < 2:
        print("⚠️ 响应数量不足，无法执行聚类")
        if responses:
            # 创建一个单一聚类
            return [{
                "cluster_id": 1,
                "response_indices": [0],
                "top_index": 0,
                "content": responses[0]
            }]
        return []
    
    # 构建聚类提示词
    usc_prompt = build_clustering_prompt(
        responses=responses,
        clustering_config=clustering_config,
        context_info=context_info
    )
    
    print(f"🔍 生成聚类分析提示词，长度: {len(usc_prompt)} 字符")
    
    # 进行聚类分析
    usc_response = call_openai(usc_prompt, **llm_kwargs)
    
    # 清理响应
    cleaned = clean_json_response(usc_response[0])
    
    try:
        # 解析聚类结果
        usc_result = json.loads(cleaned)
        clusters = usc_result.get("results", [])
        
        # 使用内容提取器或默认方法提取内容
        if content_extractor:
            for cluster in clusters:
                top_index = cluster.get("top_index", 0)
                if 0 <= top_index < len(responses):
                    cluster["content"] = content_extractor(responses[top_index])
        else:
            # 默认：直接使用top_index对应的响应作为内容
            for cluster in clusters:
                top_index = cluster.get("top_index", 0)
                if 0 <= top_index < len(responses):
                    cluster["content"] = responses[top_index]
        
        print(f"✅ 成功聚类为 {len(clusters)} 组")
        return clusters
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {str(e)}")
        # 如果聚类失败，但有响应，返回每个响应作为单独的聚类
        fallback_clusters = []
        for i, resp in enumerate(responses):
            fallback_clusters.append({
                "cluster_id": i + 1,
                "response_indices": [i],
                "top_index": i,
                "content": resp
            })
        print(f"⚠️ 聚类失败，使用备选方案，创建 {len(fallback_clusters)} 个单响应聚类")
        return fallback_clusters


if __name__ == "__main__":
    query = "Analyze the difference between the customers"

    json_path = os.path.join("storyteller", "dataset", "data_context.json")
    with open(json_path, 'r', encoding='utf-8') as f:
                            data_context = json.load(f)
    
    # 确保data_context是字符串类型
    if isinstance(data_context, dict):
        data_context = json.dumps(data_context, ensure_ascii=False)
    
    print(f"加载数据上下文: {json_path}")

    llm_kwargs = {
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    # 从配置文件读取API信息
    config_path = os.path.join("storyteller", "config", "config.yaml")
    if os.path.exists(config_path):
        import yaml
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if 'llm_kwargs' in config:
                    # 更新llm_kwargs，使用配置文件中的设置
                    llm_kwargs.update(config['llm_kwargs'])
                    print(f"✓ 成功从配置文件加载API设置")
        except Exception as e:
            print(f"✗ 读取配置文件失败: {str(e)}")

    print(">>> 正在运行 Universal Self-Consistency 流程...")
    # 使用较小的n值，避免生成过多方案导致超时
    clusters = run_universal_self_consistency(
        responses_config={
            "prompt_template": "Query2Chapters",
            "prompt_params": {
                "QUERY": query,
                "DATA_CONTEXT": data_context
            },
            "n": 4
        },
        clustering_config={
            "item_type": "章节结构",
            "format_func": lambda resp, i: f"方案{i+1}: {resp.get('chapters', [])}",
            "similarity_criteria": "- 使用相似或重新措辞但覆盖相同分析维度的章节\n- 相同分析主题的细微重新排序\n- 相同通用主题的不同特定性级别",
            "difference_criteria": "- 完全不同的分析维度\n- 通过不同的逻辑框架构建分析\n- 解决查询的不同方面(例如，一个专注于人口统计，另一个专注于时间模式)"
        },
        context_info={
            "query": query,
            "data_context": data_context
        },
        llm_kwargs=llm_kwargs
    )

    print("\n=== USC 聚类结果（章节结构） ===")
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id", "未知")
        indices = cluster.get("response_indices", [])
        top_index = cluster.get("top_index", None)
        chapters = cluster.get("content", [])

        print(f"📘 Cluster {cluster_id}:")
        print(f"  来源 response index: {indices}")
        print(f"  Top response: {top_index}")
        print(f"  章节结构: {chapters}\n")