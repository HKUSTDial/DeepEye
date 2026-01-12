from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from copy import deepcopy
from enum import Enum
import copy

# 条件导入，只在类型检查时导入
if TYPE_CHECKING:
    from .mcts_action import DataStorytellingAction

    
class ReportGenerationState(Enum):
    EMPTY = "Empty"  
    # 📌 初始状态：报告尚未开始处理，等待数据预处理

    a1 = "a1"
    # 📌 已定义章节结构：章节已经划分，但未开始生成具体内容

    a2 = "a2"
    # 📌 章节进行中：某个章节正在被处理（但章节未完成，且可能有多个章节未完成）

    a3 = "a3"
    # 📌 部分章节生成完整内容

    a4 = "a4"
    # 📌 可视化任务进行中：某个可视化任务正在被处理（但任务未完成，且可能有多个任务未完成）

    a5 = "a5"
    # 📌 部分可视化任务生成完整内容

    a6 = "a6"
    # 📌 整体报告优化完成：调整了叙事逻辑，所有章节信息结构优化完毕

    a7 = "a7"
    # 📌 章节标题优化完成：所有章节标题优化完毕

    a8 = "a8"
    # 📌 章节顺序优化完成：所有章节顺序优化完毕

    a9 = "a9"
    # 📌 整体报告优化完成：调整了叙事逻辑，所有章节信息结构优化完毕

    a10 = "a10"
    # 📌 整体报告优化完成：调整了叙事逻辑，所有章节信息结构优化完毕

    a11 = "a11"
    # 📌 摘要和结论优化完成：所有摘要和结论优化完毕

    FINALIZED = "Finalized"
    # 📌 最终报告生成完成：搜索终止，报告完成，可以导出

    REVISECHAPTERSORDERS = "ReviseChaptersOrders"
    # 📌 章节顺序已调整：已调整章节顺序，优化报告结构
    
    ADDEDTRANSITIONS = "AddedTransitions"
    # 📌 过渡文本已添加：所有章节间过渡文本已添加，提高报告连贯性




# Chart 单个图表
class Chart:
    def __init__(self,
                url: str, 
                caption: str,
                chart_position: str = "center",
                code: str = None,
                chart_type: str = None,
                task_id: str = None):
        """
        初始化图表对象
        
        参数:
            url: 图表的URL地址
            caption: 图表的说明文字
            chart_position: 图表在页面中的位置，默认为居中
            code: 生成图表的代码
            chart_type: 图表类型
            task_id: 关联的任务ID
        """
        self.type = "chart"  # 类型标识，表明这是单个图表
        self.url = url  # 存储图表的URL
        self.caption = caption  # 存储图表的说明文字
        self.chart_position = chart_position  # 图表在报告中的位置
        self.code = code  # 存储生成图表的代码
        self.chart_type = chart_type  # 存储图表类型
        self.task_id = task_id  # 存储关联的任务ID
        self.needs_caption = False  # 标记是否需要生成说明文字

    def to_dict(self):
        """
        将图表对象转换为字典格式，便于JSON序列化
        
        返回:
            包含图表信息的字典
        """
        chart_dict = {
            "type": self.type,
            "url": self.url,
            "caption": self.caption,
            "chart_position": self.chart_position,
            "code": self.code,
            "chart_type": self.chart_type,
            "task_id": self.task_id,
            "needs_caption": self.needs_caption
        }
        return chart_dict

# ChartGroup 多个Chart组合
class ChartGroup:
    def __init__(self, 
                 charts_list: List[Chart], 
                 caption: Optional[str] = None, 
                 chart_position: str = "side-by-side", 
                 caption_position: str = "below"):
        """
        初始化图表组合对象
        
        参数:
            charts_list: 图表对象列表
            caption: 整个图表组的共享说明文字，可选
        """
        self.type = "chart_group"
        self.charts_list = charts_list
        self.caption = caption
        self.chart_position = chart_position

    def to_dict(self):
        """
        将图表组合对象转换为字典格式，便于JSON序列化
        
        返回:
            包含图表组合信息的字典
        """
        return {
            "type": self.type,
            "charts_list": [chart.to_dict() for chart in self.charts_list],  # 将每个图表也转换为字典
            "caption": self.caption,
            "chart_position": self.chart_position
        }

# Chapter 章节
class Chapter:
    def __init__(self, title: str, summary: Optional[str] = None):
        """
        初始化章节对象
        
        参数:
            title: 章节标题
            summary: 章节摘要，可选
        """
        self.title = title  # 存储章节标题
        self.summary = summary  # 存储章节摘要
        self.charts: List[Union[Chart, ChartGroup]] = []  # 初始化空的图表/图表组合列表
        self.visualization_tasks = []  # 可视化任务列表
        self.tasks_status = {}  # 任务状态字典，用于跟踪任务的完成状态
        
    def add_chart(self, chart: Chart):
        """
        向章节添加单个图表
        
        参数:
            chart: 要添加的图表对象
        """
        self.charts.append(chart)  # 将图表添加到列表中

    def add_chart_group(self, chart_group: ChartGroup):
        """
        向章节添加图表组合
        
        参数:
            chart_group: 要添加的图表组合对象
        """
        self.charts.append(chart_group)  # 将图表组合添加到列表中
        
    def initialize_tasks_status(self):
        """初始化所有可视化任务的状态为 'pending'"""
        if hasattr(self, 'visualization_tasks'):
            self.tasks_status = {}  # 确保是空字典
            for i, task in enumerate(self.visualization_tasks):
                task_id = task.get('task_id', f"task_{i+1}")
                # 使用简单字符串值
                self.tasks_status[task_id] = "pending"  # 可能的状态: pending, in_progress, completed

    def get_next_pending_task(self):
        """获取下一个待处理的任务"""
        if not hasattr(self, 'visualization_tasks') or not self.visualization_tasks:
            return None, None
        
        if not hasattr(self, 'tasks_status'):
            self.tasks_status = {}
        
        # 遍历所有任务，查找状态为 pending 的任务
        for task in self.visualization_tasks:
            task_id = task.get('task_id')
            if task_id:
                # 获取任务状态，默认为 pending
                task_status = self.tasks_status.get(task_id, "pending")
                if task_status == "pending":
                    return task_id, task
        
        return None, None
        
    def mark_task_in_progress(self, task_id):
        """标记任务为进行中"""
        if not hasattr(self, 'tasks_status'):
            self.tasks_status = {}
        self.tasks_status[task_id] = "in_progress"
            
    def mark_task_completed(self, task_id):
        """将任务标记为已完成"""
        if not hasattr(self, 'tasks_status'):
            self.tasks_status = {}
        self.tasks_status[task_id] = "completed"
            
    def all_tasks_completed(self):
        """检查是否所有任务都已完成"""
        if not hasattr(self, 'visualization_tasks') or not self.visualization_tasks:
            return True
        
        if not hasattr(self, 'tasks_status'):
            return False
        
        for task in self.visualization_tasks:
            task_id = task.get('task_id')
            if task_id and self.tasks_status.get(task_id) != "completed":
                return False
        return True

    def to_dict(self):
        """
        将章节对象转换为字典格式，便于JSON序列化
        
        返回:
            包含章节信息的字典
        """
        return {
            "title": self.title,
            "summary": self.summary,
            "charts": [chart.to_dict() for chart in self.charts]  # 将每个图表/图表组合也转换为字典
        }

# Report 完整报告
class Report:
    def __init__(self, 
                 original_query: str,  # 原始查询
                 dataset_path: str,    # 数据集路径
                 data_context: str = "",   # 数据摘要（可选）
                 clarified_query: str = "", # 澄清后的查询（可选）
                 dataset_description: str = "", # 数据描述（可选）
                 task_list: List[str] = None, # 任务列表（可选）
                 narrative_strategy: str = "data-driven",  # 叙事策略
                 layout_strategy: str = "thematic",        # 布局策略
                 chapters: Optional[List[Chapter]] = None): # 章节列表
        """
        初始化报告对象
        
        参数:
            original_query: 原始用户查询
            dataset_path: 数据集路径
            data_context: 数据摘要
            clarified_query: 澄清后的查询
            data_description: 数据描述
            task_list: 任务列表
            narrative_strategy: 叙事策略
            layout_strategy: 布局策略
            chapters: 章节列表
        """
        self.original_query = original_query  # 存储原始查询
        self.dataset_path = dataset_path      # 存储数据集路径
        self.data_context = data_context      # 存储数据摘要
        self.clarified_query = clarified_query  # 存储澄清后的查询
        self.dataset_description = dataset_description  # 存储数据描述
        self.task_list = task_list if task_list else []  # 存储任务列表
        self.narrative_strategy = narrative_strategy  # 存储叙事策略
        self.layout_strategy = layout_strategy        # 存储布局策略
        self.chapters = chapters if chapters else []  # 存储章节列表
        self.full_column_names = []  # 完整列名（由 action 生成）
        self.current_iteration = 0  # 添加当前迭代号属性
        
    def add_chapter(self, chapter: Chapter) -> None:
        """
        向报告添加章节
        
        参数:
            chapter: 要添加的章节对象
        """
        self.chapters.append(chapter)  # 将章节添加到列表中
        
    def get_chapter_by_title(self, title: str) -> Optional[Chapter]:
        """
        根据标题获取章节
        
        参数:
            title: 章节标题
            
        返回:
            找到的章节对象，如果没找到则返回None
        """
        for chapter in self.chapters:
            if chapter.title == title:
                return chapter
        return None
        
    def get_chapter_titles(self) -> List[str]:
        """获取所有章节标题"""
        return [chapter.title for chapter in self.chapters]
        
    def get_chart_count(self) -> int:
        """获取报告中的图表总数"""
        return sum(len(chapter.charts) for chapter in self.chapters)

    def to_dict(self) -> Dict[str, Any]:
        """
        将报告对象转换为字典格式，便于JSON序列化
        
        返回:
            包含报告信息的字典
        """
        return {
            "original_query": self.original_query,
            "data_context": self.data_context,
            "clarified_query": self.clarified_query,
            "dataset_description": self.dataset_description,
            "task_list": self.task_list,
            "dataset_path": self.dataset_path,
            "narrative_strategy": self.narrative_strategy,
            "layout_strategy": self.layout_strategy,
            "chapters": [chapter.to_dict() for chapter in self.chapters],  # 将每个章节也转换为字典
        }
        
    def __str__(self) -> str:
        """字符串表示"""
        return f"Report(query='{self.original_query}', chapters={len(self.chapters)})"

# MCTSNode 类定义
class MCTSNode:
    def __init__(self, 
                 node_type: Union[str, ReportGenerationState],
                 parent_node: Optional["MCTSNode"] = None,
                 parent_action: Optional["DataStorytellingAction"] = None,
                 depth: int = 0,
                 report: Optional[Report] = None,
                 original_query: str = "",
                 llm_kwargs: Optional[Dict[str, Any]] = None):
        """
        初始化 MCTS 节点
        """
        # 确保 node_type 是 ReportGenerationState 枚举类型
        if isinstance(node_type, str):
            try:
                self.node_type = ReportGenerationState[node_type]  # 使用字典式访问
            except KeyError:
                # 如果字符串不是枚举名称，尝试使用值匹配
                try:
                    self.node_type = ReportGenerationState(node_type)
                except ValueError:
                    raise ValueError(f"Invalid node_type: {node_type}")
        else:
            self.node_type = node_type
            
        self.parent_node = parent_node
        self.parent_action = parent_action
        self.depth = depth

        # 当前节点所代表的报告对象
        if report:
            # 如果提供了报告对象，则深拷贝它
            self.report = deepcopy(report)
        elif parent_node:
            # 如果没有提供报告对象但有父节点，则从父节点复制报告对象
            self.report = deepcopy(parent_node.report)
        else:
            # 如果既没有报告对象也没有父节点，则抛出错误
            raise ValueError("Either report or parent_node.report must be provided.")

        self.original_query = original_query  # 存储原始查询
        self.llm_kwargs = llm_kwargs if llm_kwargs else {}  # 存储语言模型参数，如果没有提供则初始化为空字典

        self.children: List["MCTSNode"] = []  # 初始化空的子节点列表

        # MCTS算法统计信息
        self.Q = 0.0  # 累积奖励值（节点质量）
        self.N = 0    # 节点访问次数
        
        # 添加 expanded 属性，初始值为 False
        self.expanded = False
        
        # 添加 selected_task 属性
        self.selected_task = None  # 当前选中的可视化任务
        self.selected_chapter_idx = None  # 当前选中的章节索引
        
        self.data_processed = False  # 添加数据处理状态标记
        
    def add_child(self, child_node: "MCTSNode") -> None:
        """添加子节点"""
        self.children.append(child_node)
        
    def get_chapter_count(self) -> int:
        """获取报告中的章节数量"""
        return len(self.report.chapters)
        
    def get_chart_count(self) -> int:
        """获取报告中的图表总数"""
        return sum(len(chapter.charts) for chapter in self.report.chapters)
    
    def get_report_summary(self) -> Dict[str, Any]:
        """获取报告摘要信息"""
        return {
            "query": self.original_query,
            "chapter_count": self.get_chapter_count(),
            "chart_count": self.get_chart_count(),
            "node_type": self.node_type,
            "depth": self.depth
        }

    def expand(self, action_space: List["DataStorytellingAction"]):
        """
        扩展当前节点，生成子节点
        
        参数:
            action_space: 可用动作列表
        """
        # 如果已经有子节点，则不再扩展
        if self.children:
            return

        # 对每个可用动作，创建一个子节点
        for action in action_space:
            # 复制当前报告状态
            child_report = deepcopy(self.report)
            # 执行动作，修改报告状态
            action.execute(child_report=child_report, llm_kwargs=self.llm_kwargs)
            # 创建子节点
            child_node = MCTSNode(
                node_type=action.next_node_type,  # 下一个节点类型
                parent_node=self,                # 父节点为当前节点
                parent_action=action,            # 父动作为当前动作
                depth=self.depth + 1,            # 深度加1
                report=child_report,             # 报告状态为修改后的状态
                original_query=self.original_query, # 原始查询保持不变
                llm_kwargs=self.llm_kwargs       # 语言模型参数保持不变
            )
            # 将子节点添加到子节点列表
            self.children.append(child_node)

    def is_terminal(self):
        """
        判断是否为终止节点
        
        返回:
            如果节点类型为 FINALIZED，则返回True，否则返回False
        """
        return self.node_type == ReportGenerationState.FINALIZED
        
    def __str__(self) -> str:
        """字符串表示"""
        return f"MCTSNode(type={self.node_type}, depth={self.depth}, chapters={self.get_chapter_count()})"
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "node_type": self.node_type,
            "depth": self.depth,
            "report": self.report.to_dict(),
            "children_count": len(self.children),
            "Q": self.Q,
            "N": self.N
        }

    def generate_html_report(self) -> str:
        """生成节点对应的HTML报告"""
        # 实现报告生成逻辑
        pass 

    def copy(self):
        """创建节点的深度复制"""
        new_node = MCTSNode(self.node_type)
        new_node.visits = self.visits
        new_node.value = self.value
        new_node.depth = self.depth
        # 确保report被正确复制，包括current_iteration
        new_node.report = copy.deepcopy(self.report)
        return new_node 