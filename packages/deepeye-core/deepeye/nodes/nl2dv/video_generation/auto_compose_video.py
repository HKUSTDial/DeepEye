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


def calculate_total_duration(config_data):
    """从JSON配置计算视频总时长（帧数）"""
    fps = config_data['meta']['fps']
    
    # 找到所有渲染场景（opening, chart, stat_cards, closing）
    all_scenes = [s for s in config_data['scenes'] 
                  if s['type'] in ['opening', 'chart', 'stat_cards', 'closing']]
    
    if not all_scenes:
        raise ValueError("配置文件中没有找到任何可渲染的场景")
    
    # 获取最后一个场景的结束时间
    last_scene = all_scenes[-1]
    end_time = last_scene['time_range'][1]
    
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
    # FlightDataFullVideo -> flightDataJson
    name = video_id.replace('FullVideo', '')
    return name[0].lower() + name[1:] + 'Json'


def scan_components_for_prefix(component_prefix: str, components_dir: str) -> Dict[str, Tuple[str, str]]:
    """
    扫描组件目录，查找匹配 componentPrefix 的组件
    返回: {scene_id: (component_file_name, export_name)}
    """
    components_dir_path = Path(components_dir)
    if not components_dir_path.exists():
        return {}
    
    found_components = {}
    
    # 遍历所有 .tsx 文件
    for tsx_file in components_dir_path.glob('*.tsx'):
        filename = tsx_file.name
        # 检查文件名是否以 component_prefix 开头（不区分大小写）
        # 因为文件名可能是 InsightsfromARTANDDE，但 component_prefix 可能是小写
        if not filename.lower().startswith(component_prefix.lower()):
            continue
        
        # 读取文件内容，提取导出名称和场景ID
        try:
            with open(tsx_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取导出名称
            export_match = re.search(r'export const (\w+):', content)
            if not export_match:
                continue
            export_name = export_match.group(1)
            
            # 根据文件名推断 scene_id
            # 例如: InsightsfromARTANDDE_SceneChart1Animated.tsx -> scene_chart_1
            # 例如: InsightsfromARTANDDE_SceneOpeningComponentAnimated.tsx -> scene_opening
            scene_id = None
            
            if '_SceneChart' in filename:
                # 提取图表编号
                chart_match = re.search(r'_SceneChart(\d+)', filename)
                if chart_match:
                    chart_num = chart_match.group(1)
                    scene_id = f'scene_chart_{chart_num}'
            elif 'SceneOpening' in filename:
                scene_id = 'scene_opening'
            elif 'SceneClosing' in filename:
                scene_id = 'scene_closing'
            elif 'SceneStats' in filename:
                scene_id = 'scene_stats'
            
            if scene_id:
                # 生成组件导入名（去掉 .tsx 后缀）
                component_name = filename.replace('.tsx', '')
                found_components[scene_id] = (component_name, export_name)
        
        except Exception as e:
            print(f"⚠️  读取组件文件失败 {filename}: {e}")
            continue
    
    return found_components


def generate_component_mapping_code(
    component_prefix: str,
    config_data: dict,
    components_dir: str
) -> Tuple[str, str]:
    """
    生成组件映射表的 import 语句和映射表代码
    返回: (import_statements, mapping_table_code)
    """
    # 扫描组件
    found_components = scan_components_for_prefix(component_prefix, components_dir)
    
    if not found_components:
        return "", ""
    
    # 生成 import 语句
    import_lines = []
    mapping_lines = []
    
    # 从配置文件中获取所有场景，确保顺序正确
    config_scenes = {scene.get('id'): scene for scene in config_data.get('scenes', [])}
    
    # 按场景顺序处理（opening -> chart -> stat_cards -> closing）
    scene_order = ['scene_opening'] + [f'scene_chart_{i}' for i in range(1, 10)] + ['scene_stats', 'scene_closing']
    ordered_scenes = [s for s in scene_order if s in found_components]
    
    for scene_id in ordered_scenes:
        component_name, export_name = found_components[scene_id]
        
        # 生成 import 语句
        # 对于图表场景，如果导出名是 SceneComponentAnimated，需要重命名
        if scene_id.startswith('scene_chart_') and export_name == 'SceneComponentAnimated':
            # 提取图表编号
            chart_num = scene_id.replace('scene_chart_', '')
            import_alias = f"{component_prefix}_SceneChart{chart_num}Animated"
            import_lines.append(
                f"import {{SceneComponentAnimated as {import_alias}}} from './{component_name}';"
            )
            mapping_lines.append(f"  {scene_id}: {import_alias},")
        else:
            # 其他场景直接使用导出名
            import_lines.append(f"import {{{export_name}}} from './{component_name}';")
            mapping_lines.append(f"  {scene_id}: {export_name},")
    
    import_statements = '\n'.join(import_lines) if import_lines else ""
    mapping_table_name = f"{component_prefix.upper()}_COMPONENTS"
    mapping_table = f"""const {mapping_table_name}: Record<string, React.FC<any>> = {{
{chr(10).join(mapping_lines)}
}};""" if mapping_lines else ""
    
    return import_statements, mapping_table


def update_video_composer_with_mapping(
    component_prefix: str,
    config_data: dict,
    video_composer_path: Path
) -> bool:
    """
    自动更新 VideoComposer.tsx，添加新组件的 import 和映射表
    返回: 是否成功更新
    """
    if not video_composer_path.exists():
        print(f"⚠️  VideoComposer.tsx 不存在: {video_composer_path}")
        return False
    
    components_dir = str(video_composer_path.parent)  # src/components/CustomInfographic/
    
    # 生成映射表代码
    import_statements, mapping_table = generate_component_mapping_code(
        component_prefix, config_data, str(components_dir)
    )
    
    if not import_statements or not mapping_table:
        print(f"⚠️  未找到匹配的组件，跳过 VideoComposer 更新")
        return False
    
    # 读取 VideoComposer.tsx
    with open(video_composer_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经存在该映射表
    mapping_table_name = f"{component_prefix.upper()}_COMPONENTS"
    if mapping_table_name in content:
        print(f"ℹ️  映射表 {mapping_table_name} 已存在，跳过更新")
        return True
    
    # 1. 添加 import 语句（在最后一个 import 之后）
    if import_statements not in content:
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
    
    # 2. 添加映射表（在最后一个映射表之后）
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
    use_memo_pattern = r'const SCENE_COMPONENTS = React\.useMemo\(\(\) => \{([^}]+)\}, \[componentPrefix\]\);'
    use_memo_match = re.search(use_memo_pattern, content, re.DOTALL)
    
    if use_memo_match:
        use_memo_body = use_memo_match.group(1)
        # 检查是否已经包含该 componentPrefix 的匹配
        if f"componentPrefix === '{component_prefix}'" not in use_memo_body:
            # 在 return DEFAULT_SCENE_COMPONENTS 之前添加新的 if 语句
            return_pos = use_memo_body.rfind('return DEFAULT_SCENE_COMPONENTS')
            if return_pos != -1:
                new_if_block = f"    if (componentPrefix === '{component_prefix}') {{\n      return {mapping_table_name};\n    }}\n    "
                use_memo_body = use_memo_body[:return_pos] + new_if_block + use_memo_body[return_pos:]
                # 替换整个 useMemo
                new_use_memo = f"const SCENE_COMPONENTS = React.useMemo(() => {{{use_memo_body}}}, [componentPrefix]);"
                content = re.sub(use_memo_pattern, new_use_memo, content, flags=re.DOTALL)
    else:
        print(f"⚠️  找不到 SCENE_COMPONENTS useMemo，无法自动添加匹配逻辑")
    
    # 写回文件
    with open(video_composer_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已更新 VideoComposer.tsx，添加 {component_prefix} 组件映射")
    return True


def add_video_composer_to_root(config_path, video_id, total_frames, scene_counts, component_prefix=None):
    """在Root.tsx中添加VideoComposer的注册代码"""
    
    root_path = Path(__file__).parent.parent / 'src' / 'Root.tsx'
    
    if not root_path.exists():
        raise FileNotFoundError(f"找不到 Root.tsx: {root_path}")
    
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
    
    # 检查配置文件是否已导入
    if config_import_name not in content:
        # 找到 VideoComposer 导入的位置，在其后添加配置导入
        insert_pos = content.find("import {VideoComposer}")
        if insert_pos != -1:
            line_end = content.find('\n', insert_pos)
            line_end = content.find('\n', line_end + 1)  # 跳到下一行
            content = content[:line_end + 1] + import_statement + '\n' + content[line_end + 1:]
    
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
    composition_code = f"""
      {{/* 🎬 VideoComposer - {video_id} ({total_scenes} scenes: {scene_summary}) */}}
      <Composition
        id="{video_id}"
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
    
    # 检查是否已经存在该Composition
    if f'id="{video_id}"' in content:
        print(f"⚠️  VideoComposer '{video_id}' 已存在，跳过注册")
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
    
    # 生成视频ID（基于meta.title）
    video_id = get_video_id_from_config(config_data)
    print(f"📊 视频ID: {video_id}")
    
    # 生成组件前缀（基于meta.title）
    component_prefix = get_component_prefix_from_config(config_data)
    if component_prefix:
        print(f"📊 组件前缀: {component_prefix}")
    
    # 自动更新 VideoComposer.tsx（如果提供了 component_prefix）
    if component_prefix:
        print(f"\n🔧 正在更新 VideoComposer.tsx...")
        video_composer_path = Path(__file__).parent.parent / 'src' / 'components' / 'CustomInfographic' / 'VideoComposer.tsx'
        try:
            update_video_composer_with_mapping(component_prefix, config_data, video_composer_path)
        except Exception as e:
            print(f"⚠️  更新 VideoComposer 失败: {e}")
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

