# DeepEye Open Source Remediation Checklist

状态: In Progress

目标: 把当前仓库收敛为一套可公开发布、可持续维护、默认更安全的数据智能体系统。

## P0 Security And Release Blockers

- [x] 建立整改清单并固定优先级、验收标准、执行顺序
- [ ] 收紧动态代码执行边界
  - 范围: `report`, `dashboard`, `video`, 前端模板执行链路
  - 验收: 用户输入和模型输出不能直接在 API 进程或浏览器上下文中无约束执行
- [ ] 去掉后端对宿主 Docker socket 的直接依赖，或将其隔离到受限执行层
  - 验收: API/worker 不再天然具备宿主级容器控制权
- [x] 收敛工作流主真相，废弃旧 `Workflow`/`/workflows` 旁路
  - 验收: 对外只保留 `session -> turn -> draft -> run -> artifact` 模型
- [x] 建立数据库迁移体系，移除运行时 `create_all()` 作为正式升级路径
  - 验收: schema 变更可迁移、可回滚、可升级
- [x] 让默认测试基线可稳定通过
  - 验收: `pytest` 默认执行通过；需要 Docker 的测试改为显式集成测试

## P1 Architecture And Maintainability

- [x] 清理半成品/未接通模块
  - 已移除未被消费的 `workflow_templates` 前后端接口与 schema
  - 后续候选: 重复的 report 执行辅助、无实际消费的旧事件旁路
  - 验收: 模块要么有真实入口和测试，要么删除
- [ ] 统一 artifact 消费协议
  - 验收: 前端优先使用 `artifact.kind` 与持久化 workspace state，不再依赖 `dashboard_url exists`、`file_path` 等启发式
- [ ] 拆分超大文件
  - 候选: `workflow_tools.py`, `video/config/generator.py`, `dashboard_engineer.py`
  - 验收: 单文件职责聚焦，关键逻辑可单测
- [ ] 把“手工状态拼装”从 chat/workflow/tracking 各层进一步收口
  - 验收: turn/run 状态迁移有单一入口
- [x] 建立 CI
  - 验收: 至少自动跑 `pytest` 和针对改动范围的 lint/check

## P2 Open Source Packaging

- [x] 补齐根 README、backend README、frontend README、core README
  - 验收: 新用户能按文档跑起来并理解系统边界
- [x] 清理发布元数据
  - 验收: 去掉占位作者、模板文案、错误示例
- [ ] 区分开发配置与生产配置
  - 验收: `.env.example` 能表达安全默认值与必要开关
- [x] 补开源运行/安全说明
  - 验收: 明确哪些能力需要 Docker/MinIO/Postgres/Redis，哪些属于高权限执行

## Execution Order

1. 质量基线: 测试基础设施、红测修复、Docker 测试隔离
2. 发布面清理: README、元数据、无用模块与模板残留
3. 架构收敛: 统一工作流主模型，压缩 legacy 路径
4. 执行安全: 动态执行与 Docker 控制面隔离
5. 迁移与 CI: schema migration、自动化检查、发布流程

## Current Iteration

- [x] 保存整改清单
- [x] 修复测试基础设施与当前失败用例
- [x] 清理发布元数据与明显模板残留
- [x] 移除未接通的 `workflow_templates` 冗余能力面
- [x] 收紧 dashboard/video 预览面的默认浏览器与 CORS 暴露面
- [x] 移除工作区到 legacy `Workflow` 的上传桥，并隐藏侧边栏旧入口
- [x] 下线公开 `/workflows` 入口，收敛到 session-scoped workspace 与单一会话事件流
- [x] 增加一键本地质量检查入口、Compose 配置校验和 CodeQL 工作流
- [x] 补充安全模型、quickstart、artifact 协议 RFC、重构路线和发布流程文档
