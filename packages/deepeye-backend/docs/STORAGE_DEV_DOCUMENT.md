# 文件存储系统开发指南

本文档详细介绍了 `deepeye-core` 提供的通用文件存储系统。该系统采用了策略模式设计，旨在为上层应用提供统一、安全且灵活的文件存取能力，同时支持云端分布式部署和本地单机运行两种场景。

## 1. 系统架构

存储系统由以下核心组件构成：

*   **`StorageBackend` (Interface)**: 定义了所有存储后端必须实现的统一接口（如 `upload_file`, `download_file`, `list_objects` 等）。上层业务逻辑应只依赖于此接口，而不依赖具体实现。
*   **`StorageFactory`**: 工厂模块，负责根据配置信息（Config）自动实例化正确的存储后端。
*   **具体实现**:
    *   **`MinioBackend`**: 基于 Minio/S3 协议的远程存储实现。支持 IAM 策略生成，适用于多租户 Web 服务。
    *   **`LocalBackend`**: 基于本地文件系统的实现。将“Bucket”映射为文件夹，内置路径遍历防护，适用于 SDK 和本地开发。

## 2. 两种运行模式

### 2.1 远程模式 (Remote/Minio)
*   **适用场景**: 生产环境、Web 后端、多用户协作。
*   **核心特性**:
    *   **数据隔离**: 通过 IAM Policy (`starts-with` 前缀) 强制隔离不同用户的数据。
    *   **高性能**: 支持客户端直传 (Presigned Post Policy)，文件流不经过后端服务器，减轻后端压力。
    *   **依赖**: 需要 Minio 或兼容 S3 的对象存储服务。

### 2.2 本地模式 (Local)
*   **适用场景**: 本地开发、SDK 单机运行、测试环境。
*   **核心特性**:
    *   **零依赖**: 无需 Docker 或外部服务，开箱即用。
    *   **Workspace**: 所有文件操作被严格限制在指定的 `workspace` 目录下，防止误删系统文件。
    *   **简单直观**: 用户可以直接通过操作系统文件管理器查看和管理数据。

## 3. 如何接入与使用

### 3.1 初始化存储后端

推荐使用工厂函数 `get_storage_backend` 进行初始化。这使得切换存储模式仅需修改配置，无需改动代码。

**在 `app/dependencies.py` 或 Service 层中：**

```python
from app.config import settings
from deepeye.storage.factory import get_storage_backend

# 1. 构造配置字典 (通常来自环境变量)
# 生产环境示例 (Minio)
storage_config = {
    "type": "minio",
    "endpoint": settings.MINIO_ENDPOINT,   # e.g., "localhost:9000"
    "access_key": settings.MINIO_ACCESS_KEY,
    "secret_key": settings.MINIO_SECRET_KEY,
    "secure": settings.MINIO_SECURE        # True/False
}

# 或者 本地开发示例 (Local)
# storage_config = {
#     "type": "local",
#     "root_directory": "./workspace"      # 文件存储根目录
# }

# 2. 获取后端实例
# storage_backend 的类型为 StorageBackend 接口
storage_backend = get_storage_backend(storage_config)
```

### 3.2 常用操作示例

一旦获取了 `storage_backend` 实例，所有操作都是统一的：

```python
# 创建 Bucket (Minio: 真实Bucket, Local: 子目录)
storage_backend.create_bucket("user-data", exist_ok=True)

# 上传文件 (服务端中转模式)
# 注意：在 Web 场景下推荐使用 IAM 直传 (见下文)，此方法多用于系统内部文件生成
with open("report.pdf", "rb") as f:
    storage_backend.upload_file(
        bucket_name="user-data",
        object_name="reports/2023_Q1.pdf",
        data=f,
        length=os.path.getsize("report.pdf")
    )

# 下载文件
stream = storage_backend.download_file("user-data", "reports/2023_Q1.pdf")
content = stream.read()
```

## 4. Web 端集成指南 (IAM 直传)

在 Web 应用中，为了性能和安全性，**强烈推荐**使用“客户端直传”模式，而不是将文件流发给后端。

### 4.1 流程图
`前端 -> 后端 (获取上传策略) -> 直接上传到 Minio -> 后端 (确认上传完成)`

### 4.2 后端接口实现

后端需要提供一个接口，用于生成带有安全限制的上传策略。

```python
# app/services/storage_service.py

async def create_upload_policy(self, user_id: str, filename: str):
    # 1. 定义用户专属前缀 (User Isolation)
    object_prefix = f"{user_id}/"
    
    # 2. 调用 Core 功能生成策略
    # 注意：LocalBackend 不支持此功能，调用会抛出 NotImplementedError
    policy = self.backend.generate_upload_policy(
        bucket_name=settings.MINIO_BUCKET,
        object_prefix=object_prefix,
        expires=timedelta(minutes=15)
    )
    
    return {
        "upload_url": policy.url,
        "form_fields": policy.fields,
        # 前端上传时必须使用此 key，否则会被 Minio 拒绝
        "destination_key": f"{object_prefix}{filename}"
    }
```

### 4.3 前端交互逻辑

前端拿到策略后，需要构造 `FormData` 并 POST 给 Minio。

**关键点**：
1.  **字段顺序**：`file` 字段必须是 `FormData` 的**最后一个**字段。
2.  **Key 的一致性**：`key` 字段的值必须与后端返回的 `destination_key` 完全一致（包含 `user_id/` 前缀），否则会报 `403 Forbidden`。

```javascript
const formData = new FormData();
// 添加所有 policy 字段
for (const [k, v] of Object.entries(policy.form_fields)) {
    formData.append(k, v);
}
// 显式添加 key
formData.append('key', policy.destination_key);
// 最后添加文件
formData.append('file', fileObject);

await fetch(policy.upload_url, { method: 'POST', body: formData });
```

## 5. 参考资料与示例

我们在 `packages/deepeye-core/examples/` 下提供了两个完整的可运行示例，强烈建议开发者阅读和运行：

*   **`storage_minio_usage.py`**:
    *   演示 Minio 后端的配置和使用。
    *   **重点演示了 IAM 安全策略**：包含多用户隔离测试（Alice 无法上传文件到 Bob 的目录）。
    *   运行：`python examples/storage_minio_usage.py --setup` 然后 `python examples/storage_minio_usage.py --iam-upload`

*   **`storage_local_usage.py`**:
    *   演示本地后端的配置和使用。
    *   展示了文件如何在 `workspace` 目录下组织。
    *   运行：`python examples/storage_local_usage.py --setup` 然后 `python examples/storage_local_usage.py --upload`
