import math
from typing import Dict, Any
from storyteller.algorithm.mcts_node import MCTSNode, ReportGenerationState
from storyteller.algorithm.evaluator import evaluate_report
from storyteller.algorithm.utils.html2image import convert_html_to_image
import base64
import os

class StorytellingRewardModel:
    def __init__(self, llm_kwargs: Dict[str, Any] = None):
        """
        数据故事 MCTS 奖励函数
        
        参数:
            llm_kwargs: LLM调用参数
        """
        self.llm_kwargs = llm_kwargs or {}
        # 添加记录最后一次评分的属性
        self.last_quality_reward = 0.0

    def compute_reward(self, node: MCTSNode, html_path: str, image_path: str) -> float:
        """计算节点的奖励值"""
        # 只计算质量奖励 - 确保能看到图表的报告质量评估
        quality_reward = self._compute_quality_reward(node, html_path, image_path)
        self.last_quality_reward = quality_reward
        
        # 输出详细评分信息，帮助调试
        print(f"📊 评分明细 - 质量: {quality_reward:.2f}")
        
        return quality_reward
        
    def _compute_quality_reward(self, node: MCTSNode, html_path: str, image_path: str) -> float:
        """计算质量奖励（0-10分）"""
        try:
            # 如果报告未完成，返回基础分数
            if node.node_type != ReportGenerationState.FINALIZED:
                return 5.0
                
            # 准备评估所需参数
            dataset_context = node.report.data_context or ""
            query = node.report.original_query
            
            # 获取md文件路径 (通常与html文件在同一目录)
            md_path = os.path.join(os.path.dirname(html_path), "report.md")
            
            # 读取MD内容
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                print(f"✅ 成功读取Markdown报告: {md_path}")
            except Exception as e:
                print(f"⚠️ 无法读取Markdown报告: {str(e)}，尝试从HTML转换")
                # 如果无法读取MD文件，则读取HTML作为备选
                with open(html_path, 'r', encoding='utf-8') as f:
                    md_content = f"# HTML报告内容 (Markdown不可用)\n\n```html\n{f.read()}\n```"
                
            # 读取图片并转为base64
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode()
            
            # 调用评估函数
            quality_score = evaluate_report(
                dataset_context=dataset_context,
                query=query,
                md_report=md_content,
                report_image=image_base64,
                llm_kwargs=self.llm_kwargs
            )
            
            return quality_score
            
        except Exception as e:
            print(f"❌ 质量评估出错: {str(e)}")
            return 5.0
            
    def _generate_html_report(self, node: MCTSNode) -> str:
        """生成 HTML 格式的报告"""
        # TODO: 实现 HTML 报告生成逻辑
        # 可以调用 mcts_runner.py 中的相关函数
        return str(node.report)  # 临时返回报告的字符串表示