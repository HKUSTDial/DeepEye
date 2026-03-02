"""
测试用 API：在不跑真实视频生成的前提下，验证「前端 → nginx → 预览容器」链路是否打通。
"""
from fastapi import APIRouter, HTTPException

from app.services.video_deploy_service import video_deployer

router = APIRouter(prefix="/test", tags=["test"])


@router.post("/start-video-preview")
async def start_video_preview_test():
    """
    启动一个测试用预览容器（固定 task_id 20260302_999999），不消耗任何视频生成额度。
    用于确认：网关能否正确代理到预览容器、前端轮询与 iframe 是否正常。
    返回 task_id 与 url，前端可在 Video Preview 面板粘贴该 task_id 或直接打开 url。
    """
    try:
        result = await video_deployer.start_test_preview()
        return {
            "task_id": result["task_id"],
            "url": result["url"],
            "status": result["status"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start test preview: {e}")
