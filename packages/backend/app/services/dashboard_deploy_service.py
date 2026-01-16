import os
import io
import tarfile
import time
import asyncio
import docker
from typing import Dict, Optional
from app.sandbox.docker_sandbox import DockerSandbox
from app.core.config import settings
from deepeye.utils.logger import logger

class DashboardDeployService:
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to init docker client: {e}")
            self.docker_client = None

    async def deploy(self, task_id: str, local_va_app_path: str) -> Dict:
        """
        部署一个 Dashboard 到独立的容器中
        
        Args:
            task_id: 任务 ID (或 node_id)
            local_va_app_path: 后端本地存有 va_app 源代码的目录
            
        Returns:
            {
                "status": "running",
                "container_name": str,
                "url": str
            }
        """
        if not self.docker_client:
            raise RuntimeError("Docker not available")

        # 1. 构造容器名 - 统一使用 deepeye-nl2dashboard- 前缀
        container_name = f"deepeye-nl2dashboard-{task_id}"
        
        # 自动获取当前容器所在的网络
        network_name = "deepeye_nl2dashboard_default_1"
        try:
            # 获取当前 worker 容器的信息
            import socket
            hostname = socket.gethostname()
            this_container = self.docker_client.containers.get(hostname)
            # 获取它加入的网络，过滤掉默认的 bridge，优先选择业务网络
            networks = this_container.attrs['NetworkSettings']['Networks']
            if networks:
                # 优先选择非 bridge 的网络（即 docker-compose 创建的网络）
                biz_networks = [n for n in networks.keys() if n != "bridge"]
                if biz_networks:
                    network_name = biz_networks[0]
                else:
                    network_name = list(networks.keys())[0]
                print(f"[DEBUG] 自动选择容器网络: {network_name}")
        except Exception as ne:
            print(f"[WARN] 自动检测网络失败，使用默认值: {ne}")

        # 2. 清理同名旧容器
        try:
            old = self.docker_client.containers.get(container_name)
            old.remove(force=True)
        except:
            pass

        # 3. 启动新容器
        # 改进策略：补齐所有可能需要的运行库 (uvicorn, fastapi, pandas, pyecharts)
        # 注意：这些已经在 Dockerfile.sandbox 中安装过了，此处仅做最后的兜底，
        # 如果镜像中已存在，pip install 会立即完成（Already satisfied），不会触发网络下载。
        # 考虑到网络环境不稳定，我们大幅增加超时时间，并优化启动脚本。
        start_cmd = (
            "bash -c '"
            "echo [SYSTEM] Waiting for code upload...; "
            "while [ ! -f /app/app.py ]; do sleep 0.5; done; "
            "echo [SYSTEM] Code detected. Checking environment...; "
            "python3 -m pip install --no-cache-dir uvicorn fastapi pandas pyecharts -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 5 || echo [WARN] Pip check skipped or failed, continuing...; "
            "echo [SYSTEM] Starting Uvicorn...; "
            "cd /app && "
            "export PYTHONPATH=$PYTHONPATH:/app && "
            "python3 -m uvicorn app:app --host 0.0.0.0 --port 8000"
            "'"
        )

        container = self.docker_client.containers.run(
            image=settings.SANDBOX_IMAGE,
            name=container_name,
            detach=True,
            working_dir="/app",
            command=start_cmd,
            labels={"type": "dashboard-instance", "task_id": task_id},
            network=network_name
        )

        try:
            # 4. 准备代码包并上传
            print(f"[*] 正在上传 Dashboard 代码到容器 {container_name}...")
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                for item in os.listdir(local_va_app_path):
                    item_path = os.path.join(local_va_app_path, item)
                    tar.add(item_path, arcname=item)
            
            tar_stream.seek(0)
            container.put_archive("/app", tar_stream)
            print(f"[✓] 代码上传完成。")

            # 等待一小会儿，确保容器状态稳定
            await asyncio.sleep(1)
            container.reload()
            if container.status != "running":
                print(f"[ERROR] 容器在上传代码后停止了。状态: {container.status}")
                print(f"容器日志: {container.logs().decode('utf-8')}")
                raise RuntimeError(f"Container stopped after upload: {container.status}")

            # 新增：打印容器内文件结构，核对 app.py 和 public 目录位置
            print(f"[*] 检查容器内部文件结构...")
            ls_res = container.exec_run("ls -R /app")
            if ls_res.exit_code == 0:
                print("\n--- 容器 /app 目录树 ---")
                print(ls_res.output.decode('utf-8'))
                print("-----------------------\n")

            # 7. 返回访问 URL
            dashboard_url = f"/dashboards/{container_name}/"

            # 6. 等待服务就绪 (考虑到环境配置可能存在的延迟，维持 40 秒，但由于镜像已内置库，通常 5-10 秒即可)
            print(f"[*] 正在确认 Dashboard 端口状态...")
            is_ready = False
            for i in range(60):
                container.reload()
                if container.status != "running":
                    print(f"[ERROR] 容器意外停止，状态: {container.status}")
                    break

                # 使用 python 在容器内部探测 8000 端口
                check_cmd = "python3 -c 'import socket; s = socket.socket(); s.settimeout(0.5); s.connect((\"127.0.0.1\", 8000))'"
                res = container.exec_run(check_cmd)
                if res.exit_code == 0:
                    print(f"[✓] Dashboard 端口已就绪: {dashboard_url}")
                    is_ready = True
                    break
                
                # 每 5 秒打印一次进度日志到后台，防止以为卡死了
                if i % 5 == 0 and i > 0:
                    print(f"[*] 还在努力配置中... ({i}s/40s)")
                    
                await asyncio.sleep(1)
            
            if not is_ready:
                print(f"[ERROR] 部署超时。")
                print("\n" + "="*20 + " 容器实时日志 (排查重点) " + "="*20)
                print(container.logs().decode('utf-8'))
                print("="*54 + "\n")
            
            return {
                "status": "running" if is_ready else "error", 
                "container_name": container_name,
                "url": dashboard_url
            }

        except Exception as e:
            print(f"[ERROR] Deployment failed for {task_id}: {e}")
            # if 'container' in locals():
            #     container.remove(force=True)
            raise e

# 单例
dashboard_deployer = DashboardDeployService()
