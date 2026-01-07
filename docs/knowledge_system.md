# Knowledge 系统说明（详细版）

## 作用
Knowledge 系统提供知识库管理、文件解析、检索与聊天注入能力。  
设计目标是：可管理、可检索、可扩展。

## 代码结构

1) 数据模型  
路径：`packages/backend/app/models/knowledge_base.py`  
`packages/backend/app/models/knowledge_base_file.py`  
`packages/backend/app/models/knowledge_base_chunk.py`  

2) 服务层  
路径：`packages/backend/app/services/knowledge_base_service.py`  
- 上传文件 → MinIO  
- 解析文本 → 分片  
- 查询检索（LIKE/pg_trgm）  

3) MinIO 存储  
路径：`packages/backend/app/services/minio_service.py`  
配置：`MINIO_KB_BUCKET`（默认 `deepeye-knowledge`）

4) 异步任务  
路径：`packages/backend/app/tasks/kb_tasks.py`  
- 解析文件、更新状态

5) API  
路径：`packages/backend/app/api/v1/knowledge_bases.py`  
- 知识库 CRUD  
- 上传文件  
- 搜索接口  

6) Agent 入口  
路径：`packages/core/deepeye/agents/knowledge_base_agent.py`  
路径：`packages/backend/app/tools/kb_tools.py`  
- `execute_kb_sql`：执行只读 SQL 检索  

## 核心功能类说明

- `KnowledgeBase` / `KnowledgeBaseFile` / `KnowledgeBaseChunk`  
  - 存储 kb 信息、文件元数据、分片内容  

- `knowledge_base_service.py`  
  - `upload_kb_file_to_storage`：写入 MinIO  
  - `process_kb_file`：解析并分片  
  - `search_kb_chunks`：LIKE + pg_trgm 模糊查询  

- `execute_kb_sql` 工具  
  - 只允许 SELECT  
  - 必须过滤 `:user_id` 与 `:kb_ids`  
  - 限制表名：knowledge_base_*  

## 运行流程（实际链路）

1) 用户上传文件  
`POST /api/v1/knowledge-bases/{id}/files`

2) 文件入库 + 存储到 MinIO  
字段写入 `knowledge_base_files`

3) Celery 异步解析  
`kb_tasks.process_kb_file_task` → `process_kb_file`

4) 生成分片  
写入 `knowledge_base_chunks`

5) 聊天时 @知识库  
Supervisor 触发 `query_knowledge_base`  
KB Agent 调用 `execute_kb_sql` → 返回结果

## 扩展方式

### 示例：升级检索为向量检索

1) 增加向量字段
```sql
ALTER TABLE knowledge_base_chunks ADD COLUMN embedding vector(1536);
```

2) 写入 embedding
在 `process_kb_file` 中生成 embedding 并保存

3) 替换检索逻辑
```sql
SELECT content
FROM knowledge_base_chunks
WHERE kb_id = ANY(:kb_ids)
ORDER BY embedding <-> :query_embedding
LIMIT 5;
```

