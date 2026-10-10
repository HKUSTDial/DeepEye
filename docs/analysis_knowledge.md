# 互联网分析案例知识库

本功能使用本地关键词／标签检索，把相关案例的口径、前提和排查方法提供给 Supervisor 和 Workflow Planner。目标是帮助形成有依据的分析计划。它不是业务数据仓库，也不自动判定统计结论正确。

## 内容与代码

- `packages/backend/app/knowledge/cards.json`：运行时唯一知识源；当前 7 个企业案例（微软5、Spotify2）、2 个 Amplitude 方法条目，覆盖仍有限。包含条件化指标定义 `metric_definitions` 及 4 个可执行合成 SQL 示例 `examples`。
- `packages/backend/app/knowledge/retrieval.py`：结构校验、中英文检索、上下文预算、来源和版本摘要。
- `packages/backend/app/tasks/analysis_knowledge.py`：沿用现有 `tool_start/tool_end` 发布检索记录，并进入 AssistantMessage 的 steps。
- `packages/backend/app/tasks/agent_tasks.py`：根据当前用户问题检索，把同一份上下文传给 Supervisor 和规划器。
- `scripts/evaluate_analysis_knowledge.py`：可复现的小规模开发诊断，支持可选真实模型方法问答检查。
- `scripts/knowledge_acceptance.py`：三组开发验收，默认不联网；4个方法问题、4个SQL任务。人工选卡组由脚本按预设正确卡模拟，不是额外的人类实验。
- `scripts/knowledge_browser_acceptance.cjs`：真实 Edge 页面验收，使用环境变量提供的隔离测试账号；会创建对话并上传合成CSV。

代码外的 `../data-agent-build-notes/knowledge-drafts/` 保留研究过程，不作为第二份运行时配置。

## 行为

1. 每次请求读取本地知识文件，按 NFKC／大小写归一后的关键词与标签匹配。英文使用词边界，中文按短语匹配；具体短语权重较高，同分按 ID 排序。
2. 最多选择 3 张卡，卡片上下文不超过 12000 字符；只添加完整卡片，不截断来源与方法条件。字符预算不等于精确 token 预算。
3. 匹配仅代表主题相关。字段含义、时间口径、随机化单位等适用条件由 Agent 结合用户输入和 schema 检查；缺少关键条件时提示澄清，不根据字段名擅自确定语义。
4. 通过 `planning_notes` 要求给出卡片 ID、适用或拒绝理由、数据缺口和分析步骤，再解释节点连接；这些仍是模型输出约束，不是确定性方法验证器。
5. “过程”中的 `analysis_knowledge` 记录卡片 ID、标题、命中词、来源、证据状态和目录 SHA-256。它说明检索结果，不声称模型已采用。实际采用理由在工作流工具输入的 `planning_notes` 中审阅。
6. 无匹配、知识文件缺失或格式错误时保留原有工作流路径，并明确没有可用参考；不编造引用。关闭开关则不增加上下文或检索事件。

知识条目只来自本地维护文件，不会在每次分析时自动联网搜文章，也不把用户数据写入知识库。检索日志不记录用户原问题或数据预览。指标定义是有适用条件的知识，不替用户选择业务口径。内嵌示例的 SQLite 方言、字段、时间与去重规则必须重新核对；不得在用户数据库执行其建表脚本，示例输出也不是当前任务结果。

## 使用与开关

`ANALYSIS_KNOWLEDGE_ENABLED=true` 默认开启；关闭时在部署配置中设置为 `false`。

Compose 的环境变量通过 `env_file` 加载，修改 `.env` 后要重新创建服务才能更新环境：

```powershell
docker compose up -d --no-deps backend-api backend-worker
```

单纯更新已挂载的 Python 代码时，API 有 reload；Worker 需在没有运行中任务时重启：

```powershell
docker compose restart backend-worker
```

知识 JSON 每次检索重新加载；不需重启即可读取内容修订。

可试问（不需要上传数据）：

> 只讨论分析方法：某模块点击率下降，但点击次数增加，应该检查什么？请说明所需数据和参考依据。

> 只讨论方法：次日留存怎么算，需要先确认哪些口径？

具体数据分析仍需当前任务的数据源；知识库不提供当前业务事实。

## 验证命令

容器缺少测试工具时可安装仓库已声明的开发依赖；本功能没有增加生产依赖。

```powershell
docker compose exec -T backend-api uv pip install --python /app/.venv/bin/python 'pytest>=9.0.3' 'pytest-asyncio>=0.23.0' 'ruff>=0.15.12'
docker compose exec -T backend-api /app/.venv/bin/python -m pytest packages/backend/app/test/test_analysis_knowledge.py packages/backend/app/test/test_analysis_knowledge_integration.py packages/backend/app/test/test_workflow_prompts.py packages/backend/app/test/test_agent_prompts.py packages/backend/app/test/test_agent_orchestration.py -q
docker compose exec -T backend-api /app/.venv/bin/python /app/project/scripts/evaluate_analysis_knowledge.py --output /app/project/tmp/knowledge-evaluation.json
```

加 `--live` 会发起两次配置模型请求（无知识／有知识各一次），只发送合成的方法问题。输出包括模型、温度、usage、回答、知识版本；不要把单次问答当作统计显著的对比实验。

## 维护与限制

- 新卡需有 HTTPS 来源、精确章节定位、案例／方法类型、数据要求和结论边界；`evidence_status` 区分读过来源与执行过示例。
- 知识卡的修改改变 SHA-256，可追溯当时检索版本；不要把研究草稿与运行时卡分别维护成两套独立知识库。
- 关键词检索不理解否定句，也不能完整处理省略上下文的追问；可能漏检同义表达或召回不适用的案例。
- 2026-09-22 已完成真实 Edge 页面方法问答、合成CSV上传、CTR工作流计算、来源记录与历史恢复；漏斗、留存和分流只做了隔离SQL验证，不混写为全部场景的完整页面验收。
- 真模型仍可能过度推断：首次 smoke 中出现“人群变化必然导致两种 CTR 背离”的错误，已补充卡片边界，但不能以文字约束保证此类错误消失。
- 三组各4条SQL在允许六位小数舍入后全部正确；方法回答仍有过强措辞、来源引用不足。尚无独立盲测、多次配对统计比较或生产业务收益证明，不能写成企业任务成功率或已量化准确率提升。

## 完整验收与演示

```powershell
docker compose exec -T backend-api /app/.venv/bin/python -m pytest packages/backend/app/test/test_analysis_knowledge.py packages/backend/app/test/test_analysis_knowledge_integration.py packages/backend/app/test/test_knowledge_examples.py packages/backend/app/test/test_knowledge_acceptance.py packages/backend/app/test/test_workflow_prompts.py packages/backend/app/test/test_agent_prompts.py packages/backend/app/test/test_agent_orchestration.py -q
docker compose exec -T backend-api /app/.venv/bin/python /app/project/scripts/knowledge_acceptance.py --output /app/project/tmp/knowledge-acceptance.json
```

第二条命令加 `--live` 才会发起至多24次配置模型请求，无自动重试。仅发送合成任务与知识卡；报告逐次落盘，保存模型、温度、输出上限、usage、终止原因、目录版本和题目hash。未完整结束的回答不能判为质量通过。隔离SQLite仅允许只读操作与白名单函数，禁用写入、附加库和任意扩展；结果行数与执行时间有限制。

页面演示可上传 [ctr.csv](knowledge-validation/ctr.csv)，明确每行是用户×period聚合、曝光为正，要求计算总体CTR和平均用户CTR。预期 before 为6/15=0.4与0.4，after为9/45=0.2与0.375。它是验证数据，不是企业业务数据。

自动页面验收要求本机 Node、Playwright 和 Edge，以及专用测试账号。在环境中设置 `KNOWLEDGE_TEST_EMAIL`、`KNOWLEDGE_TEST_PASSWORD` 后执行 `node scripts/knowledge_browser_acceptance.cjs`。可用 `PLAYWRIGHT_MODULE` 指定已有 Playwright 模块路径，用 `KNOWLEDGE_EVIDENCE_DIR` 指定输出目录。脚本固定访问本机 `http://localhost:8080`，中文界面；不会注册账号或发送邮件，也不会读取现有用户浏览器凭据。不要在真实业务账号上运行。

研究与验收说明位于工作区外部的 `../data-agent-build-notes/08-completion-and-acceptance.md`、`09-testing-explained.md`。证据文件保留失败与更正记录；每次修改卡片后重新跑离线检查，并在下次完整页面验收前停止修改被测Python文件，避免开发热重载中断请求。
