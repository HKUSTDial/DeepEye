"""
全局中间件
"""
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from app.core.auth import verify_token
from app.core.config import settings
import uuid
import logging

logger = logging.getLogger(__name__)

# 公开路径前缀（白名单）
PUBLIC_PATH_PREFIXES = [
    "/api/auth/",      # 认证接口
    "/api/public/",    # 公开接口
    "/docs",           # Swagger 文档
    "/redoc",          # ReDoc 文档
    "/openapi.json",   # OpenAPI schema
]

# 精确匹配的公开路径
PUBLIC_EXACT_PATHS = [
    "/",
    "/health",
]
def is_public_path(path: str) -> bool:
    """
    判断是否为公开路径
    
    Args:
        path: 请求路径
        
    Returns:
        True if 公开路径, False otherwise
    """
    # 精确匹配
    if path in PUBLIC_EXACT_PATHS:
        return True
    
    # 前缀匹配
    for prefix in PUBLIC_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    
    return False


def is_stream_path(path: str) -> bool:
    return (
        (path.startswith("/api/v1/chat/") and path.endswith("/stream"))
        or (path.startswith("/api/v1/workflows/runs/") and path.endswith("/stream"))
    )


async def auth_middleware(request: Request, call_next):
    """
    全局鉴权中间件
    
    工作流程：
    1. 检查是否为公开路径（白名单）
    2. 如果是，直接放行
    3. 如果不是，验证 JWT token
    4. 验证成功后，将 user_id 注入到 request.state
    5. 验证失败，返回 401
    
    注入到 request.state 的属性：
    - user_id: UUID - 当前用户 ID
    - username: str - 当前用户名
    """
    path = request.url.path

    # Allow CORS preflight requests through without auth checks.
    if request.method == "OPTIONS":
        return await call_next(request)

    def _with_cors_headers(response: Response) -> Response:
        origin = request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response
    
    # 1. 检查是否为公开路径
    if is_public_path(path):
        logger.debug(f"Public path accessed: {path}")
        return await call_next(request)
    
    # 2. 验证 Authorization header / cookie
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        token_cookie = request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        if token_cookie:
            auth_header = f"Bearer {token_cookie}"
    if (
        not auth_header
        and settings.ALLOW_QUERY_TOKEN_FOR_STREAM
        and is_stream_path(path)
    ):
        # Legacy fallback: EventSource with query token.
        token_param = request.query_params.get("token")
        if token_param:
            auth_header = f"Bearer {token_param}"
    if not auth_header:
        logger.warning(f"Missing Authorization header for {path}")
        return _with_cors_headers(JSONResponse(
            status_code=401,
            content={
                "detail": "Missing authorization header",
                "error_code": "MISSING_AUTH_HEADER"
            }
        ))
    
    if not auth_header.startswith("Bearer "):
        logger.warning(f"Invalid Authorization header format for {path}")
        return _with_cors_headers(JSONResponse(
            status_code=401,
            content={
                "detail": "Invalid authorization header format. Expected: Bearer <token>",
                "error_code": "INVALID_AUTH_FORMAT"
            }
        ))
    
    token = auth_header.split(" ")[1]
    
    # 3. 验证 token 并注入 user_id
    try:
        payload = verify_token(token)
        request.state.user_id = uuid.UUID(payload["user_id"])
        request.state.username = payload.get("username", "")
        logger.debug(f"User {request.state.username} authenticated for {path}")
    except Exception as e:
        logger.warning(f"Token verification failed for {path}: {str(e)}")
        return _with_cors_headers(JSONResponse(
            status_code=401,
            content={
                "detail": "Invalid or expired token",
                "error_code": "INVALID_TOKEN"
            }
        ))
    
    # 4. 继续处理请求
    response = await call_next(request)
    return response
