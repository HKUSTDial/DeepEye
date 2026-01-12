import asyncio
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import os
import threading
import http.server
import socketserver
import time
from typing import Optional, Tuple

# 添加一个简易的HTTP服务器类
class SimpleHTTPServerHandler(http.server.SimpleHTTPRequestHandler):
    """自定义HTTP处理器，支持CORS和自定义根目录"""
    
    def __init__(self, *args, **kwargs):
        self.directory = kwargs.pop('directory', os.getcwd())
        super().__init__(*args, **kwargs)
    
    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Origin, Content-Type, Accept')
        super().end_headers()
    
    def log_message(self, format, *args):
        # 静默日志
        pass

def start_http_server(root_dir, port=0) -> Tuple[int, socketserver.TCPServer]:
    """
    启动一个简易的HTTP服务器
    
    参数:
        root_dir: 服务器根目录
        port: 端口号(0表示自动选择可用端口)
    
    返回:
        (port, server): 服务器使用的端口和服务器对象
    """
    # 创建处理器
    handler = lambda *args, **kwargs: SimpleHTTPServerHandler(*args, directory=root_dir, **kwargs)
    
    # 创建服务器 - 注意不使用with语句，因为会自动关闭
    httpd = socketserver.TCPServer(("localhost", port), handler)
    
    # 获取实际使用的端口
    actual_port = httpd.server_address[1]
    print(f"🌐 启动临时HTTP服务器于端口 {actual_port}，根目录: {root_dir}")
    
    # 创建服务器线程
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    
    # 等待服务器启动完成
    time.sleep(1)
    
    return actual_port, httpd

async def html_to_image(html_content: str, output_path: Optional[str] = None, width: int = 1280, height: int = None) -> str:
    """
    将HTML内容转换为图片
    
    参数:
        html_content: HTML字符串
        output_path: 输出图片路径（可选）
        width: 视口宽度
        height: 视口高度（如果为None则自动计算）
    
    返回:
        str: 生成的图片路径
    """
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # 设置视口大小
        await page.set_viewport_size({"width": width, "height": height or 800})
        
        # 加载HTML内容
        await page.set_content(html_content, wait_until="networkidle")
        
        # 如果没有指定高度，获取内容实际高度
        if height is None:
            height = await page.evaluate('document.documentElement.scrollHeight')
            await page.set_viewport_size({"width": width, "height": height})
        
        # 确定输出路径
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(__file__), "../../../output/temp")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "report_snapshot.png")
        
        # 截图
        await page.screenshot(
            path=output_path,
            full_page=True,
            type="png"
        )
        
        await browser.close()
        return output_path

def convert_html_to_image(html_content: str, output_path: Optional[str] = None) -> str:
    """同步版本的HTML转图片函数"""
    return asyncio.run(html_to_image(html_content, output_path))

def convert_html_file_to_image(html_file, output_path=None, debug=False):
    """
    将HTML文件转换为图片，特别优化以确保Vega-Lite图表正确渲染
    
    参数:
        html_file: HTML文件路径
        output_path: 输出图片路径（可选）
        debug: 是否打印调试信息
    
    返回:
        str: 生成的图片路径
    """
    # 确定输出路径
    if output_path is None:
        output_path = os.path.splitext(html_file)[0] + ".png"
    
    if debug:
        print(f"开始处理HTML文件: {html_file}")
        print(f"输出路径: {output_path}")
    
    # 获取项目根目录
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    
    # 启动临时HTTP服务器
    httpd = None
    try:
        port, httpd = start_http_server(project_root)
        
        # 计算HTML文件的相对路径
        rel_path = os.path.relpath(html_file, project_root)
        url = f"http://localhost:{port}/{rel_path.replace(os.sep, '/')}"
        
        if debug:
            print(f"项目根目录: {project_root}")
            print(f"启动HTTP服务器: http://localhost:{port}/")
            print(f"访问HTML文件: {url}")
        
        # 验证服务器是否正常运行
        import requests
        try:
            # 尝试访问服务器，确认可用
            test_url = f"http://localhost:{port}/"
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                if debug:
                    print(f"HTTP服务器测试成功: 状态码 {response.status_code}")
            else:
                print(f"⚠️ HTTP服务器似乎不正常: 状态码 {response.status_code}")
        except Exception as e:
            print(f"⚠️ 无法连接到HTTP服务器: {e}")
            return None
        
        # 使用 playwright 的同步 API
        with sync_playwright() as playwright:
            # 启动带有参数的浏览器，禁用沙箱可以减少一些问题
            browser = playwright.chromium.launch(
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                headless=True  # 无头浏览器模式
            )
            
            try:
                # 创建页面对象
                context = browser.new_context(
                    viewport={'width': 1600, 'height': 900},  # 增加视口大小
                    device_scale_factor=1.5  # 提高渲染清晰度
                )
                page = context.new_page()
                
                # 加载HTML文件(通过HTTP服务器)
                page.goto(url, 
                        wait_until="domcontentloaded",  # 等待DOM内容加载
                        timeout=60000)  # 增加超时时间到60秒
                
                if debug:
                    print("HTML文件已加载")
                
                # 等待DOM完全加载
                page.wait_for_load_state("load", timeout=60000)
                if debug:
                    print("页面完全加载")
                
                # 确保外部脚本加载完成
                page.wait_for_load_state("networkidle", timeout=60000)
                if debug:
                    print("网络请求已完成")
                
                # 检查是否有Vega-Lite图表
                has_vega = page.evaluate("""
                    () => {
                        const hasVegaEmbed = typeof vegaEmbed !== 'undefined';
                        const hasVegaEmbedTag = !!document.querySelector('script[src*="vega-embed"]');
                        console.log('Has vegaEmbed global:', hasVegaEmbed);
                        console.log('Has vega-embed script tag:', hasVegaEmbedTag);
                        return hasVegaEmbed || hasVegaEmbedTag;
                    }
                """)
                
                if has_vega:
                    if debug:
                        print("发现Vega-Lite图表")
                    
                    # 等待Vega-Lite加载完成
                    page.wait_for_function("""
                        () => typeof vegaEmbed !== 'undefined'
                    """, timeout=30000)
                    
                    # 等待图表容器
                    try:
                        page.wait_for_selector('.vega-embed', state="attached", timeout=10000)
                        if debug:
                            print("找到Vega-Lite图表容器")
                    except Exception as e:
                        if debug:
                            print(f"等待Vega-Lite图表容器失败: {e}")
                    
                    # 添加帮助脚本来检查和强制渲染图表
                    page.add_script_tag(content="""
                    window.checkVegaRenderStatus = function() {
                        const containers = document.querySelectorAll('.vega-embed');
                        console.log('Found ' + containers.length + ' Vega-Lite containers');
                        
                        let allRendered = true;
                        let details = [];
                        
                        containers.forEach((container, i) => {
                            const hasCanvas = !!container.querySelector('canvas');
                            const hasMarks = !!container.querySelector('.marks');
                            const hasSVG = !!container.querySelector('svg');
                            
                            details.push({
                                id: container.id || `container-${i}`,
                                hasCanvas,
                                hasMarks,
                                hasSVG
                            });
                            
                            if (!(hasCanvas || hasMarks || hasSVG)) {
                                allRendered = false;
                            }
                        });
                        
                        return {
                            allRendered,
                            details,
                            count: containers.length
                        };
                    };
                    
                    // 强制触发所有图表重新渲染
                    window.forceRenderCharts = function() {
                        console.log("强制触发所有图表重新渲染");
                        if (window.chartInstances) {
                            Object.values(window.chartInstances).forEach(function(chart) {
                                if (chart && chart.view) {
                                    try {
                                        chart.view.resize().run();
                                        console.log("重新渲染图表:", chart.el.id);
                                    } catch(e) {
                                        console.error("重新渲染图表失败:", e);
                                    }
                                }
                            });
                        }
                        
                        // 对于可能未包含在chartInstances中的图表，尝试重新调用vegaEmbed
                        document.querySelectorAll('.vega-embed').forEach((container, i) => {
                            const chartId = container.id || `vega-embed-${i}`;
                            const chartDiv = container.querySelector('.chart-container') || container;
                            
                            if (!container.querySelector('canvas')) {
                                console.log(`容器 ${chartId} 没有canvas，尝试触发重新渲染`);
                                // 触发resize事件可能会帮助某些图表重新渲染
                                const event = new Event('resize');
                                window.dispatchEvent(event);
                            }
                        });
                        
                        return "已尝试重新渲染所有图表";
                    };
                    """)
                    
                    # 等待一段时间让图表初始渲染
                    page.wait_for_timeout(3000)
                    
                    # 检查渲染状态
                    render_status = page.evaluate("window.checkVegaRenderStatus()")
                    
                    if debug:
                        print(f"图表渲染状态: {render_status}")
                        if render_status.get('allRendered', False):
                            print("所有图表已渲染")
                        else:
                            print(f"部分图表未渲染，发现{render_status.get('count', 0)}个容器")
                            for detail in render_status.get('details', []):
                                print(f"  容器 {detail.get('id')}: canvas={detail.get('hasCanvas')}, marks={detail.get('hasMarks')}, svg={detail.get('hasSVG')}")
                    
                    # 强制触发图表重新渲染
                    force_render_result = page.evaluate("window.forceRenderCharts()")
                    if debug:
                        print(f"强制渲染结果: {force_render_result}")
                    
                    # 等待更长时间确保渲染完成
                    page.wait_for_timeout(8000)  # 增加到8秒
                    
                    # 再次检查渲染状态
                    render_status_after = page.evaluate("window.checkVegaRenderStatus()")
                    if debug:
                        print(f"强制渲染后状态: {render_status_after}")
                    
                    # 如果仍有图表未渲染，再次尝试强制渲染
                    if not render_status_after.get('allRendered', False):
                        if debug:
                            print("再次尝试强制渲染...")
                        page.evaluate("window.forceRenderCharts()")
                        page.wait_for_timeout(5000)
                
                # 等待图片元素（如果有的话）
                try:
                    has_images = page.evaluate("!!document.querySelector('img')")
                    if has_images:
                        if debug:
                            print("页面包含图片元素，等待图片加载")
                        page.wait_for_selector("img", state="visible", timeout=30000)
                except Exception as e:
                    if debug:
                        print(f"等待图片元素时出错: {e}")
                
                # 最后的等待，确保所有渲染都完成
                page.wait_for_timeout(5000)
                if debug:
                    print("最终等待完成，准备截图")
                
                # 获取页面实际高度并设置视口
                height = page.evaluate("document.documentElement.scrollHeight")
                page.set_viewport_size({"width": 1600, "height": height})
                
                # 截图
                page.screenshot(path=output_path, full_page=True)
                if debug:
                    print(f"截图完成: {output_path}")
                    
                return output_path
                    
            except Exception as e:
                print(f"截图过程中出错: {e}")
                import traceback
                traceback.print_exc()
                return None
            finally:
                browser.close()
    except Exception as e:
        print(f"启动服务器时出错: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # 关闭HTTP服务器
        if httpd:
            try:
                httpd.shutdown()
                httpd.server_close()
                if debug:
                    print("HTTP服务器已关闭")
            except:
                pass

def test_html_to_image():
    """测试函数：测试将HTML文件转换为图片"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试HTML转图片功能')
    parser.add_argument('--html', type=str, required=True, help='HTML文件路径')
    parser.add_argument('--out', type=str, help='输出图片路径')
    parser.add_argument('--debug', action='store_true', help='打印调试信息')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.html):
        print(f"错误: 指定的HTML文件不存在: {args.html}")
        return
    
    print(f"开始转换HTML文件: {args.html}")
    output_path = convert_html_file_to_image(args.html, args.out, debug=args.debug)
    print(f"转换完成! 图片保存在: {output_path}")
    
    # 尝试自动打开图片
    try:
        import platform
        import subprocess
        
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.call(['open', output_path])
        elif system == 'Windows':
            subprocess.call(['start', output_path], shell=True)
        elif system == 'Linux':
            subprocess.call(['xdg-open', output_path])
    except Exception as e:
        print(f"无法自动打开图片: {e}")

if __name__ == "__main__":
    test_html_to_image() 