from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple

from app.deploy.services.video_naming import (
    extract_dataset_name_from_config,
    scene_id_to_filename,
    scene_needs_component_suffix,
)


def scan_components_for_prefix(
    component_prefix: str,
    components_dir: str,
    config_data: dict | None = None,
    task_id: str | None = None,
) -> Dict[str, Tuple[str, str]]:
    """
    Scan a component directory and match expected scene component files.
    Returns: {scene_id: (component_file_name_without_ext, export_name)}
    """
    if not config_data:
        return {}

    dataset_name = extract_dataset_name_from_config(config_data) or component_prefix
    found_components: Dict[str, Tuple[str, str]] = {}

    for scene in config_data.get("scenes", []):
        scene_id = scene.get("id")
        scene_type = scene.get("type", "")
        if not scene_id:
            continue

        expected_filename = scene_id_to_filename(
            scene_id,
            dataset_name,
            task_id,
            is_animated=True,
            needs_component=scene_needs_component_suffix(scene_id, scene_type),
        )
        file_path = Path(components_dir) / expected_filename

        if not file_path.exists():
            print(f"⚠️  未找到组件文件: {expected_filename} (scene_id: {scene_id})")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as file_obj:
                content = file_obj.read()
        except Exception as exc:
            print(f"⚠️  读取组件文件失败 {expected_filename}: {exc}")
            continue

        export_match = re.search(r"export const (\w+):", content)
        if not export_match:
            continue
        export_name = export_match.group(1)
        component_name = expected_filename.replace(".tsx", "")
        found_components[scene_id] = (component_name, export_name)

    return found_components


def generate_component_mapping_code(
    component_prefix: str,
    config_data: dict,
    components_dir: str,
    task_id: str | None = None,
    is_frontend: bool = False,
) -> Tuple[str, str]:
    """
    Generate import statements and mapping table code for scene components.
    Returns: (import_statements, mapping_table_code)
    """
    found_components = scan_components_for_prefix(
        component_prefix,
        components_dir,
        config_data,
        task_id,
    )

    if not found_components:
        return "", ""

    import_lines: list[str] = []
    mapping_lines: list[str] = []
    config_scenes = {scene.get("id"): scene for scene in config_data.get("scenes", [])}

    ordered_scenes: list[str] = []
    for scene in config_data.get("scenes", []):
        scene_id = scene.get("id")
        if scene_id in found_components:
            ordered_scenes.append(scene_id)

    if not ordered_scenes:
        scene_order = ["scene_opening"] + [f"scene_chart_{i}" for i in range(1, 10)] + [
            "scene_stats",
            "scene_closing",
        ]
        ordered_scenes = [scene_id for scene_id in scene_order if scene_id in found_components]

    for scene_id in ordered_scenes:
        component_name, export_name = found_components[scene_id]
        scene_type = config_scenes.get(scene_id, {}).get("type", "")

        if task_id:
            if is_frontend:
                import_path = f"./{component_prefix}/{task_id}/{component_name}"
            else:
                import_path = f"./{task_id}/{component_name}"
        else:
            import_path = f"./{component_name}"

        if scene_type == "chart" and export_name == "SceneComponentAnimated":
            if scene_id.startswith("scene_chart_"):
                scene_num = scene_id.replace("scene_chart_", "")
                import_alias = f"{component_prefix}_SceneChart{scene_num}Animated"
            else:
                scene_id_camel = "".join(word.capitalize() for word in scene_id.split("_"))
                import_alias = f"{component_prefix}_{scene_id_camel}Animated"
            import_lines.append(
                f"import {{SceneComponentAnimated as {import_alias}}} from '{import_path}';"
            )
            mapping_lines.append(f"  {scene_id}: {import_alias},")
            continue

        import_lines.append(f"import {{{export_name}}} from '{import_path}';")
        mapping_lines.append(f"  {scene_id}: {export_name},")

    import_statements = "\n".join(import_lines) if import_lines else ""
    mapping_table_name = f"{component_prefix.upper()}_COMPONENTS"
    mapping_table = (
        f"""const {mapping_table_name}: Record<string, React.FC<any>> = {{
{chr(10).join(mapping_lines)}
}};"""
        if mapping_lines
        else ""
    )
    return import_statements, mapping_table


def update_video_composer_with_mapping(
    component_prefix: str,
    config_data: dict,
    video_composer_path: Path,
    task_id: str | None = None,
    is_frontend: bool = False,
) -> bool:
    """
    Update VideoComposer.tsx with new imports and scene component mappings.
    """
    if not video_composer_path.exists():
        print(f"⚠️  VideoComposer.tsx 不存在: {video_composer_path}")
        return False

    if task_id:
        if is_frontend:
            components_dir = str(video_composer_path.parent / component_prefix / task_id)
        else:
            components_dir = str(video_composer_path.parent / task_id)
    else:
        if is_frontend:
            components_dir = str(video_composer_path.parent / component_prefix)
        else:
            components_dir = str(video_composer_path.parent)

    with open(video_composer_path, "r", encoding="utf-8") as file_obj:
        content = file_obj.read()

    mapping_table_name = f"{component_prefix.upper()}_COMPONENTS"
    mapping_exists = mapping_table_name in content
    import_statements, mapping_table = generate_component_mapping_code(
        component_prefix,
        config_data,
        components_dir,
        task_id,
        is_frontend=is_frontend,
    )

    if not import_statements or not mapping_table:
        print("⚠️  未找到匹配的组件，跳过 VideoComposer 更新")
        return False

    if mapping_exists:
        print(f"ℹ️  映射表 {mapping_table_name} 已存在，将强制更新以确保正确性")

    needs_import_update = mapping_exists or import_statements not in content
    if needs_import_update and import_statements:
        import_pattern = r"^import\s+.*?from\s+['\"][^'\"]+['\"];"
        import_matches = list(re.finditer(import_pattern, content, re.MULTILINE))
        if import_matches:
            last_import = import_matches[-1]
            insert_pos = content.find("\n", last_import.end())
            if insert_pos == -1:
                insert_pos = last_import.end()
            import_block = f"\n// 导入 {component_prefix} 相关组件\n{import_statements}\n"
            content = content[:insert_pos] + import_block + content[insert_pos:]
        else:
            print("⚠️  找不到 import 语句位置，跳过 import 添加")

    mapping_updated = False
    if mapping_exists:
        mapping_start_pattern = (
            rf"const\s+{re.escape(mapping_table_name)}:\s*Record<string,\s*React\.FC<any>>\s*="
        )
        mapping_start_match = re.search(mapping_start_pattern, content)
        if mapping_start_match:
            start_pos = mapping_start_match.start()
            comment_start = content.rfind("//", max(0, start_pos - 100), start_pos)
            if comment_start != -1:
                line_start = content.rfind("\n", max(0, comment_start - 1), comment_start)
                start_pos = line_start + 1 if line_start != -1 else comment_start

            brace_count = 0
            end_pos = mapping_start_match.end()
            for index, char in enumerate(content[end_pos:], start=end_pos):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = index + 1
                        if end_pos < len(content) and content[end_pos] == "\n":
                            end_pos += 1
                        break

            mapping_block = f"// {component_prefix} 组件映射表\n{mapping_table}\n"
            old_mapping_content = content[start_pos:end_pos]
            if old_mapping_content.strip() != mapping_block.strip():
                content = content[:start_pos] + mapping_block + content[end_pos:]
                mapping_updated = True
                print(f"✅ 已替换映射表 {mapping_table_name}")
            else:
                print(f"ℹ️  映射表 {mapping_table_name} 内容未变化，跳过更新")
        else:
            print(f"⚠️  找不到映射表 {mapping_table_name} 的位置，尝试添加新映射表")
            mapping_exists = False

    if not mapping_exists:
        mapping_pattern = r"const\s+\w+_COMPONENTS:\s*Record<string,\s*React\.FC<any>>\s*="
        mapping_matches = list(re.finditer(mapping_pattern, content))
        if mapping_matches:
            last_mapping = mapping_matches[-1]
            start_pos = last_mapping.end()
            brace_count = 0
            end_pos = start_pos
            for index, char in enumerate(content[start_pos:], start=start_pos):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = index + 1
                        break
            mapping_block = f"\n\n// {component_prefix} 组件映射表\n{mapping_table}\n"
            content = content[:end_pos] + mapping_block + content[end_pos:]
        else:
            default_pos = content.find("const DEFAULT_SCENE_COMPONENTS")
            if default_pos != -1:
                start_pos = default_pos
                brace_count = 0
                end_pos = start_pos
                for index, char in enumerate(content[start_pos:], start=start_pos):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = index + 1
                            break
                mapping_block = f"\n\n// {component_prefix} 组件映射表\n{mapping_table}\n"
                content = content[:end_pos] + mapping_block + content[end_pos:]

    use_memo_pattern = (
        r"const SCENE_COMPONENTS = React\.useMemo\(\(\) => \{([\s\S]*?)\}, \[componentPrefix\]\);"
    )
    use_memo_match = re.search(use_memo_pattern, content, re.DOTALL)
    already_exists = False
    if use_memo_match:
        use_memo_body = use_memo_match.group(1)
        check_patterns = [
            f"componentPrefix === '{component_prefix}'",
            f'componentPrefix === "{component_prefix}"',
            f"'{component_prefix}'",
            f'"{component_prefix}"',
        ]
        already_exists = any(pattern in use_memo_body for pattern in check_patterns)
        if not already_exists:
            return_pos = use_memo_body.rfind("return DEFAULT_SCENE_COMPONENTS")
            if return_pos != -1:
                return_line_start = use_memo_body.rfind("\n", 0, return_pos)
                return_line_start = 0 if return_line_start == -1 else return_line_start + 1
                indent_str = use_memo_body[return_line_start:return_pos]
                indent_level = len(indent_str) - len(indent_str.lstrip()) or 4
                indent = " " * indent_level
                new_if_block = (
                    f"{indent}if (componentPrefix === '{component_prefix}') {{\n"
                    f"{indent}  return {mapping_table_name};\n"
                    f"{indent}}}\n"
                )
                use_memo_body = use_memo_body[:return_pos] + new_if_block + use_memo_body[return_pos:]
                new_use_memo = (
                    f"const SCENE_COMPONENTS = React.useMemo(() => {{{use_memo_body}}}, [componentPrefix]);"
                )
                content = re.sub(use_memo_pattern, new_use_memo, content, flags=re.DOTALL)
                print(f"✅ 已自动添加 {component_prefix} 到 useMemo 匹配逻辑")
            else:
                print("⚠️  找不到 'return DEFAULT_SCENE_COMPONENTS'，无法自动添加匹配逻辑")
        else:
            print(f"ℹ️  {component_prefix} 的匹配逻辑已存在，跳过更新")
    else:
        print("⚠️  找不到 SCENE_COMPONENTS useMemo，无法自动添加匹配逻辑")

    updated = (not mapping_exists) or mapping_updated or (use_memo_match and not already_exists)
    if updated:
        with open(video_composer_path, "w", encoding="utf-8") as file_obj:
            file_obj.write(content)
        if not mapping_exists:
            print(f"✅ 已更新 VideoComposer.tsx，添加 {component_prefix} 组件映射")
        else:
            print(f"✅ 已更新 VideoComposer.tsx 的 useMemo，添加 {component_prefix} 匹配逻辑")
    else:
        print("ℹ️  VideoComposer.tsx 无需更新（映射表和 useMemo 都已存在）")

    return True
