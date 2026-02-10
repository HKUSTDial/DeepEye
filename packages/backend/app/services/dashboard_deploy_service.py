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
        Deploy a Dashboard to an independent container.
        
        Args:
            task_id: Task ID (or node_id)
            local_va_app_path: Backend local directory containing va_app source code.
            
        Returns:
            {
                "status": "running",
                "container_name": str,
                "url": str
            }
        """
        if not self.docker_client:
            raise RuntimeError("Docker not available")

        # 1. Construct container name - using deepeye-nl2dashboard- prefix
        container_name = f"deepeye-nl2dashboard-{task_id}"
        
        # Automatically detect the network the current container is in
        network_name = "deepeye_nl2dashboard_default_1"
        try:
            # Get current worker container info
            import socket
            hostname = socket.gethostname()
            this_container = self.docker_client.containers.get(hostname)
            # Get its networks, filter out default 'bridge', prioritize business networks
            networks = this_container.attrs['NetworkSettings']['Networks']
            if networks:
                # Prioritize non-bridge networks (e.g., created by docker-compose)
                biz_networks = [n for n in networks.keys() if n != "bridge"]
                if biz_networks:
                    network_name = biz_networks[0]
                else:
                    network_name = list(networks.keys())[0]
                print(f"[DEBUG] Automatically selected container network: {network_name}")
        except Exception as ne:
            print(f"[WARN] Automatic network detection failed, using default: {ne}")

        # 2. Cleanup old container with the same name
        try:
            old = self.docker_client.containers.get(container_name)
            old.remove(force=True)
        except:
            pass

        # 3. Start new container
        # Strategy: Ensure all required libraries are installed (uvicorn, fastapi, pandas, pyecharts)
        # Note: These are already installed in Dockerfile.sandbox, this is a final fallback.
        # If already present, pip install will finish immediately (Already satisfied).
        # Increased timeout and optimized startup script for unstable network environments.
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
            # 4. Prepare code package and upload
            print(f"[*] Uploading Dashboard code to container {container_name}...")
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                for item in os.listdir(local_va_app_path):
                    item_path = os.path.join(local_va_app_path, item)
                    tar.add(item_path, arcname=item)
            
            tar_stream.seek(0)
            container.put_archive("/app", tar_stream)
            print(f"[✓] Code upload completed.")

            # Wait a moment to ensure container status is stable
            await asyncio.sleep(1)
            container.reload()
            if container.status != "running":
                print(f"[ERROR] Container stopped after upload. Status: {container.status}")
                print(f"Container logs: {container.logs().decode('utf-8')}")
                raise RuntimeError(f"Container stopped after upload: {container.status}")

            # Print container file structure for verification
            print(f"[*] Checking container internal file structure...")
            ls_res = container.exec_run("ls -R /app")
            if ls_res.exit_code == 0:
                print("\n--- Container /app Directory Tree ---")
                print(ls_res.output.decode('utf-8'))
                print("-----------------------\n")

            # 7. Return access URL
            dashboard_url = f"/dashboards/{container_name}/"

            # 6. Wait for service to be ready (timeout 60s)
            print(f"[*] Confirming Dashboard port status...")
            is_ready = False
            for i in range(60):
                container.reload()
                if container.status != "running":
                    print(f"[ERROR] Container stopped unexpectedly, status: {container.status}")
                    break

                # Use python inside container to probe port 8000
                check_cmd = "python3 -c 'import socket; s = socket.socket(); s.settimeout(0.5); s.connect((\"127.0.0.1\", 8000))'"
                res = container.exec_run(check_cmd)
                if res.exit_code == 0:
                    print(f"[✓] Dashboard port is ready: {dashboard_url}")
                    is_ready = True
                    break
                
                # Print progress every 5 seconds
                if i % 5 == 0 and i > 0:
                    print(f"[*] Still configuring... ({i}s/60s)")
                    
                await asyncio.sleep(1)
            
            if not is_ready:
                print(f"[ERROR] Deployment timed out.")
                print("\n" + "="*20 + " Container Real-time Logs " + "="*20)
                print(container.logs().decode('utf-8'))
                print("="*54 + "\n")
            
            return {
                "status": "running" if is_ready else "error", 
                "container_name": container_name,
                "url": dashboard_url
            }

        except Exception as e:
            print(f"[ERROR] Deployment failed for {task_id}: {e}")
            raise e

# Singleton
dashboard_deployer = DashboardDeployService()
