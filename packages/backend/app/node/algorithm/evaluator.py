import json
import re
import traceback
import os
from storyteller.llm_call.openai_llm import call_openai
from storyteller.llm_call.prompt_factory import get_prompt
from typing import Dict, Any

def extract_json_from_text(text):
    """从文本中提取JSON对象"""
    try:
        # 首先尝试直接将整个文本解析为JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # 如果失败，尝试查找JSON块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                return json.loads(json_str)
            except:
                pass
                
        # 尝试查找括号包围的JSON对象
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
                
        print(f"❌ 无法从文本中提取JSON: {text[:100]}...")
        return None

def get_prompt_content(template_name, template_args):
    """直接读取模板文件并替换其中的变量，避免Python的字符串格式化问题"""
    # 获取模板文件路径
    template_path = os.path.join("storyteller", "templates", f"{template_name}.txt")
    
    # 读取模板内容
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except Exception as e:
        print(f"❌ 读取模板文件失败: {str(e)}")
        return None
    
    # 替换模板中的变量
    for key, value in template_args.items():
        placeholder = "{" + key + "}"
        template_content = template_content.replace(placeholder, str(value))
    
    return template_content

def evaluate_report(
    dataset_context: str, 
    query: str, 
    md_report: str, 
    report_image: str = None,
    llm_kwargs: Dict[str, Any] = None,
    max_retries: int = 3
) -> float:
    """
    评估数据可视化报告质量
    
    参数:
        dataset_context: 数据集上下文
        query: 用户查询
        md_report: 报告Markdown内容
        report_image: 报告截图的base64编码（可选，但当前实现不使用）
        llm_kwargs: LLM调用参数
        max_retries: 最大重试次数
    
    返回:
        float: 加权评分 (0-10分)
    """
    # 构建提示词（在重试循环外准备，避免重复构建）
    prompt_args = {
        "DATASET_CONTEXT": dataset_context,
        "QUERY": query,
        "REPORT": md_report,
        "REPORT_IMAGE": ""  # 不包含图像
    }
    
    # 使用自定义函数获取模板内容，避免格式化问题
    prompt = get_prompt_content("report_evaluation", prompt_args)
    if not prompt:
        print("❌ 获取模板内容失败")
        return 5.0  # 默认中等分数
        
    # 重试机制
    for attempt in range(max_retries):
        try:
            if attempt == 0:
                print("📝 使用通用API进行报告评估...")
            else:
                print(f"🔄 第{attempt + 1}次重试报告评估...")
            
            # 调用API进行评估
            responses = call_openai(prompt, **(llm_kwargs or {}))
            if not responses:
                print("⚠️ API未返回有效响应")
                if attempt == max_retries - 1:  # 最后一次尝试
                    return 5.0  # 默认中等分数
                continue
                
            response_text = responses[0].strip()
            print("✅ 成功获取评估响应")
            
            # 输出原始响应，方便调试
            print(f"\n📝 评估响应(截取前200字符):\n{response_text[:200]}...")
            
            # 处理可能的markdown格式
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "")
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "")
            response_text = response_text.strip()
            
            # 尝试解析JSON
            result = None
            
            # 首先尝试直接解析JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # 如果直接解析失败，使用增强的JSON提取方法
                print("⚠️ 直接JSON解析失败，尝试提取JSON...")
                result = extract_json_from_text(response_text)
                
            # 检查是否成功解析JSON
            if not result:
                print(f"❌ 第{attempt + 1}次尝试：无法从响应中提取有效JSON")
                if attempt == max_retries - 1:  # 最后一次尝试
                    print("❌ 所有重试都失败，返回默认分数")
                    return 5.0  # 默认中等分数
                continue  # 继续重试
            
            # 验证所有必要的键是否存在
            required_keys = ["informativeness", "clarity_coherence", "visualization_quality", "narrative_quality"]
            missing_keys = [key for key in required_keys if key not in result]
            if missing_keys:
                print(f"❌ 第{attempt + 1}次尝试：缺少必要的评估维度: {missing_keys}")
                if attempt == max_retries - 1:  # 最后一次尝试
                    print("❌ 所有重试都失败，返回默认分数")
                    return 5.0  # 默认中等分数
                continue  # 继续重试
            
            # 确保评分是数值类型
            try:
                for key in required_keys:
                    if not isinstance(result[key]["score"], (int, float)):
                        result[key]["score"] = float(result[key]["score"])
            except (ValueError, TypeError, KeyError) as e:
                print(f"❌ 第{attempt + 1}次尝试：评分转换为数值时出错: {str(e)}")
                if attempt == max_retries - 1:  # 最后一次尝试
                    print("❌ 所有重试都失败，返回默认分数")
                    return 5.0
                continue  # 继续重试
                
            # 如果到这里，说明解析成功
            print(f"✅ 第{attempt + 1}次尝试成功解析JSON")
            
            # 计算加权分数 - 所有维度权重相等 (25%)
            weighted_score = (
                0.3 * result["informativeness"]["score"] +
                0.3 * result["clarity_coherence"]["score"] +
                0.2 * result["visualization_quality"]["score"] +
                0.2 * result["narrative_quality"]["score"]
            )
            
            # 打印评估结果
            print("\n📊 报告评估结果:")
            print(f"- 信息丰富度 (30%): {result['informativeness']['score']}/10")
            print(f"  理由: {result['informativeness']['rationale'][:200]}...")
            
            print(f"\n- 清晰度与连贯性 (30%): {result['clarity_coherence']['score']}/10")
            print(f"  理由: {result['clarity_coherence']['rationale'][:200]}...")
            
            print(f"\n- 可视化质量 (30%): {result['visualization_quality']['score']}/10")
            print(f"  理由: {result['visualization_quality']['rationale'][:200]}...")
            
            print(f"\n- 叙事质量 (30%): {result['narrative_quality']['score']}/10")
            print(f"  理由: {result['narrative_quality']['rationale'][:200]}...")
            
            print(f"\n✨ 加权总分: {weighted_score:.2f}/10")
            
            return round(weighted_score, 2)
            
        except Exception as e:
            print(f"❌ 第{attempt + 1}次尝试出错: {str(e)}")
            if attempt == max_retries - 1:  # 最后一次尝试
                print("❌ 所有重试都失败，返回默认分数")
                traceback.print_exc()  # 打印详细错误堆栈
                return 5.0
            # 继续重试
    
    # 理论上不会到达这里，但作为安全保障
    return 5.0
    