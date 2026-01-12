import os
import subprocess
import glob
import argparse

def process_all_reports(template='dashboard', all_templates=False, specific_dir=None):
    # 如果指定了特定目录，只处理该目录
    if specific_dir:
        if os.path.exists(specific_dir) and os.path.isdir(specific_dir):
            iteration_dirs = [specific_dir]
        else:
            print(f"错误: 指定的目录 '{specific_dir}' 不存在或不是目录")
            return
    else:
        # 否则查找所有iteration目录
        base_dir = 'storyteller/output/iterations'
        iteration_dirs = glob.glob(f'{base_dir}/iteration_*')
    
    # 如果指定了生成所有模板，则使用所有可用模板
    templates_to_use = ['sidebar', 'grid', 'magazine', 'dashboard'] if all_templates else [template]
    
    for iteration_dir in sorted(iteration_dirs):
        # 检查是否存在report.md文件
        report_path = os.path.join(iteration_dir, 'report.md')
        if os.path.exists(report_path):
            print(f"正在处理: {report_path}")
            
            # 对每个模板生成报告
            for template_style in templates_to_use:
                output_file = os.path.join(iteration_dir, f'report_{template_style}.html')
                print(f"  生成 {template_style} 模板...")
                
                # 调用报告生成脚本
                cmd = [
                    'python', 
                    'storyteller/algorithm/utils/generate_report_from_md.py', 
                    report_path, 
                    '--output', output_file,
                    '--template', template_style
                ]
                
                try:
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    print(f"    {result.stdout.strip()}")
                except subprocess.CalledProcessError as e:
                    print(f"    处理 {report_path} 使用 {template_style} 时出错: {e}")
                    print(f"    错误详情: {e.stderr}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='处理所有Markdown报告并生成HTML文件')
    parser.add_argument('--template', choices=['sidebar', 'grid', 'magazine', 'dashboard'], 
                        default='dashboard', help='使用的模板样式')
    parser.add_argument('--all', action='store_true', help='使用所有可用模板生成报告')
    parser.add_argument('--dir', type=str, help='处理特定目录而不是所有iteration目录')
    args = parser.parse_args()
    
    process_all_reports(args.template, args.all, args.dir)
    
    if args.all:
        print("所有报告已使用所有模板样式处理完成！")
    else:
        print(f"所有报告已使用 {args.template} 模板处理完成！")
    