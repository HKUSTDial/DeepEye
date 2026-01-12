import os
import subprocess
import glob
import argparse

def process_all_reports(specific_dir=None):
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
    
    for iteration_dir in sorted(iteration_dirs):
        # 检查是否存在report.md文件
        report_path = os.path.join(iteration_dir, 'report.md')
        if os.path.exists(report_path):
            print(f"正在处理: {report_path}")
            
            # 生成报告
            output_file = os.path.join(iteration_dir, f'report_dashboard.html')
            print(f"  生成报告...")
            
            # 调用报告生成脚本（不再传递--template参数）
            cmd = [
                'python', 
                'storyteller/algorithm/utils/generate_report_from_md.py', 
                report_path, 
                '--output', output_file
            ]
            
            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(f"    {result.stdout.strip()}")
            except subprocess.CalledProcessError as e:
                print(f"    处理 {report_path} 时出错: {e}")
                print(f"    错误详情: {e.stderr}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='处理所有Markdown报告并生成HTML文件')
    parser.add_argument('--dir', type=str, help='处理特定目录而不是所有iteration目录')
    args = parser.parse_args()
    
    process_all_reports(args.dir)
    
    print(f"所有报告已处理完成！")
    