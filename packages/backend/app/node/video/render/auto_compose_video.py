"""
自动组装完整视频
读取JSON配置，自动在Root.tsx中注册VideoComposer完整视频

使用方法：
    python "infographic generation/auto_compose_video.py" --config generated_xxx.json
"""

import json
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

VIDEO_RUNTIME_BASE = Path(os.getenv("VIDEO_RUNTIME_BASE", "/workspace/video_runtime"))
DEFAULT_ANIMATED_OUTPUT_DIR = Path(
    os.getenv("VIDEO_ANIMATED_OUTPUT_BASE", str(VIDEO_RUNTIME_BASE / "claude_tsx_animated"))
)


def calculate_total_duration(config_data):
    """从JSON配置计算视频总时长（帧数）"""
    fps = config_data['meta']['fps']
    
    # 找到所有渲染场景（opening, chart, stat_cards, closing）
    all_scenes = [s for s in config_data['scenes'] 
                  if s['type'] in ['opening', 'chart', 'stat_cards', 'closing']]
    
    if not all_scenes:
        raise ValueError("配置文件中没有找到任何可渲染的场景")
    
    # 获取最后一个场景的结束时间（支持回退方案）
    last_scene = all_scenes[-1]
    
    # 尝试从 time_range 获取结束时间
    if 'time_range' in last_scene and isinstance(last_scene['time_range'], list) and len(last_scene['time_range']) >= 2:
        end_time = last_scene['time_range'][1]
    else:
        # 回退方案：从 narration 计算，或使用估算值
        if last_scene.get('narration') and isinstance(last_scene['narration'], list) and len(last_scene['narration']) > 0:
            last_narr = last_scene['narration'][-1]
            if 'time_end' in last_narr and isinstance(last_narr['time_end'], (int, float)):
                end_time = last_narr['time_end']
            else:
                # 估算：每个 narration 约 3 秒，每个场景至少 5 秒
                estimated_duration = len(last_scene['narration']) * 3.0
                # 计算前面所有场景的时间
                previous_time = sum(
                    max(5.0, len(s.get('narration', [])) * 3.0) 
                    for s in all_scenes[:-1]
                )
                end_time = previous_time + max(5.0, estimated_duration)
        else:
            # 完全没有时间信息，使用默认值
            end_time = len(all_scenes) * 5.0  # 每个场景默认 5 秒
    
    # 转换为帧数
    total_frames = round(end_time * fps)
    
    # 统计各类型场景数量
    scene_counts = {
        'opening': len([s for s in all_scenes if s['type'] == 'opening']),
        'chart': len([s for s in all_scenes if s['type'] == 'chart']),
        'stat_cards': len([s for s in all_scenes if s['type'] == 'stat_cards']),
        'closing': len([s for s in all_scenes if s['type'] == 'closing']),
    }
    
    return total_frames, scene_counts


def get_video_id_from_config(config_data):
    """从配置文件内容生成视频ID（基于meta.title）"""
    title = config_data.get('meta', {}).get('title', '')
    
    if title:
        # 从标题生成ID：移除特殊字符，将下划线替换为空格，转换为PascalCase
        # 例如: "Google Play Store Analysis" -> "GooglePlayStoreAnalysis"
        # 例如: "Exploring ART_AND_DESIGN Apps" -> "ExploringArtAndDesignApps"
        # Remotion要求：只能包含 a-z, A-Z, 0-9, CJK字符和连字符 -
        title_clean = title.replace('_', ' ')  # 先将下划线替换为空格
        title_clean = re.sub(r'[^\w\s]', '', title_clean)  # 移除其他特殊字符
        parts = title_clean.split()
        video_id = ''.join(word.capitalize() for word in parts if word)
        return video_id + 'FullVideo'
    else:
        # 如果没有title，回退到文件名方式
        return 'GeneratedFullVideo'


def get_component_prefix_from_config(config_data):
    """
    从配置文件内容生成组件前缀（基于meta.title）
    使用与 extract_dataset_name 相同的逻辑，确保命名一致
    """
    title = config_data.get('meta', {}).get('title', '')
    
    if title:
        # 使用与 extract_dataset_name 完全相同的逻辑
        # 去掉空格和特殊字符，只保留字母数字
        dataset_name = ''.join(c for c in title if c.isalnum())
        # 如果太长，截取前20个字符（与 extract_dataset_name 保持一致）
        if len(dataset_name) > 20:
            dataset_name = dataset_name[:20]
        return dataset_name
    else:
        return None


def get_config_import_name(video_id):
    """生成配置文件的import变量名"""
    # FullVideo-20260109-141432 -> config20260109141432Json
    # FlightDataFullVideo -> flightDataJson
    name = video_id.replace('FullVideo', '').replace('-', '').replace('_', '')
    if not name:
        return 'configJson'
    # 如果以数字开头，添加 'config' 前缀
    if name[0].isdigit():
        return 'config' + name + 'Json'
    return name[0].lower() + name[1:] + 'Json'


def extract_dataset_name_from_config(config_data: dict) -> str:
    """
    从配置文件中提取 dataset_name（用于组件命名）
    与 generate_with_claude.py 中的 extract_dataset_name 逻辑一致
    """
    video_meta = config_data.get('meta', {})
    title = video_meta.get('title', 'DataAnalysis')
    # 去掉空格和特殊字符，只保留字母数字
    dataset_name = ''.join(c for c in title if c.isalnum())
    # 如果太长，截取前20个字符
    if len(dataset_name) > 20:
        dataset_name = dataset_name[:20]
    return dataset_name


def scene_id_to_filename(
    scene_id: str, 
    dataset_name: str, 
    task_id: str = None, 
    is_animated: bool = True,
    needs_component: bool = None
) -> str:
    """
    从 scene_id 生成预期的文件名
    文件名规则: 
    - 图表场景: {dataset_name}_{scene_id转换为驼峰命名}_{task_id}Animated.tsx
    - 其他场景: {dataset_name}_{scene_id转换为驼峰命名}_{task_id}ComponentAnimated.tsx
    
    例如:
    - scene_opening -> Analyzeflightdelayst_SceneOpening_20260110_040654ComponentAnimated.tsx
    - analysis_carrier_delay_performance -> Analyzeflightdelayst_AnalysisCarrierDelayPerformance_20260110_040654Animated.tsx
    - summary_flight_statistics -> Analyzeflightdelayst_SummaryFlightStatistics_20260110_040654ComponentAnimated.tsx
    
    Args:
        scene_id: 场景ID
        dataset_name: 数据集名称
        task_id: 任务ID（可选）
        is_animated: 是否为动画版本
        needs_component: 是否需要 Component 后缀（如果为 None，则根据 scene_id 推断）
    """
    scene_id_camel = ''.join(word.capitalize() for word in scene_id.split('_'))
    
    # 判断是否需要 Component 后缀
    if needs_component is None:
        # 如果没有提供，根据 scene_id 推断
        if scene_id in ['scene_opening', 'scene_closing']:
            needs_component_suffix = True
        elif 'stat' in scene_id.lower() or scene_id.endswith('_statistics'):
            needs_component_suffix = True
        else:
            needs_component_suffix = False
    else:
        needs_component_suffix = needs_component
    
    # 构建完整文件名
    # 注意：对于需要 Component 的场景，格式是 {prefix}_{SceneId}_{task_id}ComponentAnimated.tsx
    # 而不是 {prefix}_{SceneId}Component_{task_id}Animated.tsx
    if task_id:
        if is_animated:
            if needs_component_suffix:
                # 需要 Component 的场景：{prefix}_{SceneId}_{task_id}ComponentAnimated.tsx
                return f"{dataset_name}_{scene_id_camel}_{task_id}ComponentAnimated.tsx"
            else:
                # 图表场景：{prefix}_{SceneId}_{task_id}Animated.tsx
                return f"{dataset_name}_{scene_id_camel}_{task_id}Animated.tsx"
        else:
            if needs_component_suffix:
                return f"{dataset_name}_{scene_id_camel}_{task_id}Component.tsx"
            else:
                return f"{dataset_name}_{scene_id_camel}_{task_id}.tsx"
    else:
        if is_animated:
            if needs_component_suffix:
                return f"{dataset_name}_{scene_id_camel}ComponentAnimated.tsx"
            else:
                return f"{dataset_name}_{scene_id_camel}Animated.tsx"
        else:
            if needs_component_suffix:
                return f"{dataset_name}_{scene_id_camel}Component.tsx"
            else:
                return f"{dataset_name}_{scene_id_camel}.tsx"


def scan_components_for_prefix(
    component_prefix: str, 
    components_dir: str, 
    config_data: dict = None,
    task_id: str = None
) -> Dict[str, Tuple[str, str]]:
    """
    扫描组件目录，查找匹配 componentPrefix 的组件
    返回: {scene_id: (component_file_name, export_name)}
    
    直接从配置文件生成预期文件名，然后查找文件（不需要反推）
    
    Args:
        component_prefix: 组件前缀（通常等于 dataset_name）
        components_dir: 组件目录（如果提供了 task_id，应该是任务目录路径）
        config_data: 配置文件数据，用于提取 dataset_name 和 scene_id
        task_id: 任务ID（用于生成预期文件名）
    """
    if not config_data:
        return {}
    
    # 从配置文件提取 dataset_name
    dataset_name = extract_dataset_name_from_config(config_data)
    if not dataset_name:
        dataset_name = component_prefix
    
    found_components = {}
    
    # 从配置文件读取所有 scene_id，生成预期文件名，然后查找
    for scene in config_data.get('scenes', []):
        scene_id = scene.get('id')
        scene_type = scene.get('type', '')
        if not scene_id:
            continue
        
        # 根据场景类型判断是否需要 Component 后缀
        # opening/closing/stat_cards 类型需要 Component 后缀
        needs_component = scene_type in ['opening', 'closing', 'stat_cards']
        
        # 生成预期的文件名
        expected_filename = scene_id_to_filename(scene_id, dataset_name, task_id, is_animated=True, needs_component=needs_component)
        
        # 构建文件路径
        file_path = Path(components_dir) / expected_filename
        
        # 如果文件存在，读取导出名
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取导出名称
                export_match = re.search(r'export const (\w+):', content)
                if export_match:
                    export_name = export_match.group(1)
                    # 生成组件导入名（去掉 .tsx 后缀）
                    component_name = expected_filename.replace('.tsx', '')
                    found_components[scene_id] = (component_name, export_name)
            except Exception as e:
                print(f"⚠️  读取组件文件失败 {expected_filename}: {e}")
        else:
            # 文件不存在，打印警告
            print(f"⚠️  未找到组件文件: {expected_filename} (scene_id: {scene_id})")
    
    return found_components


def generate_component_mapping_code(
    component_prefix: str,
    config_data: dict,
    components_dir: str,
    task_id: str = None,
    is_frontend: bool = False
) -> Tuple[str, str]:
    """
    生成组件映射表的 import 语句和映射表代码
    返回: (import_statements, mapping_table_code)
    """
    # 扫描组件（直接从配置生成预期文件名，然后查找）
    found_components = scan_components_for_prefix(component_prefix, components_dir, config_data, task_id)
    
    if not found_components:
        return "", ""
    
    # 生成 import 语句
    import_lines = []
    mapping_lines = []
    
    # 从配置文件中获取所有场景，按配置顺序处理
    config_scenes = {scene.get('id'): scene for scene in config_data.get('scenes', [])}
    
    # 按配置文件中的场景顺序处理
    ordered_scenes = []
    for scene in config_data.get('scenes', []):
        scene_id = scene.get('id')
        if scene_id in found_components:
            ordered_scenes.append(scene_id)
    
    # 如果没有找到匹配的场景，尝试使用传统格式
    if not ordered_scenes:
        scene_order = ['scene_opening'] + [f'scene_chart_{i}' for i in range(1, 10)] + ['scene_stats', 'scene_closing']
        ordered_scenes = [s for s in scene_order if s in found_components]
    
    for scene_id in ordered_scenes:
        component_name, export_name = found_components[scene_id]
        
        # 生成 import 语句
        # 对于图表场景，如果导出名是 SceneComponentAnimated，需要重命名以避免冲突
        scene_type = config_scenes.get(scene_id, {}).get('type', '')
        if scene_type == 'chart' and export_name == 'SceneComponentAnimated':
            # 对于 chart 类型，生成一个简洁的别名
            # 如果 scene_id 是 scene_chart_X 格式，使用原来的逻辑
            if scene_id.startswith('scene_chart_'):
                scene_num = scene_id.replace('scene_chart_', '')
                import_alias = f"{component_prefix}_SceneChart{scene_num}Animated"
            else:
                # 对于其他格式的 scene_id（如 analysis_xxx），使用 scene_id 转换为驼峰命名
                # analysis_carrier_delay_performance -> AnalysisCarrierDelayPerformance
                scene_id_camel = ''.join(word.capitalize() for word in scene_id.split('_'))
                import_alias = f"{component_prefix}_{scene_id_camel}Animated"
            
            # 如果提供了 task_id，import 路径包含任务目录
            # 前端路径格式：./{componentPrefix}/{task_id}/{component_name}
            # 后端路径格式：./{task_id}/{component_name} 或 ./{component_name}
            if task_id:
                if is_frontend:
                    import_path = f"./{component_prefix}/{task_id}/{component_name}"
                else:
                    import_path = f"./{task_id}/{component_name}"
            else:
                import_path = f"./{component_name}"
            
            import_lines.append(
                f"import {{SceneComponentAnimated as {import_alias}}} from '{import_path}';"
            )
            mapping_lines.append(f"  {scene_id}: {import_alias},")
        else:
            # 其他场景直接使用导出名
            # 如果提供了 task_id，import 路径包含任务目录
            # 前端路径格式：./{componentPrefix}/{task_id}/{component_name}
            # 后端路径格式：./{task_id}/{component_name} 或 ./{component_name}
            if task_id:
                if is_frontend:
                    import_path = f"./{component_prefix}/{task_id}/{component_name}"
                else:
                    import_path = f"./{task_id}/{component_name}"
            else:
                import_path = f"./{component_name}"
            
            import_lines.append(f"import {{{export_name}}} from '{import_path}';")
            mapping_lines.append(f"  {scene_id}: {export_name},")
    
    import_statements = '\n'.join(import_lines) if import_lines else ""
    # 使用 component_prefix 作为映射表名称
    mapping_table_name = f"{component_prefix.upper()}_COMPONENTS"
    mapping_table = f"""const {mapping_table_name}: Record<string, React.FC<any>> = {{
{chr(10).join(mapping_lines)}
}};""" if mapping_lines else ""
    
    return import_statements, mapping_table


def update_video_composer_with_mapping(
    component_prefix: str,
    config_data: dict,
    video_composer_path: Path,
    task_id: str = None,
    is_frontend: bool = False
) -> bool:
    """
    自动更新 VideoComposer.tsx，添加新组件的 import 和映射表
    返回: 是否成功更新
    
    Args:
        component_prefix: 组件前缀
        config_data: 配置文件数据
        video_composer_path: VideoComposer.tsx 文件路径
        task_id: 任务ID（如果提供，扫描任务目录；否则扫描 CustomInfographic 根目录）
    """
    if not video_composer_path.exists():
        print(f"⚠️  VideoComposer.tsx 不存在: {video_composer_path}")
        return False
    
    # 如果提供了 task_id，扫描任务目录；否则扫描根目录（兼容旧逻辑）
    if task_id:
        if is_frontend:
            # 前端路径：packages/frontend-react/src/components/video/{component_prefix}/{task_id}/
            components_dir = str(video_composer_path.parent / component_prefix / task_id)
        else:
            # 后端路径：src/components/CustomInfographic/{task_id}/
            components_dir = str(video_composer_path.parent / task_id)
    else:
        if is_frontend:
            # 前端路径：packages/frontend-react/src/components/video/{component_prefix}/
            components_dir = str(video_composer_path.parent / component_prefix)
        else:
            # 后端路径：src/components/CustomInfographic/
            components_dir = str(video_composer_path.parent)
    
    # 读取 VideoComposer.tsx（先读取，以便检查映射表是否存在）
    with open(video_composer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经存在该映射表
    mapping_table_name = f"{component_prefix.upper()}_COMPONENTS"
    mapping_exists = mapping_table_name in content
    
    # 总是重新生成映射表（即使已存在，也要更新以确保正确）
    import_statements, mapping_table = generate_component_mapping_code(
        component_prefix, config_data, components_dir, task_id, is_frontend=is_frontend
    )
    
    if not import_statements or not mapping_table:
        print(f"⚠️  未找到匹配的组件，跳过 VideoComposer 更新")
        return False
    
    if mapping_exists:
        print(f"ℹ️  映射表 {mapping_table_name} 已存在，将强制更新以确保正确性")
    
    # 1. 处理 import 语句（如果不存在则添加，如果已存在但需要更新则更新）
    # 检查是否需要更新 import（如果映射表已存在，可能需要更新 import）
    needs_import_update = mapping_exists or import_statements not in content
    
    if needs_import_update and import_statements:
        # 找到最后一个 import 语句的位置
        import_pattern = r'^import\s+.*?from\s+[\'"][^\'"]+[\'"];'
        import_matches = list(re.finditer(import_pattern, content, re.MULTILINE))
        
        if import_matches:
            last_import = import_matches[-1]
            insert_pos = content.find('\n', last_import.end())
            if insert_pos == -1:
                insert_pos = last_import.end()
            
            # 添加注释和 import 语句
            import_block = f"\n// 导入 {component_prefix} 相关组件\n{import_statements}\n"
            content = content[:insert_pos] + import_block + content[insert_pos:]
        else:
            print(f"⚠️  找不到 import 语句位置，跳过 import 添加")
    
    # 2. 处理映射表（如果已存在则替换，否则添加）
    mapping_updated = False  # 标记映射表是否被更新
    if mapping_exists:
        # 如果映射表已存在，先删除旧的
        # 查找映射表的开始和结束位置
        mapping_start_pattern = rf'const\s+{re.escape(mapping_table_name)}:\s*Record<string,\s*React\.FC<any>>\s*='
        mapping_start_match = re.search(mapping_start_pattern, content)
        
        if mapping_start_match:
            start_pos = mapping_start_match.start()
            # 向前查找注释（如果有）
            comment_start = content.rfind('//', max(0, start_pos - 100), start_pos)
            if comment_start != -1:
                # 找到注释所在行的开始
                line_start = content.rfind('\n', max(0, comment_start - 1), comment_start)
                if line_start != -1:
                    start_pos = line_start + 1
                else:
                    start_pos = comment_start
            
            # 从映射表开始位置向后查找匹配的 };
            brace_count = 0
            end_pos = mapping_start_match.end()
            
            for i, char in enumerate(content[end_pos:], start=end_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        # 跳过可能的换行
                        if end_pos < len(content) and content[end_pos] == '\n':
                            end_pos += 1
                        break
            
            # 替换旧的映射表
            mapping_block = f"// {component_prefix} 组件映射表\n{mapping_table}\n"
            old_mapping_content = content[start_pos:end_pos]
            # 检查内容是否真的改变了
            if old_mapping_content.strip() != mapping_block.strip():
                content = content[:start_pos] + mapping_block + content[end_pos:]
                mapping_updated = True
                print(f"✅ 已替换映射表 {mapping_table_name}")
            else:
                print(f"ℹ️  映射表 {mapping_table_name} 内容未变化，跳过更新")
        else:
            print(f"⚠️  找不到映射表 {mapping_table_name} 的位置，尝试添加新映射表")
            mapping_exists = False  # 降级为添加模式
    
    if not mapping_exists:
        # 找到最后一个映射表的位置（查找 "const XXX_COMPONENTS"）
        mapping_pattern = r'const\s+\w+_COMPONENTS:\s*Record<string,\s*React\.FC<any>>\s*='
        mapping_matches = list(re.finditer(mapping_pattern, content))
        
        if mapping_matches:
            # 找到最后一个映射表的结束位置（查找对应的 };）
            last_mapping = mapping_matches[-1]
            # 从该位置向后查找匹配的 };
            start_pos = last_mapping.end()
            brace_count = 0
            end_pos = start_pos
            
            for i, char in enumerate(content[start_pos:], start=start_pos):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
            
            # 在映射表后添加新映射表
            mapping_block = f"\n\n// {component_prefix} 组件映射表\n{mapping_table}\n"
            content = content[:end_pos] + mapping_block + content[end_pos:]
        else:
            # 如果找不到现有映射表，在 DEFAULT_SCENE_COMPONENTS 之后添加
            default_pos = content.find('const DEFAULT_SCENE_COMPONENTS')
            if default_pos != -1:
                # 找到 DEFAULT_SCENE_COMPONENTS 的结束位置
                start_pos = default_pos
                brace_count = 0
                end_pos = start_pos
                
                for i, char in enumerate(content[start_pos:], start=start_pos):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                mapping_block = f"\n\n// {component_prefix} 组件映射表\n{mapping_table}\n"
                content = content[:end_pos] + mapping_block + content[end_pos:]
    
    # 3. 更新 SCENE_COMPONENTS 的 useMemo，添加新映射表的匹配逻辑
    # 使用更精确的正则表达式匹配 useMemo（支持多行和嵌套大括号）
    use_memo_pattern = r'const SCENE_COMPONENTS = React\.useMemo\(\(\) => \{([\s\S]*?)\}, \[componentPrefix\]\);'
    use_memo_match = re.search(use_memo_pattern, content, re.DOTALL)
    already_exists = False  # 初始化变量
    
    if use_memo_match:
        use_memo_body = use_memo_match.group(1)
        # 检查是否已经包含该 componentPrefix 的匹配（支持多种格式）
        check_patterns = [
            f"componentPrefix === '{component_prefix}'",
            f'componentPrefix === "{component_prefix}"',
            f"'{component_prefix}'",
            f'"{component_prefix}"'
        ]
        already_exists = any(pattern in use_memo_body for pattern in check_patterns)
        
        if not already_exists:
            # 在 return DEFAULT_SCENE_COMPONENTS 之前添加新的 if 语句
            return_pos = use_memo_body.rfind('return DEFAULT_SCENE_COMPONENTS')
            if return_pos != -1:
                # 找到 return 语句所在行的开始位置和缩进
                return_line_start = use_memo_body.rfind('\n', 0, return_pos)
                if return_line_start == -1:
                    return_line_start = 0
                else:
                    return_line_start += 1  # 跳过换行符
                
                # 提取缩进（从行首到 return 之间的空格）
                indent_str = use_memo_body[return_line_start:return_pos]
                # 计算缩进级别（通常是4个空格）
                indent_level = len(indent_str) - len(indent_str.lstrip())
                if indent_level == 0:
                    indent_level = 4  # 默认4个空格
                indent = ' ' * indent_level
                
                # 构建新的 if 语句块，保持一致的缩进
                new_if_block = f"{indent}if (componentPrefix === '{component_prefix}') {{\n{indent}  return {mapping_table_name};\n{indent}}}\n"
                use_memo_body = use_memo_body[:return_pos] + new_if_block + use_memo_body[return_pos:]
                # 替换整个 useMemo
                new_use_memo = f"const SCENE_COMPONENTS = React.useMemo(() => {{{use_memo_body}}}, [componentPrefix]);"
                content = re.sub(use_memo_pattern, new_use_memo, content, flags=re.DOTALL)
                print(f"✅ 已自动添加 {component_prefix} 到 useMemo 匹配逻辑")
            else:
                print(f"⚠️  找不到 'return DEFAULT_SCENE_COMPONENTS'，无法自动添加匹配逻辑")
        else:
            print(f"ℹ️  {component_prefix} 的匹配逻辑已存在，跳过更新")
    else:
        print(f"⚠️  找不到 SCENE_COMPONENTS useMemo，无法自动添加匹配逻辑")
    
    # 写回文件（只有在内容有变化时才写回）
    # 检查是否有实际更新
    updated = False
    if not mapping_exists:
        updated = True  # 添加了新映射表
    elif mapping_updated:
        updated = True  # 替换了已存在的映射表
    elif use_memo_match and not already_exists:
        updated = True  # 更新了 useMemo
    
    if updated:
        with open(video_composer_path, 'w', encoding='utf-8') as f:
            f.write(content)
        if not mapping_exists:
            print(f"✅ 已更新 VideoComposer.tsx，添加 {component_prefix} 组件映射")
        else:
            print(f"✅ 已更新 VideoComposer.tsx 的 useMemo，添加 {component_prefix} 匹配逻辑")
    else:
        print(f"ℹ️  VideoComposer.tsx 无需更新（映射表和 useMemo 都已存在）")
    
    return True


def copy_components_to_frontend(
    component_prefix: str,
    config_data: dict,
    task_id: str,
    animated_components_dir: Path
) -> bool:
    """
    复制生成的动画组件到前端目录
    返回: 是否成功复制
    
    Args:
        component_prefix: 组件前缀
        config_data: 配置文件数据
        task_id: 任务ID
        animated_components_dir: 后端生成的动画组件目录路径
    """
    try:
        # 确定前端目录路径
        # 从当前文件位置推断项目根目录
        # __file__ 是 packages/backend/app/node/video/render/auto_compose_video.py
        # 需要找到 packages/frontend-react/src/components/video/
        current_file = Path(__file__)
        # 从 packages/backend/app/node/video/render/ 回到项目根目录
        # packages/backend/app/node/video/render/ -> packages/backend/app/node/video/ -> packages/backend/app/node/
        # -> packages/backend/app/ -> packages/backend/ -> packages/ -> 项目根目录
        project_root = current_file.parent.parent.parent.parent.parent.parent.parent
        frontend_video_dir = project_root / 'packages' / 'frontend-react' / 'src' / 'components' / 'video'
        target_dir = frontend_video_dir / component_prefix / task_id
        
        if not animated_components_dir.exists():
            print(f"⚠️  动画组件目录不存在: {animated_components_dir}")
            return False
        
        # 创建目标目录
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📂 复制组件到前端目录: {target_dir}")
        
        # 扫描组件文件
        found_components = scan_components_for_prefix(component_prefix, str(animated_components_dir), config_data, task_id)
        
        if not found_components:
            print(f"⚠️  未找到匹配的组件")
            return False
        
        # 复制文件到后端容器中的前端代码目录
        import shutil
        copied_count = 0
        for scene_id, (component_name, _) in found_components.items():
            source_file = animated_components_dir / f"{component_name}.tsx"
            if source_file.exists():
                target_file = target_dir / f"{component_name}.tsx"
                shutil.copy2(source_file, target_file)
                copied_count += 1
                print(f"   ✅ {component_name}.tsx")
            else:
                print(f"   ⚠️  文件不存在: {source_file}")
        
        print(f"✅ 已复制 {copied_count} 个组件到前端代码目录")
        
        # 检测是否在 Docker 容器中，如果是，同时复制到前端容器的运行目录
        is_docker = Path('/app').exists() and Path('/.dockerenv').exists()
        if is_docker:
            # 方法1: 检查是否有共享卷（前端容器的运行目录）
            frontend_container_dir = Path('/app/src/components/video')
            if frontend_container_dir.exists():
                # 前端容器的运行目录（通过共享卷或挂载）
                container_target_dir = frontend_container_dir / component_prefix / task_id
                container_target_dir.mkdir(parents=True, exist_ok=True)
                print(f"\n📂 复制组件到前端容器运行目录: {container_target_dir}")
                
                container_copied_count = 0
                for scene_id, (component_name, _) in found_components.items():
                    source_file = animated_components_dir / f"{component_name}.tsx"
                    if source_file.exists():
                        container_target_file = container_target_dir / f"{component_name}.tsx"
                        shutil.copy2(source_file, container_target_file)
                        container_copied_count += 1
                        print(f"   ✅ {component_name}.tsx → 前端容器")
                
                print(f"✅ 已复制 {container_copied_count} 个组件到前端容器运行目录")
            else:
                # 方法2: 如果前端容器目录不存在，尝试通过 Docker API 复制
                try:
                    import docker
                    docker_client = docker.from_env()
                    # 查找前端容器（通常名称包含 frontend）
                    containers = docker_client.containers.list(filters={'status': 'running'})
                    frontend_container = None
                    for container in containers:
                        if 'frontend' in container.name.lower():
                            frontend_container = container
                            break
                    
                    if frontend_container:
                        print(f"\n📦 通过 Docker API 复制到前端容器: {frontend_container.name}")
                        # 创建临时目录并准备文件
                        import tempfile
                        import tarfile
                        import io
                        
                        with tempfile.TemporaryDirectory() as tmp_dir:
                            tmp_path = Path(tmp_dir)
                            # 创建目录结构
                            component_tmp_dir = tmp_path / component_prefix / task_id
                            component_tmp_dir.mkdir(parents=True, exist_ok=True)
                            
                            # 复制文件到临时目录
                            for scene_id, (component_name, _) in found_components.items():
                                source_file = animated_components_dir / f"{component_name}.tsx"
                                if source_file.exists():
                                    shutil.copy2(source_file, component_tmp_dir / f"{component_name}.tsx")
                            
                            # 创建 tar 归档
                            tar_stream = io.BytesIO()
                            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                                tar.add(tmp_path / component_prefix, arcname=component_prefix)
                            
                            tar_stream.seek(0)
                            
                            # 复制到容器
                            container_target_path = '/app/src/components/video/'
                            frontend_container.put_archive(container_target_path, tar_stream.getvalue())
                            
                            print(f"✅ 已通过 Docker API 复制组件到前端容器")
                    else:
                        print(f"⚠️  未找到运行中的前端容器，跳过容器内复制")
                except ImportError:
                    print(f"⚠️  docker 库未安装，跳过容器内复制（需要: pip install docker）")
                except Exception as e:
                    print(f"⚠️  通过 Docker API 复制失败: {e}（这是可选的，不影响主要功能）")
                    import traceback
                    traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"⚠️  复制组件到前端失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_frontend_video_composer(
    component_prefix: str,
    config_data: dict,
    task_id: str
) -> bool:
    """
    更新前端的 VideoComposer.tsx，添加新组件的 import 和映射表
    返回: 是否成功更新
    
    Args:
        component_prefix: 组件前缀
        config_data: 配置文件数据
        task_id: 任务ID
    """
    success = False
    try:
        # 方法1: 尝试更新后端容器中的前端代码目录（用于版本控制）
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent.parent.parent.parent
        backend_frontend_path = project_root / 'packages' / 'frontend-react' / 'src' / 'components' / 'video' / 'VideoComposer.tsx'
        
        if backend_frontend_path.exists():
            print(f"📝 更新后端容器中的前端代码: {backend_frontend_path}")
            try:
                if update_video_composer_with_mapping(
                    component_prefix,
                    config_data,
                    backend_frontend_path,
                    task_id,
                    is_frontend=True
                ):
                    print(f"✅ 已更新后端容器中的前端代码")
                    success = True
            except Exception as e:
                print(f"⚠️  更新后端容器中的前端代码失败: {e}")
        
        # 方法2: 尝试更新前端容器的实际运行文件
        is_docker = Path('/app').exists() and Path('/.dockerenv').exists()
        if is_docker:
            # 检查是否有共享卷（前端容器的运行目录）
            frontend_container_path = Path('/app/src/components/video/VideoComposer.tsx')
            if frontend_container_path.exists():
                print(f"📝 更新前端容器运行文件: {frontend_container_path}")
                try:
                    if update_video_composer_with_mapping(
                        component_prefix,
                        config_data,
                        frontend_container_path,
                        task_id,
                        is_frontend=True
                    ):
                        print(f"✅ 已更新前端容器运行文件")
                        success = True
                except Exception as e:
                    print(f"⚠️  更新前端容器运行文件失败: {e}")
            else:
                # 如果没有共享卷，尝试通过 Docker API 更新
                try:
                    import docker
                    docker_client = docker.from_env()
                    containers = docker_client.containers.list(filters={'status': 'running'})
                    frontend_container = None
                    for container in containers:
                        if 'frontend' in container.name.lower():
                            frontend_container = container
                            break
                    
                    if frontend_container:
                        print(f"📦 通过 Docker API 更新前端容器: {frontend_container.name}")
                        # 先在后端容器中生成更新后的内容
                        import tempfile
                        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False, encoding='utf-8')
                        temp_path = Path(temp_file.name)
                        temp_file.close()
                        
                        try:
                            # 读取当前前端容器的文件内容
                            import io
                            import tarfile
                            bits, stat = frontend_container.get_archive('/app/src/components/video/VideoComposer.tsx')
                            file_obj = io.BytesIO(b''.join(bits))
                            with tarfile.open(fileobj=file_obj) as tar:
                                tar.extractall(path=temp_path.parent)
                                extracted_file = temp_path.parent / 'VideoComposer.tsx'
                                if extracted_file.exists():
                                    # 更新文件
                                    if update_video_composer_with_mapping(
                                        component_prefix,
                                        config_data,
                                        extracted_file,
                                        task_id,
                                        is_frontend=True
                                    ):
                                        # 打包并复制回容器
                                        tar_stream = io.BytesIO()
                                        with tarfile.open(fileobj=tar_stream, mode='w') as tar_out:
                                            tar_out.add(extracted_file, arcname='VideoComposer.tsx')
                                        tar_stream.seek(0)
                                        frontend_container.put_archive('/app/src/components/video/', tar_stream.getvalue())
                                        print(f"✅ 已通过 Docker API 更新前端容器")
                                        success = True
                        except Exception as e:
                            print(f"⚠️  通过 Docker API 更新失败: {e}")
                        finally:
                            if temp_path.exists():
                                temp_path.unlink()
                            if (temp_path.parent / 'VideoComposer.tsx').exists():
                                (temp_path.parent / 'VideoComposer.tsx').unlink()
                except ImportError:
                    print(f"⚠️  docker 库未安装，跳过 Docker API 更新（需要: pip install docker）")
                except Exception as e:
                    print(f"⚠️  通过 Docker API 更新失败: {e}（这是可选的，不影响主要功能）")
        
        return success
        
    except Exception as e:
        print(f"⚠️  更新前端 VideoComposer.tsx 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_video_composer_to_root(config_path, video_id, total_frames, scene_counts, component_prefix=None):
    """在Root.tsx中添加VideoComposer的注册代码"""
    
    root_path = Path(__file__).parent.parent.parent / 'src' / 'Root.tsx'
    
    if not root_path.exists():
        # 在 Docker 环境中，Remotion 项目可能不存在，这是正常的
        # 只生成 TSX 组件文件即可，不需要注册到 Root.tsx
        print(f"⚠️  Root.tsx 不存在: {root_path}")
        print(f"   这在 Docker 环境中是正常的，Remotion 项目可能不在容器内")
        print(f"   TSX 组件文件已生成，可以在 Remotion 项目中手动注册")
        return False  # 返回 False 表示跳过，但不抛出异常
    
    with open(root_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生成import语句
    config_import_name = get_config_import_name(video_id)
    
    # 计算相对路径
    config_rel_path = os.path.relpath(config_path, root_path.parent)
    # 转换为Unix风格路径（保留.json后缀）
    config_import_path = config_rel_path.replace('\\', '/')
    if not config_import_path.startswith('../'):
        config_import_path = '../' + config_import_path
    
    import_statement = f"import {config_import_name} from '{config_import_path}';"
    
    # 检查是否已经导入了VideoComposer
    if 'import {VideoComposer}' not in content:
        # 在 Claude 生成的组件导入区域后添加 VideoComposer 导入
        video_composer_import = """
// VideoComposer - 通用视频串联组件
import {VideoComposer} from './components/CustomInfographic/VideoComposer';"""
        
        # 找到合适的位置插入（在最后一个 import 语句之后）
        # 优先查找已知的导入标记
        insert_pos = content.rfind("import {ClaudeRevenueStatic_v2}")
        if insert_pos == -1:
            insert_pos = content.find("// 兼容 Remotion Composition")
        if insert_pos == -1:
            # 查找最后一个 import 语句
            import_pattern = r'^import\s+.*?from\s+[\'"][^\'"]+[\'"];'
            import_matches = list(re.finditer(import_pattern, content, re.MULTILINE))
            if import_matches:
                last_import = import_matches[-1]
                insert_pos = last_import.end()
        
        if insert_pos != -1:
            line_end = content.find('\n', insert_pos)
            if line_end == -1:
                line_end = len(content)
            content = content[:line_end + 1] + video_composer_import + '\n' + content[line_end + 1:]
        else:
            # 如果找不到合适位置，在文件开头附近插入
            first_import_end = content.find('\n', content.find('import'))
            if first_import_end != -1:
                content = content[:first_import_end + 1] + video_composer_import + '\n' + content[first_import_end + 1:]
    
    # 检查配置文件是否已导入，如果已导入但路径不同则更新
    import_updated = False
    if config_import_name not in content:
        # 找到 VideoComposer 导入的位置，在其后添加配置导入
        insert_pos = content.find("import {VideoComposer}")
        if insert_pos != -1:
            line_end = content.find('\n', insert_pos)
            line_end = content.find('\n', line_end + 1)  # 跳到下一行
            content = content[:line_end + 1] + import_statement + '\n' + content[line_end + 1:]
            import_updated = True
            print(f"✅ 添加配置文件导入: {config_import_path}")
    else:
        # 配置文件已导入，检查路径是否需要更新
        import re
        # 查找现有的导入语句
        pattern = rf"import {re.escape(config_import_name)} from ['\"]([^'\"]+)['\"];"
        match = re.search(pattern, content)
        if match:
            old_path = match.group(1)
            if old_path != config_import_path:
                # 路径不同，更新导入路径
                content = re.sub(pattern, f"import {config_import_name} from '{config_import_path}';", content)
                import_updated = True
                print(f"✅ 更新配置文件导入路径: {old_path} -> {config_import_path}")
    
    # 🔥 关键修复：导入路径更新后立即保存，不依赖后续Composition更新
    if import_updated:
        with open(root_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 已保存导入路径更新")
        # 重新读取文件，确保后续操作基于最新内容
        with open(root_path, 'r', encoding='utf-8') as f:
            content = f.read()
    
    # 生成场景统计信息
    total_scenes = sum(scene_counts.values())
    scene_info = []
    if scene_counts['opening'] > 0:
        scene_info.append(f"{scene_counts['opening']} opening")
    if scene_counts['chart'] > 0:
        scene_info.append(f"{scene_counts['chart']} chart")
    if scene_counts['stat_cards'] > 0:
        scene_info.append(f"{scene_counts['stat_cards']} stat_cards")
    if scene_counts['closing'] > 0:
        scene_info.append(f"{scene_counts['closing']} closing")
    scene_summary = ' + '.join(scene_info)
    
    # 生成场景组件映射表代码
    scene_components_code = ""
    if component_prefix:
        # 读取配置文件以获取所有场景
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data_for_components = json.load(f)
        
        # 构建sceneComponents映射表
        scene_components_lines = []
        
        for scene in config_data_for_components.get('scenes', []):
            scene_id = scene.get('id', '')
            if not scene_id:
                continue
            
            # 根据scene_id和component_prefix构建组件名
            if scene_id == 'scene_opening':
                component_name = f"{component_prefix}_SceneOpeningComponent"
            elif scene_id == 'scene_closing':
                component_name = f"{component_prefix}_SceneClosingComponent"
            elif scene_id.startswith('scene_chart_'):
                chart_num = scene_id.replace('scene_chart_', '')
                component_name = f"{component_prefix}_SceneChart{chart_num}Animated"
            else:
                continue
            
            # 检查Root.tsx中是否已导入该组件
            if component_name in content:
                scene_components_lines.append(f"            {scene_id}: {component_name},")
        
        if scene_components_lines:
            scene_components_code = f"""
          sceneComponents: {{{{
{chr(10).join(scene_components_lines)}
          }}}},"""
    
    # 生成Composition注册代码
    component_prefix_prop = f"componentPrefix: '{component_prefix}'," if component_prefix else ""
    # Composition ID 不能包含下划线，替换为连字符
    composition_id = video_id.replace('_', '-')
    composition_code = f"""
      {{/* 🎬 VideoComposer - {video_id} ({total_scenes} scenes: {scene_summary}) */}}
      <Composition
        id="{composition_id}"
        component={{VideoComposer}}
        defaultProps={{{{
          configJson: {config_import_name},
          scenePrefix: 'SceneChart',
          includeOpeningClosing: true,
          {component_prefix_prop}{scene_components_code}
        }}}}
        durationInFrames={{{total_frames}}}
        fps={{30}}
        width={{1280}}
        height={{720}}
      />
"""
    
    # 检查是否已经存在该Composition（使用转换后的 composition_id）
    if f'id="{composition_id}"' in content:
        print(f"ℹ️  VideoComposer '{composition_id}' 已存在，尝试更新配置...")
        
        # 尝试更新已存在的 Composition 的配置
        import re
        
        # 方法1: 尝试匹配完整的 Composition 代码块（包括注释和多行结构）
        # 匹配从注释开始到 </Composition> 结束的完整块
        composition_pattern = rf'(\{{\s*/\*.*?VideoComposer.*?{re.escape(video_id)}.*?\*/\s*<Composition[\s\S]*?id="{re.escape(composition_id)}"[\s\S]*?</Composition>\s*}})'
        match = re.search(composition_pattern, content, re.DOTALL)
        
        if match:
            # 更新 configJson 路径
            old_composition = match.group(1)
            # 检查是否需要更新 configJson
            if f'configJson: {config_import_name}' not in old_composition:
                # 更新 configJson 路径（匹配多行格式）
                updated_composition = re.sub(
                    r'configJson:\s*\w+,',
                    f'configJson: {config_import_name},',
                    old_composition
                )
                # 更新 durationInFrames（匹配多行格式）
                updated_composition = re.sub(
                    r'durationInFrames=\{\{\d+\}\}',
                    f'durationInFrames={{{total_frames}}}',
                    updated_composition
                )
                # 更新场景数量注释
                updated_composition = re.sub(
                    r'\(\d+\s+scenes:.*?\)',
                    f'({total_scenes} scenes: {scene_summary})',
                    updated_composition
                )
                
                content = content.replace(old_composition, updated_composition)
                print(f"✅ 已更新 Composition '{composition_id}' 的配置")
                print(f"   - 配置文件: {config_import_path}")
                print(f"   - 总时长: {total_frames} 帧")
                
                # 写回文件
                with open(root_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            else:
                print(f"ℹ️  配置变量 {config_import_name} 已存在，跳过更新")
                return True
        else:
            # 方法2: 如果完整匹配失败，尝试使用正则表达式匹配 Composition 标签
            print(f"⚠️  无法找到 Composition '{composition_id}' 的完整代码块，尝试直接匹配标签...")
            
            # 使用正则表达式匹配包含指定 id 的 Composition 标签（支持自闭合和闭合标签）
            # 匹配模式：从 <Composition 开始，包含 id="composition_id"，到 /> 或 </Composition> 结束
            # 使用更精确的匹配：确保 id 属性在 <Composition 标签内
            composition_regex = rf'<Composition[\s\S]*?id="{re.escape(composition_id)}"[\s\S]*?(?:/>|</Composition>)'
            match = re.search(composition_regex, content, re.DOTALL)
            
            if match:
                # 找到匹配的 Composition 标签
                composition_section = match.group(0)
                comment_start = match.start()
                end_pos = match.end()
                
                # 确保包含注释（如果存在）
                if '{/*' not in composition_section:
                    # 向前查找注释
                    comment_pos = content.rfind('{/*', max(0, comment_start - 500), comment_start)
                    if comment_pos != -1:
                        # 找到注释结束位置
                        comment_end = content.find('*/}', comment_pos, comment_start)
                        if comment_end != -1:
                            comment_end += 3
                            composition_section = content[comment_pos:end_pos]
                            comment_start = comment_pos
                
                # 确保 end_pos 在 comment_start 之后且有效
                if end_pos > comment_start and end_pos > 0 and end_pos <= len(content):
                    # 重新获取完整的 composition_section（包含注释）
                    composition_section = content[comment_start:end_pos]
                    
                    # 确保包含换行符（如果 Composition 标签后面有换行）
                    if end_pos < len(content) and content[end_pos] == '\n':
                        end_pos += 1
                        # 如果下一行是空行，也包含进去
                        if end_pos < len(content) and content[end_pos] == '\n':
                            end_pos += 1
                        composition_section = content[comment_start:end_pos]
                    
                    # 检查是否需要更新
                    needs_update = False
                    updated_section = composition_section
                    
                    # 更新 configJson（如果存在且不同）
                    config_json_pattern = r'configJson:\s*(\w+),'
                    config_match = re.search(config_json_pattern, updated_section)
                    if config_match:
                        old_config_var = config_match.group(1)
                        if old_config_var != config_import_name:
                            updated_section = re.sub(
                                config_json_pattern,
                                f'configJson: {config_import_name},',
                                updated_section
                            )
                            needs_update = True
                            print(f"   ✅ 更新 configJson: {old_config_var} -> {config_import_name}")
                    
                    # 更新 durationInFrames（如果存在且不同）
                    duration_pattern = r'durationInFrames=\{\{(\d+)\}\}'
                    duration_match = re.search(duration_pattern, updated_section)
                    if duration_match:
                        old_duration = int(duration_match.group(1))
                        if old_duration != total_frames:
                            updated_section = re.sub(
                                duration_pattern,
                                f'durationInFrames={{{total_frames}}}',
                                updated_section
                            )
                            needs_update = True
                            print(f"   ✅ 更新 durationInFrames: {old_duration} -> {total_frames}")
                    
                    # 更新场景数量注释
                    scene_count_pattern = r'\(\d+\s+scenes:.*?\)'
                    if re.search(scene_count_pattern, updated_section):
                        updated_section = re.sub(
                            scene_count_pattern,
                            f'({total_scenes} scenes: {scene_summary})',
                            updated_section
                        )
                        needs_update = True
                        print(f"   ✅ 更新场景数量注释")
                    
                    if needs_update:
                        content = content[:comment_start] + updated_section + content[end_pos:]
                        # 写回文件
                        with open(root_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"✅ 已更新 Composition '{composition_id}' 的配置（通过字段更新）")
                        print(f"   - 配置文件: {config_import_path}")
                        print(f"   - 总时长: {total_frames} 帧")
                        return True
                    else:
                        print(f"ℹ️  配置已是最新，无需更新")
                        return True
                else:
                    # 提供更详细的调试信息
                    if end_pos == -1:
                        print(f"⚠️  无法找到 Composition '{composition_id}' 的结束位置（既不是 </Composition> 也不是 />）")
                    elif end_pos <= start_pos:
                        print(f"⚠️  结束位置 ({end_pos}) 不晚于开始位置 ({start_pos})")
                    elif end_pos > len(content):
                        print(f"⚠️  结束位置 ({end_pos}) 超出文件长度 ({len(content)})")
                    else:
                        print(f"⚠️  无法定位 Composition '{composition_id}' 的边界（未知原因）")
                    return False
            else:
                print(f"⚠️  无法找到 Composition '{composition_id}' 的 id 属性，跳过更新")
                return False
    
    # 尝试找到 END AUTO-GENERATED COMPOSITIONS 标记
    end_marker = '{/* === END AUTO-GENERATED COMPOSITIONS === */}'
    end_pos = content.find(end_marker)
    
    if end_pos == -1:
        # 如果没有标记，则在最后一个 </Composition> 之后插入
        last_composition_end = content.rfind('</Composition>')
        if last_composition_end != -1:
            # 找到该行的结束位置
            line_end = content.find('\n', last_composition_end)
            if line_end != -1:
                end_pos = line_end + 1
            else:
                # 如果找不到换行符，在 </Composition> 后直接插入
                end_pos = last_composition_end + len('</Composition>')
        else:
            # 如果连 Composition 都找不到，则在 </> 之前插入
            closing_tag_pos = content.rfind('</>')
            if closing_tag_pos != -1:
                end_pos = closing_tag_pos
            else:
                raise ValueError("找不到合适的插入位置：既没有 END AUTO-GENERATED COMPOSITIONS 标记，也没有找到 Composition 或 </>")
    
    # 在标记之前插入
    content = content[:end_pos] + composition_code + '\n      ' + content[end_pos:]
    
    # 写回文件
    with open(root_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def main():
    parser = argparse.ArgumentParser(description='自动组装完整视频到Root.tsx')
    parser.add_argument('--config', required=True, help='JSON配置文件路径')
    parser.add_argument('--task-id', type=str, default=None, help='任务ID，用于生成简短的Composition ID')
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    print("="*70)
    print("🎬 自动组装完整视频")
    print("="*70)
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    video_title = config_data['meta']['title']
    print(f"\n📊 视频标题: {video_title}")
    
    # 计算总时长
    total_frames, scene_counts = calculate_total_duration(config_data)
    fps = config_data['meta']['fps']
    duration_seconds = total_frames / fps
    
    total_scenes = sum(scene_counts.values())
    print(f"📊 场景数量: {total_scenes} (Opening: {scene_counts['opening']}, Chart: {scene_counts['chart']}, Stat Cards: {scene_counts['stat_cards']}, Closing: {scene_counts['closing']})")
    print(f"📊 总时长: {total_frames} 帧 ({duration_seconds:.1f} 秒 @ {fps}fps)")
    
    # 生成视频ID
    if args.task_id:
        # 使用简短的 task_id 格式，避免名字太长
        video_id = f"FullVideo-{args.task_id.replace('_', '-')}"
        print(f"📊 视频ID: {video_id} (基于任务ID)")
    else:
        # 回退到基于标题的长ID
        video_id = get_video_id_from_config(config_data)
        print(f"📊 视频ID: {video_id} (基于标题)")
    
    # 生成组件前缀（保持基于标题，与组件文件名匹配）
    component_prefix = get_component_prefix_from_config(config_data)
    if component_prefix:
        print(f"📊 组件前缀: {component_prefix}")
    
    # 确定动画组件目录
    animated_components_dir = None
    if args.task_id:
        # 优先使用统一运行时目录（可由 VIDEO_ANIMATED_OUTPUT_BASE 覆盖）
        animated_components_dir = DEFAULT_ANIMATED_OUTPUT_DIR / args.task_id
    
    # 复制组件到前端目录（如果提供了 task_id 和 component_prefix）
    if component_prefix and args.task_id and animated_components_dir:
        print(f"\n📦 正在复制组件到前端目录...")
        try:
            copy_components_to_frontend(component_prefix, config_data, args.task_id, animated_components_dir)
        except Exception as e:
            print(f"⚠️  复制组件到前端失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 更新前端 VideoComposer.tsx（如果提供了 component_prefix 和 task_id）
    # 注意：DeepEye-DataMagic 使用动态加载机制，不需要硬编码映射表
    # 组件会通过 API 获取并在浏览器中编译，所以跳过前端 VideoComposer 的自动更新
    if component_prefix and args.task_id:
        print(f"\n🔧 跳过前端 VideoComposer.tsx 自动更新（使用动态加载机制）...")
        print(f"   组件将通过 API 动态加载: /api/public/video/components/{args.task_id}/")
        # update_frontend_video_composer(component_prefix, config_data, args.task_id)  # 已禁用
    
    # 自动更新后端 VideoComposer.tsx（如果提供了 component_prefix，用于 Remotion 项目）
    if component_prefix:
        print(f"\n🔧 正在更新后端 VideoComposer.tsx（Remotion 项目）...")
        video_composer_path = Path(__file__).parent.parent.parent / 'src' / 'components' / 'CustomInfographic' / 'VideoComposer.tsx'
        try:
            update_video_composer_with_mapping(component_prefix, config_data, video_composer_path, args.task_id)
        except Exception as e:
            print(f"⚠️  更新后端 VideoComposer 失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 添加到Root.tsx
    print(f"\n🔧 正在注册到 Root.tsx...")
    
    try:
        success = add_video_composer_to_root(config_path, video_id, total_frames, scene_counts, component_prefix)
        
        if success:
            print(f"✅ 成功注册 VideoComposer: {video_id}")
            print(f"\n💡 现在你可以在 Remotion Studio 中预览完整视频！")
            print(f"   视频名称: {video_id}")
            print(f"   场景数量: {total_scenes}")
            print(f"   总时长: {duration_seconds:.1f}秒")
        
    except Exception as e:
        print(f"❌ 注册失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
