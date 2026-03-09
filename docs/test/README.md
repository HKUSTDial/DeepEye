# Test Assets

## 手测场景一：零售城市经营分析（CSV + PostgreSQL）

主文档：[retail_ops_workflow_sample.md](retail_ops_workflow_sample.md)

数据文件：
- [data/retail_city_targets_q4_2025.csv](data/retail_city_targets_q4_2025.csv)
- [data/expected_summary.json](data/expected_summary.json)
- [docker/test-db/retail_ops_init.sql](../../docker/test-db/retail_ops_init.sql)

Docker Compose 服务：`retail-ops-db`

---

## 手测场景二：全球销售效率分析（CSV + PostgreSQL，推荐）

主文档：[global_sales_workflow_sample.md](global_sales_workflow_sample.md)

数据文件：
- [data/sales_with_products.csv](data/sales_with_products.csv) — 2000 条交易流水（产品/地区/利润/成本）
- [docker/test-db/global_ops_init.sql](../../docker/test-db/global_ops_init.sql) — 区域运营月度数据

Docker Compose 服务：`global-ops-db`

连接串：`postgresql://global_ops:deepeye_global_ops_password@global-ops-db:5432/global_ops`

**为什么更好**：CSV 提供交易级销售数据，DB 提供运营成本与客户数据，两者通过 `region` 联结后可派生净利润率、营销 ROI、人均产出等单一数据源无法计算的指标，天然强制 LLM 完成真正的跨源融合。
