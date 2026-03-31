from __future__ import annotations

import json
import os
import re
from pathlib import Path


def get_config_import_name(video_id):
    """生成配置文件的import变量名"""
    name = video_id.replace('FullVideo', '').replace('-', '').replace('_', '')
    if not name:
        return 'configJson'
    if name[0].isdigit():
        return 'config' + name + 'Json'
    return name[0].lower() + name[1:] + 'Json'


def add_video_composer_to_root(config_path, video_id, total_frames, scene_counts, component_prefix=None):
    """在Root.tsx中添加VideoComposer的注册代码"""

    root_path = Path(__file__).parent.parent.parent / 'src' / 'Root.tsx'

    if not root_path.exists():
        print(f"⚠️  Root.tsx 不存在: {root_path}")
        print(f"   这在 Docker 环境中是正常的，Remotion 项目可能不在容器内")
        print(f"   TSX 组件文件已生成，可以在 Remotion 项目中手动注册")
        return False

    with open(root_path, 'r', encoding='utf-8') as f:
        content = f.read()

    config_import_name = get_config_import_name(video_id)
    config_rel_path = os.path.relpath(config_path, root_path.parent)
    config_import_path = config_rel_path.replace('\\', '/')
    if not config_import_path.startswith('../'):
        config_import_path = '../' + config_import_path

    import_statement = f"import {config_import_name} from '{config_import_path}';"

    if 'import {VideoComposer}' not in content:
        video_composer_import = """
// VideoComposer - 通用视频串联组件
import {VideoComposer} from './components/CustomInfographic/VideoComposer';"""

        insert_pos = content.rfind("import {ClaudeRevenueStatic_v2}")
        if insert_pos == -1:
            insert_pos = content.find("// 兼容 Remotion Composition")
        if insert_pos == -1:
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
            first_import_end = content.find('\n', content.find('import'))
            if first_import_end != -1:
                content = content[:first_import_end + 1] + video_composer_import + '\n' + content[first_import_end + 1:]

    import_updated = False
    if config_import_name not in content:
        insert_pos = content.find("import {VideoComposer}")
        if insert_pos != -1:
            line_end = content.find('\n', insert_pos)
            line_end = content.find('\n', line_end + 1)
            content = content[:line_end + 1] + import_statement + '\n' + content[line_end + 1:]
            import_updated = True
            print(f"✅ 添加配置文件导入: {config_import_path}")
    else:
        pattern = rf"import {re.escape(config_import_name)} from ['\"]([^'\"]+)['\"];"
        match = re.search(pattern, content)
        if match:
            old_path = match.group(1)
            if old_path != config_import_path:
                content = re.sub(pattern, f"import {config_import_name} from '{config_import_path}';", content)
                import_updated = True
                print(f"✅ 更新配置文件导入路径: {old_path} -> {config_import_path}")

    if import_updated:
        with open(root_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 已保存导入路径更新")
        with open(root_path, 'r', encoding='utf-8') as f:
            content = f.read()

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

    scene_components_code = ""
    if component_prefix:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data_for_components = json.load(f)

        scene_components_lines = []

        for scene in config_data_for_components.get('scenes', []):
            scene_id = scene.get('id', '')
            if not scene_id:
                continue

            if scene_id == 'scene_opening':
                component_name = f"{component_prefix}_SceneOpeningComponent"
            elif scene_id == 'scene_closing':
                component_name = f"{component_prefix}_SceneClosingComponent"
            elif scene_id.startswith('scene_chart_'):
                chart_num = scene_id.replace('scene_chart_', '')
                component_name = f"{component_prefix}_SceneChart{chart_num}Animated"
            else:
                continue

            if component_name in content:
                scene_components_lines.append(f"            {scene_id}: {component_name},")

        if scene_components_lines:
            scene_components_code = f"""
          sceneComponents: {{{{
{chr(10).join(scene_components_lines)}
          }}}},"""

    component_prefix_prop = f"componentPrefix: '{component_prefix}'," if component_prefix else ""
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

    if f'id="{composition_id}"' in content:
        print(f"ℹ️  VideoComposer '{composition_id}' 已存在，尝试更新配置...")

        composition_pattern = rf'(\{{\s*/\*.*?VideoComposer.*?{re.escape(video_id)}.*?\*/\s*<Composition[\s\S]*?id="{re.escape(composition_id)}"[\s\S]*?</Composition>\s*}})'
        match = re.search(composition_pattern, content, re.DOTALL)

        if match:
            old_composition = match.group(1)
            if f'configJson: {config_import_name}' not in old_composition:
                updated_composition = re.sub(
                    r'configJson:\s*\w+,',
                    f'configJson: {config_import_name},',
                    old_composition,
                )
                updated_composition = re.sub(
                    r'durationInFrames=\{\{\d+\}\}',
                    f'durationInFrames={{{total_frames}}}',
                    updated_composition,
                )
                updated_composition = re.sub(
                    r'\(\d+\s+scenes:.*?\)',
                    f'({total_scenes} scenes: {scene_summary})',
                    updated_composition,
                )

                content = content.replace(old_composition, updated_composition)
                print(f"✅ 已更新 Composition '{composition_id}' 的配置")
                print(f"   - 配置文件: {config_import_path}")
                print(f"   - 总时长: {total_frames} 帧")

                with open(root_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

            print(f"ℹ️  配置变量 {config_import_name} 已存在，跳过更新")
            return True

        print(f"⚠️  无法找到 Composition '{composition_id}' 的完整代码块，尝试直接匹配标签...")
        composition_regex = rf'<Composition[\s\S]*?id="{re.escape(composition_id)}"[\s\S]*?(?:/>|</Composition>)'
        match = re.search(composition_regex, content, re.DOTALL)

        if match:
            composition_section = match.group(0)
            comment_start = match.start()
            end_pos = match.end()

            if '{/*' not in composition_section:
                comment_pos = content.rfind('{/*', max(0, comment_start - 500), comment_start)
                if comment_pos != -1:
                    comment_end = content.find('*/}', comment_pos, comment_start)
                    if comment_end != -1:
                        comment_end += 3
                        composition_section = content[comment_pos:end_pos]
                        comment_start = comment_pos

            if end_pos > comment_start and end_pos > 0 and end_pos <= len(content):
                composition_section = content[comment_start:end_pos]

                if end_pos < len(content) and content[end_pos] == '\n':
                    end_pos += 1
                    if end_pos < len(content) and content[end_pos] == '\n':
                        end_pos += 1
                    composition_section = content[comment_start:end_pos]

                needs_update = False
                updated_section = composition_section

                config_json_pattern = r'configJson:\s*(\w+),'
                config_match = re.search(config_json_pattern, updated_section)
                if config_match:
                    old_config_var = config_match.group(1)
                    if old_config_var != config_import_name:
                        updated_section = re.sub(
                            config_json_pattern,
                            f'configJson: {config_import_name},',
                            updated_section,
                        )
                        needs_update = True
                        print(f"   ✅ 更新 configJson: {old_config_var} -> {config_import_name}")

                duration_pattern = r'durationInFrames=\{\{(\d+)\}\}'
                duration_match = re.search(duration_pattern, updated_section)
                if duration_match:
                    old_duration = int(duration_match.group(1))
                    if old_duration != total_frames:
                        updated_section = re.sub(
                            duration_pattern,
                            f'durationInFrames={{{total_frames}}}',
                            updated_section,
                        )
                        needs_update = True
                        print(f"   ✅ 更新 durationInFrames: {old_duration} -> {total_frames}")

                scene_count_pattern = r'\(\d+\s+scenes:.*?\)'
                if re.search(scene_count_pattern, updated_section):
                    updated_section = re.sub(
                        scene_count_pattern,
                        f'({total_scenes} scenes: {scene_summary})',
                        updated_section,
                    )
                    needs_update = True
                    print(f"   ✅ 更新场景数量注释")

                if needs_update:
                    content = content[:comment_start] + updated_section + content[end_pos:]
                    with open(root_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ 已更新 Composition '{composition_id}' 的配置（通过字段更新）")
                    print(f"   - 配置文件: {config_import_path}")
                    print(f"   - 总时长: {total_frames} 帧")
                    return True

                print(f"ℹ️  配置已是最新，无需更新")
                return True

            if end_pos == -1:
                print(f"⚠️  无法找到 Composition '{composition_id}' 的结束位置（既不是 </Composition> 也不是 />）")
            elif end_pos <= comment_start:
                print(f"⚠️  结束位置 ({end_pos}) 不晚于开始位置 ({comment_start})")
            elif end_pos > len(content):
                print(f"⚠️  结束位置 ({end_pos}) 超出文件长度 ({len(content)})")
            else:
                print(f"⚠️  无法定位 Composition '{composition_id}' 的边界（未知原因）")
            return False

        print(f"⚠️  无法找到 Composition '{composition_id}' 的 id 属性，跳过更新")
        return False

    end_marker = '{/* === END AUTO-GENERATED COMPOSITIONS === */}'
    end_pos = content.find(end_marker)

    if end_pos == -1:
        last_composition_end = content.rfind('</Composition>')
        if last_composition_end != -1:
            line_end = content.find('\n', last_composition_end)
            if line_end != -1:
                end_pos = line_end + 1
            else:
                end_pos = last_composition_end + len('</Composition>')
        else:
            closing_tag_pos = content.rfind('</>')
            if closing_tag_pos != -1:
                end_pos = closing_tag_pos
            else:
                raise ValueError("找不到合适的插入位置：既没有 END AUTO-GENERATED COMPOSITIONS 标记，也没有找到 Composition 或 </>")

    content = content[:end_pos] + composition_code + '\n      ' + content[end_pos:]

    with open(root_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True
