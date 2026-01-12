import markdown
from bs4 import BeautifulSoup
import os
import argparse
from pathlib import Path
import random
import urllib.parse
import json
import re

def parse_markdown(md_path):
    """
    解析Markdown文件，提取章节和图表信息
    直接使用更高效的直接解析方法
    """
    #print(f"\n开始解析Markdown文件: {md_path}")
    return parse_markdown_direct(md_path)

def parse_markdown_direct(md_path):
    """使用直接解析Markdown的方式提取数据结构"""
    #print(f"\n使用直接解析方式提取Markdown内容: {md_path}")
    
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 获取Markdown文件所在目录
    md_dir = os.path.dirname(os.path.abspath(md_path))
    # 提取迭代目录路径 (例如: /path/to/iteration_1/)
    iteration_dir = md_dir
    # 查找vegalite_configs目录
    vegalite_configs_dir = os.path.join(iteration_dir, "vegalite_configs")
    print(f"Vega-Lite配置目录: {vegalite_configs_dir}")

    # 初始化数据结构
    sections = []
    current_section = None
    current_caption = ""
    in_chart_group = False
    current_group_charts = []
    current_group_caption = ""
    current_subsection = None
    summary_content = ""
    intro_text = []  # 用于存储章节引言/过渡文本
    query_from_title = ""  # 用于存储从标题中提取的查询
    report_abstract = ""  # 用于存储报告摘要
    report_conclusion = ""  # 用于存储报告结论
    
    # 按行处理Markdown内容
    lines = md_content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 识别主标题 (# 开头) - 从中提取查询
        if line.startswith('# ') and not query_from_title:
            query_from_title = line[2:].strip()  # 移除"# "前缀
            print(f"从标题中提取查询: {query_from_title}")
            i += 1
            continue
        
        # 识别摘要部分 (## 摘要)
        elif line.startswith('## 摘要') or line.startswith('## Abstract') or line.startswith('## Summary') or line.startswith('## Key Abstract'):
            print(f"发现摘要部分: {line}")
            # 收集摘要内容直到下一个章节标题
            abstract_lines = []
            j = i + 1
            while j < len(lines) and not (lines[j].strip().startswith('## ') and 
                                        not lines[j].strip().startswith('## 摘要') and 
                                        not lines[j].strip().startswith('## Abstract') and 
                                        not lines[j].strip().startswith('## Summary') and
                                        not lines[j].strip().startswith('## Key Abstract')):
                if lines[j].strip():  # 只添加非空行
                    abstract_lines.append(lines[j].strip())
                j += 1
            
            if abstract_lines:
                report_abstract = " ".join(abstract_lines)
                print(f"收集摘要内容: {report_abstract[:100]}...")
            
            # 跳过已处理的行
            i = j - 1
        
        # 识别结论部分 (## brief_conclusion)
        elif line.startswith('## brief_conclusion') or line.startswith('## 结论') or line.startswith('## Conclusion'):
            print(f"发现结论部分: {line}")
            # 收集结论内容直到文件结束
            conclusion_lines = []
            j = i + 1
            while j < len(lines):
                if lines[j].strip():  # 只添加非空行
                    conclusion_lines.append(lines[j].strip())
                j += 1
            
            if conclusion_lines:
                report_conclusion = " ".join(conclusion_lines)
                print(f"收集结论内容: {report_conclusion[:100]}...")
            
            # 跳过已处理的行
            i = j - 1
        
        # 识别章节标题 (## 开头，但排除摘要)
        elif line.startswith('## ') and not line.startswith('## 摘要') and not line.startswith('## Abstract') and not line.startswith('## Summary') and not line.startswith('## Key Abstract'):
            # 保存之前的章节（如果有）
            if current_section:
                # 添加所有收集到的章节总结
                if summary_content:
                    current_section["summary"] = summary_content
                    print(f"设置章节摘要: {current_section['summary'][:50]}...")
                    summary_content = ""
                sections.append(current_section)
            
            # 提取章节标题
            title = line[3:].strip()
            # 处理字典格式的标题
            if title.startswith("{'title': '") and title.endswith("'}"):
                title = title[len("{'title': '"):-2]
            
            # 创建新章节
            current_section = {
                "title": title,
                "charts": [],
                "summary": "",
                "key_insights": [],
                "subsections": [],
                "intro_text": ""  # 添加引言/过渡文本字段
            }
            current_caption = ""
            in_chart_group = False
            current_group_charts = []
            current_group_caption = ""
            current_subsection = None
            summary_content = ""
            intro_text = []  # 重置引言文本
            
            print(f"发现章节: {title}")
        
        # 识别Chapter Summary部分
        elif line.startswith("### Chapter Summary") or line.startswith("### 章节总结"):
            # 当找到一个章节总结时，收集所有内容直到下一个标题
            summary_lines = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('#') and j < len(lines):
                if lines[j].strip():  # 只有非空行才添加
                    summary_lines.append(lines[j].strip())
                j += 1
            
            if summary_lines and current_section:
                summary_content = " ".join(summary_lines)
                # 注意：不要立即设置current_section["summary"]，而是在章节结束时设置
                #print(f"收集章节摘要（将在章节末尾显示）: {summary_content[:50]}...")
                # 跳过已处理的行
                i = j - 1
        
        # 识别子章节标题 (### 开头，但不是Chapter Summary)
        elif line.startswith('### ') and not line.startswith("### Chapter Summary") and not line.startswith("### 章节总结"):
            # 如果此时有收集到的引言文本，则保存到当前章节
            if intro_text and current_section:
                current_section["intro_text"] = "\n".join(intro_text)
                #print(f"设置章节引言: {current_section['intro_text'][:50]}...")
                intro_text = []
            
            subsection_title = line[4:].strip()
            current_subsection = {
                "title": subsection_title,
                "content": []
            }
            if current_section:
                current_section["subsections"].append(current_subsection)
            #print(f"发现子章节: {subsection_title}")
        
        # 识别普通段落文本
        elif line and not line.startswith('>') and not line.startswith('<!--') and not line.startswith('!['):
            if current_subsection:
                # 如果有当前子章节，添加到子章节内容
                if current_subsection.get("content"):
                    current_subsection["content"].append(line)
                else:
                    current_subsection["content"] = [line]
            elif current_section and not current_subsection:
                # 如果没有当前子章节但有当前章节，此为章节引言/过渡文本
                intro_text.append(line)
        
        # 识别引用块 (> 开头)，处理为caption
        elif line.startswith('>'):
            caption_text = line[1:].strip()
            
            # 检查下一行是否也是引用块 (> 开头)，如果是则合并
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('>'):
                caption_text += '\n' + lines[j][1:].strip()
                j += 1
                i += 1  # 跳过已处理的行
            
            # 检查下一行是否是key point的连续部分(不以>开头但以key point开头)
            while j < len(lines) and lines[j].strip() and (lines[j].strip().startswith('key point') or 
                  (caption_text.endswith('key point') and not lines[j].strip().startswith('>'))):
                caption_text += '\n' + lines[j].strip()
                j += 1
                i += 1  # 跳过已处理的行
            
            # 检查是否是无价值图表的caption
            is_no_value_caption = (
                "will not be included" in caption_text.lower() or
                "lacks clear insight" in caption_text.lower() or
                "no insight value" in caption_text.lower() or
                "不包含在最终报告中" in caption_text.lower()
            )
            
            if is_no_value_caption:
                print(f"⚠️ 检测到无价值图表caption，将跳过后续图表: {caption_text[:50]}...")
                # 设置特殊标记，用于跳过接下来的图表
                current_caption = "SKIP_NO_VALUE"
            else:
                # 检查是否是图表组开始
                k = j
                while k < len(lines) and not lines[k].strip():
                    k += 1  # 跳过空行
                    
                is_next_group_start = k < len(lines) and "<!-- chart-group-start -->" in lines[k].strip()
                
                if in_chart_group or is_next_group_start:
                    current_group_caption = caption_text
                    #print(f"设置图表组caption: {caption_text[:30]}...")
                else:
                    current_caption = caption_text
                    #print(f"设置单图表caption: {caption_text[:30]}...")
        
        # 识别图表组开始标记
        elif '<!-- chart-group-start -->' in line:
            in_chart_group = True
            current_group_charts = []
            #print("检测到图表组开始标记")
                
        # 识别图表组结束标记
        elif '<!-- chart-group-end -->' in line:
            if in_chart_group and current_group_charts and current_section:
                # 检查是否是无价值图表组
                if current_group_caption == "SKIP_NO_VALUE":
                    print(f"⚠️ 跳过无价值图表组，包含 {len(current_group_charts)} 个图表")
                else:
                    # 创建图表组对象
                    chart_group = {
                        "is_chart_group": True,
                        "charts": current_group_charts,
                        "group_caption": current_group_caption
                    }
                    
                    # 添加到章节
                    current_section["charts"].append(chart_group)
                    print(f"添加图表组，包含 {len(current_group_charts)} 个图表, caption: '{current_group_caption[:50]}...'")
            
            in_chart_group = False
            current_group_charts = []
            current_group_caption = ""
        
        # 识别图片 (![alt](src) 格式)
        elif line.startswith('![') and '](' in line and line.endswith(')'):
            # 检查是否应该跳过无价值图表
            if current_caption == "SKIP_NO_VALUE" or current_group_caption == "SKIP_NO_VALUE":
                print(f"⚠️ 跳过无价值图表: {line}")
                # 重置标记，但不处理这个图表
                if not in_chart_group:
                    current_caption = ""
                i += 1
                continue
            
            # 提取图片信息
            alt_start = line.find('![') + 2
            alt_end = line.find('](')
            src_start = alt_end + 2
            src_end = line.rfind(')')
            
            if alt_start < alt_end and src_start < src_end:
                alt_text = line[alt_start:alt_end]
                src = line[src_start:src_end]
                
                # 提取文件名
                img_filename = os.path.basename(src)
                
                # 直接使用相对于charts文件夹的路径
                relative_img_path = "charts/" + img_filename
                
                # 提取图片文件名（不包含路径和扩展名）
                img_name, img_ext = os.path.splitext(img_filename)
                
                # 查找对应的Vega-Lite配置文件
                vegalite_config_path = os.path.join(vegalite_configs_dir, f"{img_name}.json")
                
                # 创建图表信息
                chart_info = {
                    "img": relative_img_path,  # 只保存相对路径
                    "img_filename": img_filename,  # 保存文件名
                    "caption": current_caption if not in_chart_group else "",
                    "alt_text": alt_text,
                    "subsection_title": current_subsection["title"] if current_subsection else ""
                }
                
                # 如果找到对应的Vega-Lite配置文件，添加到chart_info中
                if os.path.exists(vegalite_config_path):
                    chart_info["vegalite_config"] = vegalite_config_path
                    chart_info["is_vegalite"] = True  # 标记为Vega-Lite图表
                    print(f"找到Vega-Lite配置文件: {vegalite_config_path}")
                else:
                    print(f"未找到Vega-Lite配置文件: {vegalite_config_path}")
                
                # 添加到适当的位置
                if in_chart_group:
                    chart_info["in_group"] = True
                    current_group_charts.append(chart_info)
                    print(f"添加图片到组: {src}, vegalite: {chart_info.get('is_vegalite', False)}")
                elif current_section:
                    current_section["charts"].append(chart_info)
                    print(f"添加单个图片: {src}, vegalite: {chart_info.get('is_vegalite', False)}")
        
        i += 1
    
    # 添加最后一个章节
    if current_section:
        # 保存收集的引言文本（如果有）
        if intro_text:
            current_section["intro_text"] = "\n".join(intro_text)
            #print(f"设置最后章节引言: {current_section['intro_text'][:50]}...")
        
        # 添加所有收集到的章节总结
        if summary_content:
            current_section["summary"] = summary_content
            #print(f"设置最后章节摘要: {current_section['summary'][:50]}...")
        sections.append(current_section)
    
    # 打印统计信息
    if report_abstract:
        print(f"\n解析完成: 找到报告摘要和 {len(sections)} 个章节")
        print(f"报告摘要: {report_abstract[:100]}...")
    else:
        print(f"\n解析完成: 找到 {len(sections)} 个章节（无摘要）")
    
    for i, section in enumerate(sections, 1):
        charts_count = len(section.get("charts", []))
        subsections_count = len(section.get("subsections", []))
        has_intro = bool(section.get("intro_text", ""))
        #print(f"章节 {i}: '{section.get('title', '无标题')}' - 包含 {charts_count} 个图表/图表组, {subsections_count} 个子章节, 有引言: {has_intro}")
        
        # 打印子章节信息
        for k, subsection in enumerate(section.get("subsections", []), 1):
            print(f"  - 子章节 {k}: '{subsection.get('title', '无标题')}'")
        
        for j, chart in enumerate(section.get("charts", []), 1):
            if isinstance(chart, dict) and chart.get("is_chart_group", False):
                group_charts = chart.get("charts", [])
                group_caption = chart.get("group_caption", "")
                vegalite_charts = sum(1 for c in group_charts if c.get("is_vegalite", False))
                #print(f"  - 图表组 {j}: 包含 {len(group_charts)} 个图表 ({vegalite_charts} 个Vega-Lite), caption: '{group_caption[:30]}...'")
            else:
                img_path = chart.get("img", "")
                caption = chart.get("caption", "")
                is_vegalite = chart.get("is_vegalite", False)
                #print(f"  - 图表 {j}: {chart.get('img_filename', '')}, caption: '{caption[:30]}...', vegalite: {is_vegalite}")
        
        # 打印章节摘要信息
        if section.get("summary"):
            print(f"  - 摘要: '{section.get('summary', '')[:50]}...'")
        else:
            print(f"  - 无摘要")
    
    return sections, query_from_title, report_abstract

# 辅助函数：将文件名中的特殊字符转换为下划线，避免在查找文件时出错
def escape_filename(name):
    if not name:
        return "unnamed"
    # 将特殊字符转换为下划线，保留字母、数字和常见标点
    import re
    return re.sub(r'[^\w\-\.]', '_', name)

# 辅助函数：将绝对路径转换为相对路径
def convert_to_relative_path(path):
    """
    将路径转换为适合HTML中使用的相对路径，处理空格和特殊字符
    """
    if not path:
        return ""
        
    # 使用URL编码处理空格和特殊字符
    # 如果是相对路径，直接返回编码后的路径
    encoded_path = path.replace(" ", "%20")
    return encoded_path

# 添加一个通用函数来处理Vega-Lite配置
def prepare_vegalite_config(sections):
    """
    为sections中的所有图表准备Vega-Lite配置
    返回：
    - chart_configs: 包含所有图表配置的列表
    - chart_id_counter: 用于生成唯一图表ID的计数器
    """
    # 用于存储所有图表配置的数组
    chart_configs = []
    
    # 为每个图表创建唯一的ID
    chart_id_counter = 0
    
    for section in sections:
        for chart_item in section.get("charts", []):
            # 检查是否是图表组
            if isinstance(chart_item, dict) and chart_item.get("is_chart_group", False):
                # 处理图表组内的所有图表
                for group_chart in chart_item.get("charts", []):
                    process_chart_config(group_chart, chart_configs, chart_id_counter)
                    if "chart_id" in group_chart:
                        chart_id_counter += 1
            else:
                # 处理单个图表
                process_chart_config(chart_item, chart_configs, chart_id_counter)
                if "chart_id" in chart_item:
                    chart_id_counter += 1
    
    return chart_configs, chart_id_counter

def process_chart_config(chart, chart_configs, chart_id_counter):
    """处理单个图表的配置"""
    vegalite_config_path = chart.get("vegalite_config", "")
    img_path = chart.get("img", "")
    
    if vegalite_config_path and os.path.exists(vegalite_config_path):
        # 如果有配置文件，使用Vega-Lite渲染
        chart_id = f"vegalite_chart_{chart_id_counter}"
        
        # 读取JSON配置文件内容
        try:
            with open(vegalite_config_path, 'r', encoding='utf-8') as f:
                vegalite_spec = json.load(f)
            
            # 修改Vega-Lite规格，确保它能自适应容器宽度
            vegalite_spec["width"] = "container"
            vegalite_spec["height"] = "container"
            
            # 优化y轴标题显示
            if "encoding" in vegalite_spec:
                if "y" in vegalite_spec["encoding"]:
                    # 只有当配置文件中没有指定axis.title时才设置
                    y_encoding = vegalite_spec["encoding"]["y"]
                    if "axis" not in y_encoding or "title" not in y_encoding["axis"]:
                        y_field = y_encoding.get("field", "")
                        if "Purchase_Amount__USD_" in y_field:
                            if "axis" not in y_encoding:
                                y_encoding["axis"] = {}
                            y_encoding["axis"]["title"] = "Purchase Amount (USD)"
                    
                    # 添加字体大小设置
                    if "axis" in y_encoding:
                        y_encoding["axis"]["titleFontSize"] = 14
                        y_encoding["axis"]["labelFontSize"] = 12
            
            # 添加autosize属性确保适应容器
            vegalite_spec["autosize"] = {
                "type": "fit",
                "contains": "padding",
                "resize": True
            }
            
            # 检测图表类型，为不同类型的图表设置不同的边距
            chart_type = ""
            if "mark" in vegalite_spec:
                if isinstance(vegalite_spec["mark"], dict):
                    chart_type = vegalite_spec["mark"].get("type", "")
                else:
                    chart_type = vegalite_spec["mark"]
            
            # 特殊处理热力图
            if chart_type == "rect" and "Promo code usage by category" in vegalite_config_path:
                print(f"发现热力图: {vegalite_config_path}")
                # 强制设置固定高度，确保热力图显示完整
                vegalite_spec["width"] = 500
                vegalite_spec["height"] = 300
                # 确保热力图的文本可见
                if "encoding" in vegalite_spec and "text" in vegalite_spec["encoding"]:
                    if "mark" in vegalite_spec:
                        if isinstance(vegalite_spec["mark"], str):
                            vegalite_spec["mark"] = {
                                "type": "rect",
                                "tooltip": True
                            }
                        elif isinstance(vegalite_spec["mark"], dict):
                            vegalite_spec["mark"]["tooltip"] = True
                    
                    # 添加标签层来显示频率数字
                    vegalite_spec["layer"] = [
                        {"mark": "rect"},
                        {
                            "mark": {
                                "type": "text",
                                "color": "white",
                                "font": "sans-serif",
                                "fontSize": 14,
                                "fontWeight": "bold"
                            },
                            "encoding": {
                                "text": {"field": "Frequency", "type": "quantitative"},
                                "color": {
                                    "condition": {
                                        "test": "datum.Frequency < 10",
                                        "value": "black"
                                    },
                                    "value": "white"
                                }
                            }
                        }
                    ]
                    
                # 为热力图设置更大的边距
                if "config" not in vegalite_spec:
                    vegalite_spec["config"] = {}
                if "padding" not in vegalite_spec["config"]:
                    vegalite_spec["config"]["padding"] = {}
                
                vegalite_spec["config"]["padding"] = {
                    "left": 80,
                    "bottom": 50,
                    "top": 50,
                    "right": 30
                }
            
            # 为柱状图和直方图设置更大的边距
            elif chart_type in ["bar", "histogram"]:
                # 设置足够大的左侧和底部边距
                if "config" not in vegalite_spec:
                    vegalite_spec["config"] = {}
                if "padding" not in vegalite_spec["config"]:
                    vegalite_spec["config"]["padding"] = {}
                
                vegalite_spec["config"]["padding"] = {
                    "left": 50,  # 增加左侧边距，确保y轴标签显示
                    "bottom": 30, # 增加底部边距，确保x轴标签显示
                    "top": 60,    # 为图例保留空间
                    "right": 20   # 右侧边距
                }
            else:
                # 其他图表类型使用标准边距
                if "config" not in vegalite_spec:
                    vegalite_spec["config"] = {}
                if "padding" not in vegalite_spec["config"]:
                    vegalite_spec["config"]["padding"] = {}
                
                vegalite_spec["config"]["padding"] = {
                    "left": 20,
                    "bottom": 20,
                    "top": 60,  # 为图例保留空间
                    "right": 20
                }
            
            # 改进x轴标签显示
            if "encoding" in vegalite_spec:
                # 如果有x轴编码，改进其标签的显示
                if "x" in vegalite_spec["encoding"]:
                    # 检查是否是名义型数据
                    if vegalite_spec["encoding"]["x"].get("type") == "nominal":
                        # 添加轴配置以改善标签显示
                        vegalite_spec["encoding"]["x"]["axis"] = {
                            "labelAngle": 0,  # 标签不旋转
                            "labelOverlap": False,  # 不允许标签重叠
                            "labelLimit": 150  # 增加标签文本长度限制
                        }
                
                # 处理图例配置，避免与图表重叠
                if "color" in vegalite_spec["encoding"]:
                    # 确保图例位置合理
                    vegalite_spec["encoding"]["color"]["legend"] = {
                        "orient": "top",  # 将图例放在顶部
                        "direction": "horizontal",  # 水平排列图例项
                        "titlePadding": 10,
                        "labelLimit": 200,
                        "symbolSize": 100
                    }
            
            # 确保配置包含必要的配置项
            if "config" not in vegalite_spec:
                vegalite_spec["config"] = {}
            
            # 添加axis配置以改善所有坐标轴的显示
            if "axis" not in vegalite_spec["config"]:
                vegalite_spec["config"]["axis"] = {}
            
            # 确保坐标轴标签不会被截断
            vegalite_spec["config"]["axis"].update({
                "labelLimit": 200,  # 增加所有标签的文本长度限制
                "labelFontSize": 12,  # 标签字体大小
                "titleFontSize": 14,  # 坐标轴标题字体大小
                "labelPadding": 8    # 标签与轴线的距离
            })
            
            # 获取编码后的相对路径
            relative_img_path = convert_to_relative_path(img_path)
            
            # 保存配置信息
            chart_configs.append({
                "chartId": chart_id,
                "vegaliteSpec": vegalite_spec,
                "imgPath": relative_img_path
            })
            
            # 在图表对象上添加chart_id属性，以便模板函数使用
            chart["chart_id"] = chart_id
            # 标记为Vega-Lite图表
            chart["is_vegalite"] = True
            
            print(f"已处理Vega-Lite配置: {os.path.basename(vegalite_config_path)} -> chart_id: {chart_id}")
            
        except Exception as e:
            print(f"读取Vega-Lite配置文件失败: {vegalite_config_path}")
            print(f"错误详情: {str(e)}")
            print(f"确保文件存在且是有效的JSON格式")

# 生成Vega-Lite渲染脚本
def generate_vegalite_script(chart_configs):
    """
    根据图表配置生成Vega-Lite渲染脚本
    """
    if not chart_configs:
        return ""
        
    chart_script = """
    // 初始化所有图表
    document.addEventListener('DOMContentLoaded', function() {
        console.log('初始化所有Vega-Lite图表...');
        
        // 通用配置
        const vegaOptions = {
            renderer: 'canvas',
            actions: false, // 禁用所有导出功能按钮
            downloadFileName: 'chart',
            config: {
                axis: {
                    labelFontSize: 12,
                    titleFontSize: 13,
                    labelOverlap: true,
                    labelLimit: 200,
                    labelPadding: 8,
                    grid: true,
                    gridColor: '#f0f0f0',
                    tickCount: 5
                },
                legend: {
                    labelFontSize: 12,
                    titleFontSize: 13,
                    orient: 'top',
                    direction: 'horizontal',
                    symbolSize: 80,
                    labelLimit: 250,
                    padding: 10,
                    offset: 5
                },
                title: {
                    fontSize: 14,
                    fontWeight: 'bold',
                    anchor: 'middle',
                    font: 'sans-serif'
                },
                view: {
                    stroke: 'transparent',
                    strokeWidth: 0,
                    continuousHeight: 300,
                    continuousWidth: 400
                },
                range: {
                    category: ['#4169E1', '#FF6347', '#32CD32', '#FFD700', '#9370DB', '#4682B4', '#FF7F50', '#66CDAA']
                },
                mark: {
                    tooltip: true,
                    clip: true,
                    fontSize: 12,
                    font: 'sans-serif'
                },
                bar: {
                    cornerRadius: 0,
                    cornerRadiusTopLeft: 3,
                    cornerRadiusTopRight: 3
                },
                autosize: {
                    type: 'fit',
                    contains: 'padding',
                    resize: true
                },
                padding: {left: 10, right: 10, top: 60, bottom: 10}
            }
        };
        
        // 添加自定义CSS样式，修复图例问题
        const styleEl = document.createElement('style');
        styleEl.textContent = `
            .chart-container {
                position: relative;
                min-height: 450px !important;
                overflow: visible !important;
            }
            .vega-embed {
                width: 100%;
                height: 100%;
                position: relative;
                overflow: visible !important;
            }
            /* 确保图例不会溢出容器 */
            .vega-embed .vega-bindings {
                position: absolute;
                top: 5px;
                right: 5px;
            }
            /* 图例样式优化 */
            .vega-embed .role-legend {
                transform: translate(0, -40px) !important;
            }
            .vega-embed .role-legend-entry .role-legend-symbol {
                fill-opacity: 0.8 !important;
            }
            .vega-embed .role-legend-entry:hover .role-legend-symbol {
                fill-opacity: 1 !important;
                stroke-width: 1.5;
            }
            /* 确保坐标轴标签可见 */
            .vega-embed .role-axis-label {
                font-weight: normal;
                font-size: 12px;
            }
            /* 确保直方图和柱状图完全显示 */
            .vega-embed .mark-rect {
                shape-rendering: crispEdges;
            }
            /* 增加图表视图区域的内边距 */
            .vega-embed .role-frame {
                overflow: visible !important;
            }
        `;
        document.head.appendChild(styleEl);
    """
    
    # 添加所有图表配置并初始化
    for i, config in enumerate(chart_configs):
        # 将Python字典转换为JSON字符串
        chart_id = config['chartId']
        json_str = json.dumps(config['vegaliteSpec'])
        chart_script += f"""
        // 图表 {i+1}: {chart_id}
        (function() {{
            const chartId = '{chart_id}';
            const element = document.getElementById(chartId);
            if (element) {{
                console.log('正在渲染图表:', chartId);
                const vegaSpec = {json_str};
                
                // 确保容器有足够的高度
                element.style.minHeight = '450px';
                
                // 为热力图增加额外高度
                if (chartId === 'vegalite_chart_6') {{
                    console.log('设置热力图特殊高度:', chartId);
                    element.style.minHeight = '500px';
                    element.style.height = '500px';
                    // 确保父容器也有足够的高度
                    const parent = element.closest('.chart-group-item');
                    if (parent) {{
                        parent.style.minHeight = '520px';
                    }}
                    // 增加父容器的宽度
                    const gridContainer = element.closest('.chart-group-grid');
                    if (gridContainer) {{
                        gridContainer.style.minHeight = '520px';
                    }}
                }}
                
                vegaEmbed('#' + chartId, vegaSpec, vegaOptions)
                    .then(function(result) {{
                        console.log('图表渲染成功:', chartId);
                        window.chartInstances = window.chartInstances || {{}};
                        window.chartInstances[chartId] = result;
                        
                        // 检查图例位置，避免重叠
                        setTimeout(() => {{
                            const legendElements = element.querySelectorAll('.role-legend');
                            if (legendElements.length > 0) {{
                                // 强制将图例移到顶部
                                legendElements.forEach(legend => {{
                                    // 获取当前transform
                                    const currentTransform = legend.getAttribute('transform');
                                    if (currentTransform && currentTransform.includes('translate')) {{
                                        // 提取当前x坐标
                                        const match = currentTransform.match(/translate\\\\(([^,]+),([^)]+)\\\\)/);
                                        if (match) {{
                                            const x = parseFloat(match[1]);
                                            // 强制将图例移到顶部，y坐标设为-40
                                            const newTransform = 'translate(' + x + ',-40)';
                                            legend.setAttribute('transform', newTransform);
                                        }}
                                    }}
                                }});
                            }}
                            
                            // 延迟调整图表大小，确保完全渲染
                            setTimeout(() => {{
                                if (result && result.view) {{
                                    // 强制重新调整大小并渲染
                                    result.view.resize().run();
                                    console.log('已调整图表大小:', chartId);
                                }}
                            }}, 300);
                        }}, 500);
                    }})
                    .catch(function(error) {{
                        console.error('图表渲染失败:', chartId, error);
                        const fallbackImg = element.getAttribute('data-fallback');
                        if (fallbackImg) {{
                            console.log('使用备用图片:', fallbackImg);
                            const img = document.createElement('img');
                            img.src = fallbackImg;
                            img.alt = '图表';
                            img.style.width = '100%';
                            img.style.height = 'auto';
                            element.innerHTML = '';
                            element.appendChild(img);
                        }}
                    }});
            }} else {{
                console.warn('找不到图表容器:', chartId);
            }}
        }})();
        """
    
    chart_script += """
        // 适应窗口大小调整
        window.addEventListener('resize', function() {
            if (window.chartInstances) {
                Object.values(window.chartInstances).forEach(function(chart) {
                    if (chart && chart.view) {
                        chart.view.resize().run();
                    }
                });
            }
        });
    });
    """
    
    return chart_script

def fill_template(sections, template_type="dashboard", query="", report_abstract=""):
    """根据章节数据填充HTML模板，生成报告"""
    if template_type == "dashboard":
        return generate_dashboard_template(sections, query, report_abstract)

def highlight_keywords(text, keywords=None):
    """
    对文本中的关键词进行高亮处理
    
    参数:
    - text: 要处理的文本
    - keywords: 关键词列表，如果为None则使用默认关键词
    
    返回:
    - 处理后的文本，带有HTML高亮标记
    """
    if not text:
        return ""
    
    # 如果没有提供关键词，使用默认关键词
    if keywords is None:
        keywords = [
            "增长", "下降", "上升", "趋势", "显著", "明显", 
            "突出", "重要", "关键", "异常", "高于", "低于",
            "最高", "最低", "增加", "减少", "变化", "稳定",
            "波动", "集中", "分散", "极值", "outlier", "异常值"
        ]
    
    from html import escape
    
    # 先进行HTML转义，避免注入
    escaped_text = escape(text)
    
    # 对每个关键词进行高亮处理
    for keyword in keywords:
        # 使用正则表达式进行大小写不敏感的替换
        import re
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        escaped_text = pattern.sub(f'<span class="highlight">{keyword}</span>', escaped_text)
    
    return escaped_text

def generate_dashboard_template(sections, query="", report_abstract=""):
    from html import escape
    
    # 处理图表配置，使用Vega-Lite
    chart_configs, chart_id_counter = prepare_vegalite_config(sections)
    
    # 输出配置情况
    print(f"生成了 {len(chart_configs)} 个Vega-Lite图表配置")
    
    # 生成仪表盘图表面板
    panels_html = ""
    
    # 添加查询展示信息
    instruction_html = f'''
    <div class="instruction-card">
        <div class="instruction-icon">🔍</div>
        <div class="instruction-content">
            <h3>用户查询</h3>
            <p class="query-text">{escape(query) if query else "数据分析报告"}</p>
        </div>
    </div>
    '''
    
    # 添加摘要容器（如果有摘要）
    abstract_html = ""
    if report_abstract:
        abstract_html = f'''
        <div class="abstract-container">
            <h2 class="abstract-title">摘要</h2>
            <div class="abstract-content">
                <p>{highlight_keywords(report_abstract)}</p>
        </div>
    </div>
    '''
    
    # 生成章节导航
    toc_html = '<div class="toc-container">\n<h3>目录</h3>\n<ul class="toc-list">\n'
    for i, section in enumerate(sections, 1):
        title = section.get("title", "")
        toc_html += f'<li><a href="#section-{i}" class="toc-link">{i}. {escape(title)}</a></li>\n'
        
        # 添加子章节到目录
        subsections = section.get("subsections", [])
        if subsections:
            toc_html += '<ul class="toc-sublist">\n'
            for j, subsection in enumerate(subsections, 1):
                subsection_title = subsection.get("title", "")
                toc_html += f'<li><a href="#subsection-{i}-{j}" class="toc-sublink">{i}.{j} {escape(subsection_title)}</a></li>\n'
            toc_html += '</ul>\n'
            
    toc_html += '</ul>\n</div>\n'
    
    # 生成各章节内容
    for i, section in enumerate(sections, 1):
        title = section.get("title", "")
        charts = section.get("charts", [])
        summary = section.get("summary", "")
        subsections = section.get("subsections", [])
        
        # 创建子章节标题到图表的映射
        subsection_charts = {}
        for chart_item in charts:
            if isinstance(chart_item, dict):
                if chart_item.get("is_chart_group", False):
                    group_charts = chart_item.get("charts", [])
                    if group_charts and len(group_charts) > 0:
                        subsection_title = group_charts[0].get("subsection_title", "")
                        if subsection_title:
                            if subsection_title not in subsection_charts:
                                subsection_charts[subsection_title] = []
                            subsection_charts[subsection_title].append(chart_item)
                else:
                    subsection_title = chart_item.get("subsection_title", "")
                    if subsection_title:
                        if subsection_title not in subsection_charts:
                            subsection_charts[subsection_title] = []
                        subsection_charts[subsection_title].append(chart_item)
        
        # 添加从上一个章节到当前章节的过渡文本（仅从第二个章节开始）
        if i > 1 and section.get("intro_text"):
            intro_text = section.get("intro_text", "")
            panels_html += f'''
            <div class="section-transition">
                <p>{escape(intro_text)}</p>
            </div>
            '''
        
        # 章节面板开始
        panels_html += f'''
        <div id="section-{i}" class="section-panel">
            <div class="section-header">
                <div class="section-number">{i}</div>
                <h2 class="section-title">{escape(title)}</h2>
                <div class="section-actions">
                    <button class="section-action" title="折叠章节" onclick="toggleSection(this)"><i class="icon">▼</i></button>
                </div>
            </div>
            <div class="section-content">
        '''
        
        # 添加子章节内容及对应的图表
        for j, subsection in enumerate(subsections, 1):
            subsection_title = subsection.get("title", "")
            subsection_content = subsection.get("content", [])
            
            panels_html += f'''
            <div id="subsection-{i}-{j}" class="subsection-panel">
                <h3 class="subsection-title">{escape(subsection_title)}</h3>
                <div class="subsection-content">
            '''
            
            # 添加子章节正文
            if subsection_content:
                for paragraph in subsection_content:
                    panels_html += f'<p>{escape(paragraph)}</p>\n'
                    
            panels_html += '</div>\n'
        
            # 添加该子章节对应的图表
            if subsection_title in subsection_charts:
                for chart_item in subsection_charts[subsection_title]:
                    # 确定图表类型并处理
                    if isinstance(chart_item, dict) and chart_item.get("is_chart_group", False):
                        # 处理图表组
                        group_charts = chart_item.get("charts", [])
                        group_caption = chart_item.get("group_caption", "")
                        
                        # 拆分关键点
                        key_points = []
                        if group_caption:
                            # 尝试从caption中提取key points
                            lines = group_caption.split('\n')
                            for line in lines:
                                line = line.strip()
                                if 'key point' in line.lower():
                                    key_points.append(line)
                        
                        print(f"生成图表组模板，包含 {len(group_charts)} 个图表, caption: '{group_caption[:50]}...'")
                        
                        # 处理组标题 - 只有当group_caption不是完全由key points组成时才设置
                        group_title = ""
                        
                        # 检查是否是特殊格式的图表组标题，如果是则不显示标题
                        if group_caption.startswith("图表组:"):
                            group_title = ""  # 将标题设为空，不显示标题条
                        else:
                            # 检查是否所有行都是key points
                            all_key_points = True
                            non_empty_lines = [line.strip() for line in group_caption.split('\n') if line.strip()]
                            for line in non_empty_lines:
                                if 'key point' not in line.lower():
                                    all_key_points = False
                                    break
                            
                            if not all_key_points:
                                # 如果不是全部是key points，尝试找一个非key point的行作为标题
                                for line in group_caption.split('\n'):
                                    if 'key point' not in line.lower() and line.strip():
                                        group_title = line.strip()
                                        break
                        
                        # 创建图表组容器
                        panels_html += f'''
                        <div class="chart-group">
                        '''
                        
                        # 只有当有组标题时才添加标题区域
                        if group_title:
                            panels_html += f'''
                            <div class="chart-group-header">
                                <h4 class="chart-group-title">{escape(group_title)}</h4>
                            </div>
                            '''
                        
                        panels_html += f'''
                            <div class="chart-group-container">
                                <div class="chart-group-grid chart-group-{len(group_charts)}">
                        '''
                        
                        # 添加组内所有图表
                        for group_chart in group_charts:
                            img = group_chart.get("img", "")
                            alt_text = group_chart.get("alt_text", "图表")
                            is_vegalite = group_chart.get("is_vegalite", False)
                            
                            panels_html += '<div class="chart-group-item">\n'
                            
                            # 获取相对路径
                            relative_img_path = convert_to_relative_path(img)
                            
                            if is_vegalite:
                                chart_id = group_chart.get("chart_id", "")
                                print(f"  添加Vega-Lite图表: {chart_id}, 图片备用: {relative_img_path}")
                                panels_html += f'<div class="chart-wrapper"><div id="{chart_id}" data-fallback="{relative_img_path}" class="chart-container"></div></div>\n'
                            else:
                                # 使用编码后的相对路径
                                panels_html += f'<div class="chart-wrapper"><img src="{relative_img_path}" alt="{escape(alt_text)}"></div>\n'
                            
                            panels_html += '</div>\n'
                        
                        # 结束图表组网格
                        panels_html += '</div>\n'
                        
                        # 如果有关键点，添加关键点列表
                        if key_points:
                            panels_html += '<div class="key-points-container">\n'
                            panels_html += '<h4 class="key-points-title">Key Points</h4>\n'
                            panels_html += '<ul class="key-points-list">\n'
                            for point in key_points:
                                # 移除"key point1: "等前缀
                                point_text = re.sub(r'^key point\d+:\s*', '', point)
                                panels_html += f'<li class="key-point">{highlight_keywords(point_text)}</li>\n'
                            panels_html += '</ul>\n'
                            panels_html += '</div>\n'
                        
                        # 关闭图表组容器 (只关闭必要的标签)
                        panels_html += '</div>\n</div>\n'
                    
                    elif isinstance(chart_item, dict):
                        # 处理单个图表
                        caption = chart_item.get("caption", "")
                        img = chart_item.get("img", "")
                        alt_text = chart_item.get("alt_text", "图表")
                        is_vegalite = chart_item.get("is_vegalite", False)
                        
                        # 拆分关键点
                        key_points = []
                        if caption:
                            # 尝试从caption中提取key points
                            lines = caption.split('\n')
                            for line in lines:
                                line = line.strip()
                                if 'key point' in line.lower():
                                    key_points.append(line)
                        
                        # 处理标题
                        chart_title = ""
                        # 检查是否所有行都是key points
                        all_key_points = True
                        non_empty_lines = [line.strip() for line in caption.split('\n') if line.strip()]
                        for line in non_empty_lines:
                            if 'key point' not in line.lower():
                                all_key_points = False
                                break
                        
                        if not all_key_points:
                            # 如果不是全部是key points，尝试找一个非key point的行作为标题
                            for line in caption.split('\n'):
                                if 'key point' not in line.lower() and line.strip():
                                    chart_title = line.strip()
                                    break
                        
                        panels_html += f'''
                        <div class="chart-single">
                        '''
                        
                        # 只有当有标题时才添加标题区域
                        if chart_title:
                            panels_html += f'''
                            <div class="chart-single-header">
                                <h4 class="chart-single-title">{escape(chart_title)}</h4>
                            </div>
                            '''
                        
                        panels_html += f'''
                            <div class="chart-single-container">
                        '''
                        
                        # 添加图表
                        panels_html += '<div class="chart-wrapper">\n'
                        if is_vegalite:
                            chart_id = chart_item.get("chart_id", "")
                            print(f"  添加单个Vega-Lite图表: {chart_id}, 图片备用: {img}")
                            panels_html += f'<div id="{chart_id}" data-fallback="{img}" class="chart-container"></div>\n'
                        else:
                            # 使用编码后的相对路径
                            relative_img_path = convert_to_relative_path(img)
                            panels_html += f'<img src="{relative_img_path}" alt="{escape(alt_text)}">\n'
                        panels_html += '</div>\n'
                        
                        # 添加关键点（如果有）
                        if key_points:
                            panels_html += '<div class="key-points-container">\n'
                            panels_html += '<h4 class="key-points-title">Key Points</h4>\n'
                            panels_html += '<ul class="key-points-list">\n'
                            for point in key_points:
                                # 移除"key point1: "等前缀
                                point_text = re.sub(r'^key point\d+:\s*', '', point)
                                panels_html += f'<li class="key-point">{highlight_keywords(point_text)}</li>\n'
                            panels_html += '</ul>\n'
                            panels_html += '</div>\n'
                        
                        panels_html += '</div>\n</div>\n'
            
            # 关闭子章节面板
            panels_html += '</div>\n'
        
        # 处理未关联到子章节的图表
        orphan_charts = []
        for chart_item in charts:
            if isinstance(chart_item, dict):
                if chart_item.get("is_chart_group", False):
                    group_charts = chart_item.get("charts", [])
                    if not group_charts or len(group_charts) == 0 or not group_charts[0].get("subsection_title", ""):
                        orphan_charts.append(chart_item)
                elif not chart_item.get("subsection_title", ""):
                    orphan_charts.append(chart_item)
        
        # 添加没有子章节的独立图表
        if orphan_charts:
            for chart_item in orphan_charts:
                if isinstance(chart_item, dict):
                    if not chart_item.get("is_chart_group", False):
                        # 处理单个图表
                        caption = chart_item.get("caption", "")
                        img = chart_item.get("img", "")
                        alt_text = chart_item.get("alt_text", "图表")
                        is_vegalite = chart_item.get("is_vegalite", False)
                        
                        # 拆分关键点
                        key_points = []
                        if caption:
                            # 尝试从caption中提取key points
                            lines = caption.split('\n')
                            for line in lines:
                                line = line.strip()
                                if 'key point' in line.lower():
                                    key_points.append(line)
                        
                        # 处理标题
                        chart_title = ""
                        # 检查是否所有行都是key points
                        all_key_points = True
                        non_empty_lines = [line.strip() for line in caption.split('\n') if line.strip()]
                        for line in non_empty_lines:
                            if 'key point' not in line.lower():
                                all_key_points = False
                                break
                        
                        if not all_key_points:
                            # 如果不是全部是key points，尝试找一个非key point的行作为标题
                            for line in caption.split('\n'):
                                if 'key point' not in line.lower() and line.strip():
                                    chart_title = line.strip()
                                    break
                        
                        panels_html += f'''
                        <div class="chart-single">
                        '''
                        
                        # 只有当有标题时才添加标题区域
                        if chart_title:
                            panels_html += f'''
                            <div class="chart-single-header">
                                <h4 class="chart-single-title">{escape(chart_title)}</h4>
                            </div>
                            '''
                        
                        panels_html += f'''
                            <div class="chart-single-container">
                        '''
                        
                        # 添加图表
                        panels_html += '<div class="chart-wrapper">\n'
                        if is_vegalite:
                            chart_id = chart_item.get("chart_id", "")
                            print(f"  添加单个Vega-Lite图表: {chart_id}, 图片备用: {img}")
                            panels_html += f'<div id="{chart_id}" data-fallback="{img}" class="chart-container"></div>\n'
                        else:
                            # 使用编码后的相对路径
                            relative_img_path = convert_to_relative_path(img)
                            panels_html += f'<img src="{relative_img_path}" alt="{escape(alt_text)}">\n'
                        panels_html += '</div>\n'
                        
                        # 添加关键点（如果有）
                        if key_points:
                            panels_html += '<div class="key-points-container">\n'
                            panels_html += '<h4 class="key-points-title">Key Points</h4>\n'
                            panels_html += '<ul class="key-points-list">\n'
                            for point in key_points:
                                # 移除"key point1: "等前缀
                                point_text = re.sub(r'^key point\d+:\s*', '', point)
                                panels_html += f'<li class="key-point">{highlight_keywords(point_text)}</li>\n'
                            panels_html += '</ul>\n'
                            panels_html += '</div>\n'
                        
                        panels_html += '</div>\n</div>\n'
        
        # 添加章节总结（移动到章节最末尾）
        if summary:
            panels_html += f'''
            <div id="section-{i}-summary" class="section-summary">
                <h3 class="summary-title">Summary</h3>
                <div class="summary-content">
                    <p>{highlight_keywords(summary)}</p>
                </div>
            </div>
            '''
        
        # 结束章节
        panels_html += '</div>\n</div>\n'
    
    # 生成完整HTML
    css = get_css()
    js = get_js()
    vegalite_script = generate_vegalite_script(chart_configs)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据分析报告</title>
    <style>
    {css}
    </style>
    <!-- Vega & Vega-Lite -->
    <script src="https://cdn.jsdelivr.net/npm/vega@5.25.0"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-lite@5.16.0"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-embed@6.22.2"></script>
</head>
<body>
    <header>
        <div class="header-content">
            <h1>数据分析报告</h1>
            <div class="header-controls">
                <button id="expandAllBtn">展开全部</button>
                <button id="collapseAllBtn">折叠全部</button>
                <button id="printBtn">打印报告</button>
            </div>
        </div>
    </header>
    
    <div class="container">
        <aside class="sidebar">
            {toc_html}
        </aside>
        
        <main class="content">
            {instruction_html}
            
            {abstract_html}
            
            <div class="panels-container">
                {panels_html}
            </div>
        </main>
    </div>
    
    <script>
    {js}
    </script>
    
    <!-- Vega-Lite图表初始化 -->
    <script>
    {vegalite_script}
    </script>
</body>
</html>'''
    
    return html

def get_css():
    """获取CSS样式"""
    return '''
    :root {
        --primary-color: #4169E1;
        --primary-light: #E6ECFF;
        --secondary-color: #6495ED;
        --accent-color: #1E90FF;
        --text-color: #333;
        --light-bg: #f9f9f9;
        --border-color: #ddd;
        --shadow-color: rgba(0,0,0,0.1);
        --success-color: #4CAF50;
        --info-color: #2196F3;
        --warning-color: #FF9800;
        --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        --transition-speed: 0.3s;
    }
    
    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }
    
    body {
        font-family: var(--font-main);
        line-height: 1.6;
        color: var(--text-color);
        background-color: var(--light-bg);
        padding-top: 60px;
        overflow-x: hidden;
    }
    
    a {
        color: var(--accent-color);
        text-decoration: none;
    }
    
    a:hover {
        text-decoration: underline;
    }
    
    /* 头部样式 */
    header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: white;
        box-shadow: 0 2px 4px var(--shadow-color);
        z-index: 1000;
        height: 60px;
        display: flex;
        align-items: center;
    }
    
    .header-content {
        width: 100%;
        max-width: 1600px;  /* 匹配容器最大宽度 */
        margin: 0 auto;
        padding: 0 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .header-controls button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        padding: 8px 12px;
        margin-left: 10px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        transition: background-color var(--transition-speed);
    }
    
    .header-controls button:hover {
        background-color: var(--secondary-color);
    }
    
    /* 容器布局 */
    .container {
        display: flex;
        max-width: 1600px;  /* 增加最大宽度 */
        margin: 0 auto;
        min-height: calc(100vh - 120px);
        padding: 0 20px;
    }
    
    /* 侧边栏样式 */
    .sidebar {
        width: 15%;  /* 减小侧边栏宽度 */
        min-width: 180px;
        max-width: 220px;  /* 限制最大宽度 */
        background-color: white;
        box-shadow: 0 1px 3px var(--shadow-color);
        position: sticky;
        top: 60px;
        height: calc(100vh - 60px);
        overflow-y: auto;
        padding: 20px 0;
        z-index: 900;
    }
    
    /* 主内容区域 */
    .content {
        flex: 1;
        padding: 20px 20px 20px 40px;  /* 增加左侧内边距 */
        overflow-x: hidden;
        min-width: 0;  /* 防止内容溢出 */
        width: 85%;  /* 增加内容区域宽度 */
    }
    
    /* 目录样式 */
    .toc-container {
        padding: 0 15px 20px;
    }
    
    .toc-container h3 {
        font-size: 18px;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
    }
    
    .toc-list {
        list-style-type: none;
    }
    
    .toc-link {
        display: block;
        padding: 8px 0;
        color: var(--text-color);
        font-weight: 500;
        transition: color var(--transition-speed);
    }
    
    .toc-link:hover {
        color: var(--accent-color);
    }
    
    .toc-sublist {
        list-style-type: none;
        margin-left: 15px;
    }
    
    .toc-sublink {
        display: block;
        padding: 6px 0;
        color: var(--text-color);
        font-size: 14px;
        transition: color var(--transition-speed);
    }
    
    .toc-sublink:hover {
        color: var(--accent-color);
    }
    
    /* 提示卡片 */
    .instruction-card {
        display: flex;
        background-color: white;
        border-radius: 6px;
        margin-bottom: 30px;
        padding: 15px;
        box-shadow: 0 1px 3px var(--shadow-color);
    }
    
    .instruction-icon {
        font-size: 24px;
        margin-right: 15px;
        color: var(--info-color);
    }
    
    .instruction-content h3 {
        margin-bottom: 8px;
        color: var(--info-color);
    }
    
    .query-text {
        font-size: 16px;
        font-weight: 500;
        color: var(--primary-color);
        background-color: var(--primary-light);
        padding: 10px 15px;
        border-radius: 4px;
        margin: 8px 0;
        border-left: 3px solid var(--primary-color);
    }
    
    /* 章节样式 */
    .section-panel {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px var(--shadow-color);
        margin-bottom: 30px;
        overflow: hidden;
    }
    
    .section-header {
        padding: 15px 20px;
        background-color: white;
        border-bottom: 2px solid var(--primary-color);
        color: var(--text-color);
        display: flex;
        align-items: center;
        position: relative;
    }
    
    .section-number {
        background-color: var(--primary-color);
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 15px;
    }
    
    .section-title {
        flex: 1;
        font-size: 20px;
        font-weight: 500;
        color: var(--primary-color);
    }
    
    .section-actions {
        position: absolute;
        right: 20px;
        top: 15px;
    }
    
    .section-action {
        background: none;
        border: none;
        color: var(--primary-color);
        cursor: pointer;
        font-size: 16px;
    }
    
    .section-content {
        padding: 20px;
    }
    
    /* 子章节样式 */
    .subsection-panel {
        margin-bottom: 25px;
    }
    
    .subsection-title {
        font-size: 18px;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
        color: var(--secondary-color);
    }
    
    .subsection-content p {
        margin-bottom: 15px;
    }
    
    /* 过渡文本 */
    .section-transition {
        padding: 15px 0;
        margin-bottom: 20px;
        color: var(--text-color);
        font-style: italic;
        border-bottom: 1px dashed var(--border-color);
    }
    
    /* 图表组 */
    .chart-group {
        background-color: white;
        border-radius: 6px;
        margin-bottom: 25px;
        box-shadow: 0 1px 3px var(--shadow-color);
    }
    
    .chart-group-header {
        padding: 15px;
        border-bottom: 1px solid var(--border-color);
    }
    
    .chart-group-title {
        font-size: 16px;
        font-weight: 500;
        margin: 0;
        color: var(--secondary-color);
    }
    
    .chart-group-container {
        padding: 15px;
        width: 100%;
        overflow: visible;
    }
    
    .chart-group-grid {
        display: grid;
        gap: 20px;
        width: 100%;
    }
    
    .chart-group-1 {
        grid-template-columns: 1fr;
    }
    
    .chart-group-2 {
        grid-template-columns: repeat(2, minmax(500px, 1fr));  /* 增加最小宽度 */
    }
    
    .chart-group-3 {
        grid-template-columns: repeat(3, minmax(400px, 1fr));  /* 增加最小宽度 */
    }
    
    .chart-group-4 {
        grid-template-columns: repeat(2, minmax(500px, 1fr));  /* 增加最小宽度 */
    }
    
    /* 单个图表 */
    .chart-single {
        background-color: white;
        border-radius: 6px;
        margin-bottom: 25px;
        box-shadow: 0 1px 3px var(--shadow-color);
    }
    
    .chart-single-header {
        padding: 15px;
        border-bottom: 1px solid var(--border-color);
    }
    
    .chart-single-title {
        font-size: 16px;
        font-weight: 500;
        margin: 0;
        color: var(--secondary-color);
    }
    
    .chart-single-container {
        padding: 15px;
    }
    
    /* 图表容器 */
    .chart-wrapper {
        width: 100%;
        margin-bottom: 15px;
        overflow: visible;
        border-radius: 4px;
        min-height: 450px;
    }
    
    .chart-wrapper img {
        width: 100%;
        height: auto;
        display: block;
    }
    
    .chart-container {
        width: 100%;
        min-height: 450px;
        position: relative;
        overflow: visible !important;
    }
    
    /* 确保热力图正确显示 */
    #vegalite_chart_6 {
        min-height: 500px !important;
        height: 500px !important;
    }
    
    /* 确保Vega-Lite图表正确显示 */
    .vega-embed {
        width: 100%;
        height: 100%;
        position: relative;
        overflow: visible !important;
    }
    
    .vega-embed .vega-actions {
        position: absolute;
        top: -40px;
        right: 0;
        z-index: 1000;
    }
    
    /* 关键点样式 */
    .key-points-container {
        padding: 15px;
        margin-top: 15px;
        border-top: 1px solid var(--border-color);
    }
    
    .key-points-title {
        font-size: 16px;
        font-weight: 500;
        margin-bottom: 12px;
        color: var(--secondary-color);
    }
    
    .key-points-list {
        list-style-type: none;
    }
    
    .key-point {
        position: relative;
        padding-left: 20px;
        margin-bottom: 10px;
    }
    
    .key-point:before {
        content: "•";
        position: absolute;
        left: 0;
        color: var(--accent-color);
        font-weight: bold;
    }
    
    /* 章节总结样式 */
    .section-summary {
        padding: 20px 0;
        margin-top: 25px;
        border-top: 1px dashed var(--border-color);
    }
    
    .summary-title {
        font-size: 18px;
        margin-bottom: 12px;
        color: var(--primary-color);
    }
    
    .summary-content {
        color: var(--text-color);
    }
    
    /* 关键词高亮 */
    .highlight, .keyword {
        color: var(--accent-color);
        font-weight: 500;
    }
    
    /* 页脚样式 */
    footer {
        background-color: white;
        color: var(--text-color);
        padding: 20px 0;
        border-top: 1px solid var(--border-color);
    }
    
    .footer-content {
        max-width: 1600px;  /* 匹配容器最大宽度 */
        margin: 0 auto;
        text-align: center;
        padding: 0 20px;
        color: #777;
        font-size: 14px;
    }
    
    /* 响应式样式 */
    @media (max-width: 1400px) {
        .chart-group-2, .chart-group-3, .chart-group-4 {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    
    @media (max-width: 992px) {
        .container {
            flex-direction: column;
            padding: 0 10px;
        }
        
        .sidebar {
            width: 100%;
            max-width: none;
            position: static;
            height: auto;
            margin-bottom: 20px;
        }
        
        .content {
            width: 100%;
            padding: 20px;
        }
        
        .chart-group-2, .chart-group-3, .chart-group-4 {
            grid-template-columns: 1fr;
        }
    }
    
    /* 打印样式 */
    @media print {
        body {
            padding-top: 0;
        }
        
        header, .sidebar, footer, .section-actions {
            display: none;
        }
        
        .container {
            display: block;
        }
        
        .content {
            width: 100%;
            padding: 0;
        }
        
        .section-panel {
            break-inside: avoid;
            margin-bottom: 30px;
            box-shadow: none;
            border: 1px solid #ddd;
        }
    }
    
    /* 摘要容器 */
    .abstract-container {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px var(--shadow-color);
        margin-bottom: 30px;
        padding: 25px;
        border-left: 4px solid var(--success-color);
    }
    
    .abstract-title {
        font-size: 22px;
        font-weight: 600;
        margin-bottom: 15px;
        color: var(--success-color);
        display: flex;
        align-items: center;
    }
    
    .abstract-title:before {
        content: "📋";
        margin-right: 10px;
        font-size: 20px;
    }
    
    .abstract-content {
        color: var(--text-color);
        line-height: 1.7;
    }
    
    .abstract-content p {
        margin: 0;
        font-size: 16px;
    }
    '''

def get_js():
    """获取JavaScript脚本"""
    return '''
    // 折叠展开功能
    function toggleSection(button) {
        const section = button.closest('.section-panel');
        const content = section.querySelector('.section-content');
        const icon = button.querySelector('.icon');
        
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.textContent = '▼';
            button.setAttribute('title', '折叠章节');
        } else {
            content.style.display = 'none';
            icon.textContent = '►';
            button.setAttribute('title', '展开章节');
        }
    }
    
    // 折叠全部章节
    document.getElementById('collapseAllBtn').addEventListener('click', function() {
        document.querySelectorAll('.section-content').forEach(content => {
            content.style.display = 'none';
            const icon = content.parentElement.querySelector('.section-actions .icon');
            if (icon) icon.textContent = '►';
        });
    });
    
    // 展开全部章节
    document.getElementById('expandAllBtn').addEventListener('click', function() {
        document.querySelectorAll('.section-content').forEach(content => {
            content.style.display = 'block';
            const icon = content.parentElement.querySelector('.section-actions .icon');
            if (icon) icon.textContent = '▼';
        });
    });
    
    // 打印功能
    document.getElementById('printBtn').addEventListener('click', function() {
        window.print();
    });
    
    // 平滑滚动到锚点
    document.querySelectorAll('.toc-link, .toc-sublink').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
                
                // 确保目标章节展开
                const sectionPanel = targetElement.closest('.section-panel');
                if (sectionPanel) {
                    const content = sectionPanel.querySelector('.section-content');
                    const icon = sectionPanel.querySelector('.section-actions .icon');
                    if (content.style.display === 'none') {
                        content.style.display = 'block';
                        if (icon) icon.textContent = '▼';
                    }
                }
            }
        });
    });
    
    // 初始化时展开所有章节
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.section-content').forEach(content => {
            content.style.display = 'block';
        });
    });
    '''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate styled report from Markdown.')
    parser.add_argument('markdown_file', type=str, help='Path to the input Markdown file')
    parser.add_argument('--output', type=str, default='report_generated.html', help='Output HTML file name')
    parser.add_argument('--template', type=str, choices=['dashboard', 'article'], default='dashboard', help='Template style to use')
    parser.add_argument('--query', type=str, default='', help='User query to display in the report')
    args = parser.parse_args()

    # 获取输入文件的绝对路径
    md_path = os.path.abspath(args.markdown_file)
    
    if not os.path.exists(md_path):
        print(f"错误: 找不到输入文件 {md_path}")
        exit(1)
    
    # 确定输出路径 - 如果未指定目录，则放在与markdown同一目录
    output_path = args.output
    if not os.path.dirname(output_path):
        md_dir = os.path.dirname(md_path)
        output_path = os.path.join(md_dir, output_path)
    
    try:
        print(f"开始解析并生成报告...")
        print(f"输入文件: {md_path}")
        print(f"输出文件: {output_path}")
        print(f"使用模板: {args.template}")
        if args.query:
            print(f"用户查询: {args.query}")
        
        # 解析Markdown文件
        sections, query_from_title, report_abstract = parse_markdown(md_path)
        
        if not sections:
            print("警告: 未找到任何章节数据。请检查Markdown文件格式。")
            exit(1)
            
        # 统计图表和图表组数量
        total_charts = 0
        total_groups = 0
        
        for section in sections:
            for chart in section.get("charts", []):
                if isinstance(chart, dict) and chart.get("is_chart_group", False):
                    total_groups += 1
                    total_charts += len(chart.get("charts", []))
                else:
                    total_charts += 1
        
        print(f"解析结果: {len(sections)}个章节, {total_charts}个图表, {total_groups}个图表组")
        
        # 确定最终使用的查询：优先使用命令行参数，否则使用从markdown标题中提取的查询
        final_query = args.query if args.query else query_from_title
        if query_from_title and not args.query:
            print(f"从markdown标题中提取到查询: {query_from_title}")
        
        # 生成HTML内容
        print("生成HTML报告...")
        html = fill_template(sections, args.template, final_query, report_abstract)
    
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 写入HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
        print(f"✅ 报告已成功生成: {output_path}")
        print(f"  - 包含 {len(sections)} 个章节")
        print(f"  - 包含 {total_charts} 个图表 ({total_groups} 个图表组)")
        print(f"  - 使用了 {args.template} 模板")
        
    except Exception as e:
        print(f"❌ 生成报告时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
