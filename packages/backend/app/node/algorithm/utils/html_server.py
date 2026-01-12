#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML服务器模块，用于启动临时HTTP服务器以便截图Vega-Lite图表
"""

import os
import sys
import time
import socket
import threading
import http.server
import socketserver
from pathlib import Path
import webbrowser
import urllib.request
from contextlib import contextmanager

class SimpleHTTPServerWithContentTypes(http.server.SimpleHTTPRequestHandler):
    """扩展的SimpleHTTPRequestHandler，添加了额外的MIME类型"""
    
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.geojson': 'application/json',
        '.md': 'text/markdown',
    }
    
    def __init__(self, *args, **kwargs):
        self.directory = kwargs.pop('directory', os.getcwd())
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """禁用日志输出"""
        pass

def find_free_port():
    """查找可用的端口号"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@contextmanager
def serve_directory(directory=None, port=None, quiet=True):
    """
    启动一个HTTP服务器，在上下文结束时关闭
    
    参数:
        directory: 要服务的目录路径，默认为当前目录
        port: 服务端口，如果为None则自动查找可用端口
        quiet: 是否禁止输出日志
    
    返回:
        服务器的基础URL
    """
    if directory is None:
        directory = os.getcwd()
    else:
        directory = os.path.abspath(directory)
    
    if port is None:
        port = find_free_port()
    elif is_port_in_use(port):
        raise RuntimeError(f"端口 {port} 已被占用")
    
    # 创建服务器
    handler = lambda *args, **kwargs: SimpleHTTPServerWithContentTypes(*args, directory=directory, **kwargs)
    with socketserver.TCPServer(("", port), handler) as httpd:
        # 启动服务器线程
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        if not quiet:
            print(f"启动HTTP服务器: http://localhost:{port}/")
            print(f"服务目录: {directory}")
        
        # 构建服务器URL
        server_url = f"http://localhost:{port}"
        
        try:
            # 等待服务器启动
            for _ in range(5):  # 尝试5次
                try:
                    urllib.request.urlopen(f"{server_url}/")
                    break
                except Exception:
                    time.sleep(0.1)
            
            # 返回服务器URL
            yield server_url
        finally:
            # 关闭服务器
            httpd.shutdown()
            httpd.server_close()
            if not quiet:
                print("HTTP服务器已关闭")

def get_project_root():
    """获取项目根目录"""
    current_path = os.path.abspath(os.path.dirname(__file__))
    # 向上查找，直到找到包含storyteller目录的目录
    while True:
        parent = os.path.dirname(current_path)
        if parent == current_path:  # 已经到达根目录
            return None
        if os.path.exists(os.path.join(parent, 'storyteller')):
            return parent
        current_path = parent

def main():
    """启动HTTP服务器的命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='启动HTTP服务器')
    parser.add_argument('--dir', type=str, help='要服务的目录路径')
    parser.add_argument('--port', type=int, default=None, help='服务端口')
    parser.add_argument('--open', action='store_true', help='自动打开浏览器')
    parser.add_argument('--file', type=str, help='要打开的HTML文件路径')
    
    args = parser.parse_args()
    
    # 如果没有指定目录，尝试查找项目根目录
    if args.dir is None:
        root_dir = get_project_root()
        if root_dir:
            args.dir = root_dir
    
    print(f"启动HTTP服务器，服务目录: {args.dir or os.getcwd()}")
    with serve_directory(args.dir, args.port, quiet=False) as url:
        if args.open:
            # 如果指定了文件，打开该文件
            if args.file:
                file_path = os.path.abspath(args.file)
                dir_path = os.path.abspath(args.dir or os.getcwd())
                if file_path.startswith(dir_path):
                    rel_path = os.path.relpath(file_path, dir_path)
                    webbrowser.open(f"{url}/{rel_path.replace(os.path.sep, '/')}")
                else:
                    print(f"错误: 文件 {args.file} 不在服务目录 {args.dir or os.getcwd()} 中")
            else:
                # 否则直接打开服务器根路径
                webbrowser.open(url)
        
        # 保持程序运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n服务器已终止")

if __name__ == "__main__":
    main() 