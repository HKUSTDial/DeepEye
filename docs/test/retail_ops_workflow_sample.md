# Retail Ops Workflow Test Sample

## Scenario
你是一家连锁零售品牌的区域经营负责人。你已经拿到两类异构数据：

1. 一份 CSV：`retail_city_targets_q4_2025.csv`
   - 记录每个城市的 Q4 收入目标、营销预算、活动主题和负责人
2. 一个 PostgreSQL 数据库：`retail_ops`
   - 记录 Q4 每天每家门店的销售、折扣、退款和会员订单数据

目标是让 DeepEye 自动编排一条异构工作流：
- `datasource.read` 读取 CSV
- `sql.execute` 聚合数据库销售数据
- `python.code` 做跨源合并与指标派生
- 最终输出 `Dashboard`、`Report`、`Video`

## Files
- CSV: [data/retail_city_targets_q4_2025.csv](/home/liboyan/project/DeepEye/docs/test/data/retail_city_targets_q4_2025.csv)
- Expected summary: [data/expected_summary.json](/home/liboyan/project/DeepEye/docs/test/data/expected_summary.json)
- DB init SQL: [docker/test-db/retail_ops_init.sql](/home/liboyan/project/DeepEye/docker/test-db/retail_ops_init.sql)

## Docker Compose DB Service
建议使用 `retail-ops-db` 这个 compose 服务。

连接串：
```text
postgresql://retail_ops:deepeye_retail_ops_password@retail-ops-db:5432/retail_ops
```

## Recommended SQL Shape
建议 LLM 在 `sql.execute` 中先聚合到城市粒度，再把结果交给 `python.code` 与 CSV 融合：

```sql
SELECT
  s.city AS city,
  SUM(ds.net_revenue) AS total_revenue,
  SUM(ds.orders_count) AS total_orders,
  SUM(ds.member_orders) AS member_orders,
  SUM(ds.discount_amount) AS total_discount,
  SUM(ds.refund_amount) AS total_refund
FROM daily_store_sales ds
JOIN stores s ON ds.store_id = s.store_id
WHERE ds.sales_date BETWEEN DATE '2025-10-01' AND DATE '2025-12-31'
GROUP BY s.city
ORDER BY total_revenue DESC;
```

## Why `python.code` Is Needed
CSV 里有数据库没有的经营字段：
- `quarter_target_revenue`
- `marketing_budget`
- `focus_campaign`
- `strategic_tier`
- `regional_owner`

因此需要 `python.code` 做跨源合并，并派生：
- `achievement_rate`
- `revenue_gap`
- `budget_roi`
- `member_penetration`
- `priority_label`

## Manual Test Steps
1. 启动 compose 服务，确保 `retail-ops-db` 已就绪。
2. 前端上传 CSV 文件：[data/retail_city_targets_q4_2025.csv](/home/liboyan/project/DeepEye/docs/test/data/retail_city_targets_q4_2025.csv)
3. 前端添加数据库数据源，连接到 `retail-ops-db`
4. 依次测试以下 3 个用户请求

## Prompt 1: Dashboard
```text
我刚上传了一份 2025Q4 城市经营目标与营销预算表，也连接了门店销售数据库。请基于这些数据整理一份城市经营分析数据集，生成一个 dashboard，让我能看到城市排名、目标完成情况和预算效率等业务洞察信息。
```

## Prompt 2: Report
```text
我刚上传了一份 2025Q4 城市经营目标与营销预算表，也连接了门店销售数据库。请基于这些数据生成一份专业的英文经营分析报告。
```

## Prompt 3: Video
```text
我刚上传了一份 2025Q4 城市经营目标与营销预算表，也连接了门店销售数据库。请基于这些数据做一个英文数据洞察视频。
```

## Expected Business Conclusions
基于当前样例数据，稳定应当得到这些核心事实：

- Q4 总营收最高的城市：`Hangzhou`
- 总营收：`794673.36`
- 第二名：`Shenzhen`，总营收 ` 736325.78`
- 第三名：`Shanghai`，总营收 ` 705395.86`

更细的经营判断：
- 目标达成率最高城市：`Shenzhen`
- 预算 ROI 最高城市：`Hangzhou`
- 明显低于目标的城市：Shanghai, Beijing, Chengdu

## Suggested Workflow Shape
```text
read_targets_csv(datasource.read)
  -> aggregate_sales(sql.execute)
  -> merge_and_score(python.code)
  -> dashboard/report/video artifact node
```

## Notes For Review
- 如果 workflow 没有使用 `python.code`，大概率没有真正完成跨源融合
- 如果 artifact 节点缺少 `dataset_ref`，说明 DAG 没连通
- 如果 `python.code` 只输出文本而不是表格 JSON / dataset_ref，下游 artifact 会失败
