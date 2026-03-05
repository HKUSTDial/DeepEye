#!/usr/bin/env python3
"""
自动注册生成的 TSX 组件到 Remotion 项目

功能：
1. 扫描生成的 TSX 组件
2. 复制到目标目录（默认 copy-only 模式写入运行时目录）
3. 自动在 src/Root.tsx 中注册
4. 配置持续时间（根据配置文件）
"""
import os
import shutil
import json
import re
from typing import List, Dict


VIDEO_RUNTIME_BASE = os.getenv("VIDEO_RUNTIME_BASE", "/workspace/video_runtime")
DEFAULT_COMPONENTS_OUTPUT_BASE = os.getenv(
    "VIDEO_COMPONENTS_OUTPUT_BASE",
    os.path.join(VIDEO_RUNTIME_BASE, "claude_tsx_components"),
)
DEFAULT_ANIMATED_OUTPUT_BASE = os.getenv(
    "VIDEO_ANIMATED_OUTPUT_BASE",
    os.path.join(VIDEO_RUNTIME_BASE, "claude_tsx_animated"),
)
DEFAULT_COPY_TARGET_DIR = os.getenv(
    "VIDEO_REGISTER_TARGET_DIR",
    os.path.join(VIDEO_RUNTIME_BASE, "registered_components"),
)


def scan_generated_components(output_dir: str) -> List[Dict[str, str]]:
    """扫描生成的 TSX 组件"""
    components = []
    
    if not os.path.exists(output_dir):
        print(f"❌ 输出目录不存在: {output_dir}")
        return components
    
    for filename in sorted(os.listdir(output_dir)):
        if filename.endswith('.tsx'):
            file_path = os.path.join(output_dir, filename)
            component_name = filename.replace('.tsx', '')
            
            # 读取组件内容，提取导出名称
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找 export const XXX 的导出名称
                match = re.search(r'export const (\w+):', content)
                if match:
                    export_name = match.group(1)
                else:
                    export_name = component_name  # 默认使用文件名
            
            components.append({
                'filename': filename,
                'component_name': component_name,
                'export_name': export_name,
                'source_path': file_path
            })
    
    return components


def copy_components_to_project(components: List[Dict[str, str]], target_dir: str, task_id: str = None):
    """复制组件到项目目录
    如果提供了 task_id，创建任务子目录：target_dir/{task_id}/
    否则直接复制到 target_dir/
    """
    if task_id:
        # 创建任务子目录
        task_target_dir = os.path.join(target_dir, task_id)
        os.makedirs(task_target_dir, exist_ok=True)
        print(f"\n📂 复制组件到任务目录: {task_target_dir}")
    else:
        # 直接复制到目标目录（兼容旧逻辑）
        task_target_dir = target_dir
        os.makedirs(task_target_dir, exist_ok=True)
        print(f"\n📂 复制组件到项目目录: {task_target_dir}")
    
    for comp in components:
        target_path = os.path.join(task_target_dir, comp['filename'])
        shutil.copy2(comp['source_path'], target_path)
        print(f"   ✅ {comp['filename']} → {target_path}")


def get_scene_duration(config_path: str, scene_id: str) -> int:
    """从配置文件获取场景持续时间（帧数）"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        scenes = config.get('scenes', [])
        fps = config.get('meta', {}).get('fps', 30)
        
        for scene in scenes:
            if scene.get('id') == scene_id:
                # 优先使用 time_range 数组
                if 'time_range' in scene and isinstance(scene['time_range'], list) and len(scene['time_range']) >= 2:
                    time_start = scene['time_range'][0]
                    time_end = scene['time_range'][1]
                    duration_seconds = time_end - time_start
                    return int(duration_seconds * fps)
                # 兼容旧格式：time_start 和 time_end
                elif 'time_start' in scene and 'time_end' in scene:
                    time_start = scene.get('time_start', 0)
                    time_end = scene.get('time_end', 0)
                    duration_seconds = time_end - time_start
                    return int(duration_seconds * fps)
        
        return 300  # 默认 300 帧（10秒）
    except Exception as e:
        print(f"⚠️  获取场景时长失败: {e}")
        return 300


def update_root_tsx(components: List[Dict[str, str]], root_tsx_path: str, config_path: str):
    """自动更新 Root.tsx 文件"""
    
    if not os.path.exists(root_tsx_path):
        print(f"❌ Root.tsx 文件不存在: {root_tsx_path}")
        return
    
    with open(root_tsx_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 添加 import 语句
    print(f"\n📝 更新 Root.tsx...")
    import_lines = []
    for comp in components:
        import_line = f"import {{{comp['export_name']}}} from './components/CustomInfographic/{comp['filename'].replace('.tsx', '')}';"
        
        # 检查是否已存在
        if import_line not in content:
            import_lines.append(import_line)
    
    if import_lines:
        # 找到 Claude 生成的组件导入区域
        claude_import_marker = "// Claude 生成的完整 TSX 组件"
        if claude_import_marker in content:
            # 在这个标记后插入
            content = content.replace(
                claude_import_marker,
                claude_import_marker + '\n' + '\n'.join(import_lines)
            )
        else:
            # 如果没有标记，在第一个 import 后插入
            first_import_end = content.find('\n', content.find('import'))
            content = content[:first_import_end] + '\n' + '\n'.join(import_lines) + content[first_import_end:]
        
        print(f"   ✅ 添加了 {len(import_lines)} 个 import 语句")
    
    # 2. 添加 Composition 注册
    composition_lines = []
    for comp in components:
        # 尝试从文件名推断 scene_id
        # 支持新格式：GooglePlayStoreAnaly_SceneChart1 -> scene_chart_1
        # 也支持旧格式：SceneChart1 -> scene_chart_1
        scene_id_match = re.search(r'(?:.*_)?Scene(Chart\d+|Opening|Closing)', comp['component_name'])
        if scene_id_match:
            scene_type = scene_id_match.group(1)
            if scene_type.startswith('Chart'):
                scene_id = f"scene_chart_{scene_type.replace('Chart', '').lower()}"
            elif scene_type == 'Opening':
                scene_id = 'scene_opening'
            elif scene_type == 'Closing':
                scene_id = 'scene_closing'
            else:
                scene_id = f"scene_{scene_type.lower()}"
        else:
            # 如果不匹配，则使用组件名的小写版本
            scene_id = comp['component_name'].lower()
        
        duration = get_scene_duration(config_path, scene_id)
        
        # Composition ID 不能包含下划线，替换为连字符
        composition_id = comp['component_name'].replace('_', '-')
        
        composition_block = f"""
      <Composition
        id="{composition_id}"
        component={{{comp['export_name']}}}
        durationInFrames={{{duration}}}
        fps={{30}}
        width={{1280}}
        height={{720}}
      />"""
        
        # 检查是否已存在（通过 id 判断）
        if f'id="{composition_id}"' not in content:
            composition_lines.append(composition_block)
    
    if composition_lines:
        # 在最后一个 Composition 后插入，但要在 </> 之前
        # 策略：
        # 1. 查找 </> 的位置
        # 2. 在 </> 之前插入新的 Composition
        
        closing_fragment = content.rfind('</>')
        if closing_fragment != -1:
            # 找到了 </>，在它之前插入
            # 找到 </> 所在行的开始
            line_start = content.rfind('\n', 0, closing_fragment)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            
            # 在该行之前插入
            content = content[:line_start] + ''.join(composition_lines) + '\n\n' + content[line_start:]
            print(f"   ✅ 注册了 {len(composition_lines)} 个 Composition")
        else:
            # 如果找不到 </>，尝试查找最后一个 Composition
            last_composition_end = content.rfind('</Composition>')
            if last_composition_end == -1:
                # 查找自闭合标签 />
                pos = len(content) - 1
                while pos > 0:
                    closing_pos = content.rfind('/>', 0, pos)
                    if closing_pos == -1:
                        break
                    # 向前查找是否有 <Composition
                    comp_start = content.rfind('<Composition', max(0, closing_pos - 500), closing_pos)
                    if comp_start != -1:
                        last_composition_end = closing_pos + 2
                        break
                    pos = closing_pos - 1
            
            if last_composition_end != -1:
                insert_pos = content.find('\n', last_composition_end)
                if insert_pos != -1:
                    insert_pos += 1
                else:
                    insert_pos = last_composition_end
                content = content[:insert_pos] + ''.join(composition_lines) + '\n' + content[insert_pos:]
                print(f"   ✅ 注册了 {len(composition_lines)} 个 Composition")
            else:
                print(f"   ⚠️  无法找到插入位置，跳过 Composition 注册")
    
    # 保存更新后的文件
    with open(root_tsx_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Root.tsx 更新完成")


def main():
    import argparse
    default_config_path = os.getenv(
        "VIDEO_DEFAULT_CONFIG_PATH",
        "infographic_generation/generated_config_aligned.json",
    )
    
    # 命令行参数
    parser = argparse.ArgumentParser(description='自动注册 TSX 组件到 Remotion 项目')
    parser.add_argument('--animated', action='store_true', help='注册带动画的组件（默认注册静态组件）')
    parser.add_argument('--config', type=str,
                       default=default_config_path,
                       help='配置文件路径')
    parser.add_argument('--task-id', type=str, default=None,
                       help='任务ID（用于扫描子目录）')
    parser.add_argument('--copy-only', action='store_true',
                       help='只复制组件文件，不注册为 Composition')
    parser.add_argument('--base-output-dir', type=str, default=None,
                       help='覆盖默认输出基础目录（用于外部自定义渲染目录）')
    parser.add_argument('--target-dir', type=str, default=None,
                       help='复制目标目录（默认 copy-only 写入运行时目录，注册模式写入 src/components/CustomInfographic）')
    args = parser.parse_args()
    
    # 配置路径
    if args.base_output_dir:
        base_output_dir = args.base_output_dir
        print(f"🚀 使用自定义输出目录扫描组件: {base_output_dir}")
    elif args.animated:
        base_output_dir = DEFAULT_ANIMATED_OUTPUT_BASE
        print("🚀 自动注册**动画**组件到 Remotion 项目...")
    else:
        base_output_dir = DEFAULT_COMPONENTS_OUTPUT_BASE
        print("🚀 自动注册**静态**组件到 Remotion 项目...")
    
    # 如果提供了 task_id，则扫描子目录
    if args.task_id:
        output_dir = os.path.join(base_output_dir, args.task_id)
        print(f"📁 扫描任务子目录: {output_dir}")
    else:
        output_dir = base_output_dir
        print(f"📁 扫描默认目录: {output_dir}")
    
    if args.target_dir:
        target_dir = args.target_dir
    elif args.copy_only:
        target_dir = DEFAULT_COPY_TARGET_DIR
    else:
        target_dir = "src/components/CustomInfographic"

    print(f"📂 复制目标目录: {target_dir}")
    root_tsx_path = "src/Root.tsx"
    config_path = args.config
    
    print("="*70)
    
    # 1. 扫描生成的组件
    components = scan_generated_components(output_dir)
    
    if not components:
        print(f"❌ 未找到生成的组件，请先运行 generate_with_claude.py")
        return
    
    print(f"\n✅ 找到 {len(components)} 个组件:")
    for comp in components:
        print(f"   - {comp['filename']} (export: {comp['export_name']})")
    
    # 2. 复制到项目（如果提供了 task_id，创建任务子目录）
    copy_components_to_project(components, target_dir, args.task_id)
    
    # 3. 更新 Root.tsx（如果不是只复制模式）
    if args.copy_only:
        print("\n✅ 组件文件已复制（跳过 Root.tsx 注册）")
    else:
        update_root_tsx(components, root_tsx_path, config_path)
    
    # 总结
    print("\n" + "="*70)
    if args.copy_only:
        print("\n🎉 组件复制完成！")
    else:
        print("\n🎉 自动注册完成！")
    print(f"\n📺 现在可以查看组件：")
    print(f"   1. 运行 'npm run dev' 启动 Remotion Studio")
    print(f"   2. 在浏览器中打开显示的 URL（通常是 http://localhost:3000）")
    print(f"   3. 在左侧列表中选择组件（例如：SceneChart1）")
    print(f"   4. 点击播放按钮预览效果")
    print(f"\n💡 提示：")
    print(f"   - 组件已注册为独立的 Composition，可以单独预览")
    print(f"   - 持续时间已根据配置文件自动设置")
    print(f"   - 如果需要修改，可以直接编辑 src/Root.tsx")


if __name__ == "__main__":
    main()
