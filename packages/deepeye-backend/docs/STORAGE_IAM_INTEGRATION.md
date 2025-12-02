# Minio/S3 IAM 存储集成指南

本文档旨在指导后端开发团队如何集成 `deepeye-core` 中新实现的基于 IAM（身份与访问管理）的文件存储功能。

## 1. 为什么使用 IAM 策略上传？

在旧的实现中，文件上传通常采用“服务端中转”模式：
`前端 -> 后端 API (接收文件流) -> 上传到 Minio`

这种方式存在以下问题：
*   **性能瓶颈**：大文件上传会占用后端服务器的带宽和内存。
*   **单点故障**：上传流量过大可能拖垮 API 服务。

新的实现采用 **“客户端直传 + IAM 策略隔离”** 模式：
`前端 -> 后端 (获取上传策略) -> 直接上传到 Minio`

**安全性保障**：
我们使用 **Presigned POST Policy**（预签名 POST 策略）。后端生成的策略中包含 `starts-with` 条件，强制要求上传的文件名必须以特定的前缀（如 `user_123/`）开头。Minio/S3 会自动拒绝任何不符合该策略的上传请求（例如试图上传到 `admin/` 目录）。

## 2. 核心组件介绍

>注：可参考使用示例： `packages/deepeye-core/examples/storage_minio_usage.py`

在 `deepeye-core` 中，我们提供了以下核心组件：

*   **`MinioBackend`**: 实现了 `StorageBackend` 接口，封装了与 Minio 的交互。
*   **`generate_upload_policy`**: 生成带有安全限制的上传策略。

### 初始化 MinioBackend

建议在 `app/dependencies.py` 或 `app/services/storage_service.py` 中初始化单例：

```python
from app.config import settings
from deepeye.storage.backends.minio_backend import MinioBackend

# 初始化存储后端
storage_backend = MinioBackend(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)
```

## 3. 后端集成步骤

请按照以下步骤修改 `app/services/storage_service.py` 和 `app/api/v1/files.py`。

### 3.1 修改 StorageService

需要在 `StorageService` 中添加生成上传策略的方法。

```python
# app/services/storage_service.py

class StorageService:
    def __init__(self):
        # 假设 storage_backend 已在某处初始化或通过依赖注入传入
        self.backend = storage_backend 

    async def create_upload_policy(self, user_id: str, filename: str, content_type: str = None):
        """
        生成前端直传所需的 IAM 策略。
        """
        # 1. 定义用户专属前缀，实现隔离
        object_prefix = f"{user_id}/"
        
        # 2. 调用 Core 功能生成策略
        policy = self.backend.generate_upload_policy(
            bucket_name=settings.MINIO_BUCKET,
            object_prefix=object_prefix,
            content_type=content_type,
            expires=timedelta(minutes=15) # 策略有效期
        )
        
        # 3. 构造返回给前端的数据
        # 注意：前端需要将 filename 拼接到 key 中
        # key = object_prefix + filename
        return {
            "upload_url": policy.url,
            "form_fields": policy.fields,
            "destination_key": f"{object_prefix}{filename}"
        }
```

### 3.2 修改 API 接口

在 `app/api/v1/files.py` 中，你需要：
1.  保留（或弃用）旧的 `POST /upload` 接口。
2.  新增 `GET /upload/policy` 接口。
3.  新增 `POST /upload/confirm` 接口（可选但推荐）。

#### 新增获取策略接口

```python
# app/api/v1/files.py

@router.get("/upload/policy")
async def get_upload_policy(
    filename: str,
    content_type: str,
    current_user: CurrentUserDep,
):
    """
    获取文件上传策略。
    前端拿到策略后，直接 POST 到 Minio。
    """
    return await storage_service.create_upload_policy(
        user_id=str(current_user.id),
        filename=filename,
        content_type=content_type
    )
```

#### 关于文件元数据同步

由于文件不再经过后端，后端不知道文件何时上传完成。通常有两种方案：

1.  **前端回调 (推荐)**：前端上传 Minio 成功后，立即调用后端 `POST /files/confirm`，告知后端“我上传完了，文件路径是 xxx，大小是 xxx”，后端此时在数据库创建文件记录。
2.  **Minio Webhook**：配置 Minio 在文件上传成功后自动回调后端（配置较复杂，不推荐用于 Demo 阶段）。

### 3.3 前端交互示例

前端收到策略后的上传代码示例（参考 `deepeye-core/examples/storage_minio_usage.py`）：

```javascript
// 1. 获取策略
const policy = await api.get('/files/upload-policy', { params: { filename: 'data.csv' } });

// 2. 构造 FormData
const formData = new FormData();
// 必须将所有 fields 添加进去
for (const [key, value] of Object.entries(policy.form_fields)) {
    formData.append(key, value);
}
// 须手动添加 key 字段（如果 fields 里没有包含完整的 key）
formData.append('key', policy.destination_key); 
// 文件必须是最后一个字段
formData.append('file', fileObject);

// 3. 直传 Minio
await fetch(policy.upload_url, {
    method: 'POST',
    body: formData
});

// 4. 通知后端记录
await api.post('/files/confirm', { ... });
```

## 4. 常见问题排查

*   **`403 Forbidden`**: 通常是因为上传时使用的 `key` 不符合策略中的 `starts-with` 前缀限制。请检查前端构造的 `key` 是否正确包含了 `user_id/` 前缀。
*   **`EntityTooLarge`**: 文件大小超过了 `generate_upload_policy` 中设置的 `max_size`（默认 10MB）。

