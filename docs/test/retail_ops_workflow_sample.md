# European Coffee Chain Workflow Demo Sample

## Scenario
You are the regional operations lead for a European coffee chain preparing an end-of-year performance review. You already have two heterogeneous data sources:

1. A CSV file: `coffee_city_campaign_calendar_q4_2025.csv`
   - Weekly campaign planning by city, including hero product, discount mechanic, channel focus, and city owner
2. A PostgreSQL database: `retail_ops`
   - Store-level daily operating facts, which need to be aggregated to city-week level before they can be joined with the CSV

This scenario works well for an international jury because it is immediately understandable:
- Which city is growing fastest
- Which city generates the most revenue
- Which city has a supply risk
- Which city has a fulfillment risk
- Which city is the most balanced operator

The goal is to let DeepEye orchestrate a heterogeneous workflow that:
- Uses `datasource.read` to load the campaign CSV
- Uses `sql.execute` to aggregate store-level daily data into city-week operating data
- Uses `python.code` only to join the two sources
- Produces a `Dashboard`, `Report`, and `Video`

## Why This Demo Fits Geneva Judges
- The business context is universal and does not depend on local Chinese market knowledge.
- The KPIs are simple enough to understand in seconds.
- The workflow still demonstrates real multi-source analysis, not just chart generation.
- The final narrative naturally supports dashboard, report, and video outputs in English.
- The database now contains about `2,016` store-day records, which feels materially closer to a real business dataset than a tiny handcrafted table.

## Files
- CSV: [data/coffee_city_campaign_calendar_q4_2025.csv](/home/liboyan/project/DeepEye/docs/test/data/coffee_city_campaign_calendar_q4_2025.csv)
- Expected summary: [data/coffee_ops_expected_summary.json](/home/liboyan/project/DeepEye/docs/test/data/coffee_ops_expected_summary.json)
- DB init SQL: [docker/test-db/retail_ops_init.sql](/home/liboyan/project/DeepEye/docker/test-db/retail_ops_init.sql)

## Docker Compose DB Service
Use the `retail-ops-db` compose service.

Connection string:
```text
postgresql://retail_ops:deepeye_retail_ops_password@retail-ops-db:5432/retail_ops
```

## Dataset Shape
CSV fields:
- `city`
- `week_start`
- `city_tier`
- `store_count`
- `campaign_name`
- `hero_product`
- `discount_rule`
- `channel_focus`
- `ops_owner`

Database tables:
- `stores`
  - `store_id`
  - `city`
  - `store_code`
  - `store_name`
  - `store_format`
  - `store_weight`
- `store_daily_ops`
  - `ops_date`
  - `store_id`
  - `orders`
  - `revenue`
  - `new_members`
  - `repeated_orders`
  - `stockout_orders`
  - `bad_reviews`
  - `delivery_orders`

## Recommended SQL Shape
Aggregate the daily store-level facts into a `city + week_start` dataset first. That gives the artifact enough trend detail without exposing raw operational noise:

```sql
SELECT
  DATE_TRUNC('week', sdo.ops_date)::date AS week_start,
  s.city,
  SUM(sdo.revenue) AS revenue,
  SUM(sdo.orders) AS orders,
  ROUND(SUM(sdo.revenue) / NULLIF(SUM(sdo.orders), 0), 2) AS avg_ticket,
  SUM(sdo.new_members) AS new_members,
  ROUND(SUM(sdo.repeated_orders)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS repeat_rate,
  ROUND(SUM(sdo.stockout_orders)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS stockout_rate,
  ROUND(SUM(sdo.bad_reviews)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS bad_review_rate,
  ROUND(SUM(sdo.delivery_orders)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS delivery_share
FROM store_daily_ops sdo
JOIN stores s ON sdo.store_id = s.store_id
WHERE sdo.ops_date BETWEEN DATE '2025-11-03' AND DATE '2025-12-28'
GROUP BY 1, 2
ORDER BY week_start, city;
```

## Why `python.code` Is Needed
The CSV contains campaign context that does not exist in the database:
- `campaign_name`
- `hero_product`
- `discount_rule`
- `channel_focus`
- `city_tier`
- `store_count`
- `ops_owner`

`python.code` should therefore:
- Normalize the `week_start` format if needed
- Join the CSV rows and the aggregated SQL result on `city + week_start`
- Output the final analysis-ready dataset for downstream artifact nodes

This sample does not require Python-based KPI calculations. `python.code` should only be responsible for cross-source joining.

## Manual Test Steps
1. Start the compose stack and make sure `retail-ops-db` is healthy.
2. Upload the CSV file [data/coffee_city_campaign_calendar_q4_2025.csv](/home/liboyan/project/DeepEye/docs/test/data/coffee_city_campaign_calendar_q4_2025.csv) in the frontend.
3. Add the PostgreSQL datasource and connect it to `retail-ops-db`.
4. Run the three user requests below.

## Prompt 1: Dashboard
```text
I uploaded a weekly city campaign calendar and connected a store-level daily operations database for our European coffee chain. Aggregate the daily data to city-week level, join the two sources by city and week, then build a dashboard that quickly shows revenue performance, member growth, and operational risks across cities.
```

## Prompt 2: Report
```text
I uploaded a weekly city campaign calendar and connected a store-level daily operations database for our European coffee chain. Aggregate the daily data to city-week level, then create a professional English business review that explains which cities are growing fastest, which cities have supply or fulfillment risks, and what actions leadership should take next.
```

## Prompt 3: Video
```text
I uploaded a weekly city campaign calendar and connected a store-level daily operations database for our European coffee chain. Aggregate the daily data to city-week level and create a 60-second English insight video structured around growth cities, risk cities, and the most balanced city.
```

## Expected Business Conclusions
With the current sample data, the workflow should consistently surface these conclusions after SQL aggregation:

- `Zurich` has the highest total revenue at `1271000`, but also the highest average stockout rate at `9.34%`
- `Amsterdam` is the fastest-growing city and the strongest acquisition city, with `8120` new members and `48.31%` revenue growth versus the first week
- `London` has the highest delivery dependence and the clearest fulfillment risk, with `66.71%` average delivery share and `3.86%` average bad review rate
- `Geneva` is the most balanced city, with `56.29%` repeat rate, `2.64%` stockout rate, and `1.86%` bad review rate
- `Paris` has the highest average ticket at `30.57`, but slower growth than the other major cities
- `Milan` has the strongest loyalty profile, with `61.67%` repeat rate and the lowest bad review rate at `1.53%`

## Suggested Workflow Shape
```text
read_campaign_calendar_csv(datasource.read)
  -> aggregate_store_daily_ops(sql.execute)
  -> join_on_city_and_week(python.code)
  -> dashboard/report/video artifact node
```

## Manual Workflow Builder Recipe

Use this section when you want to build the workflow manually in `/workflows` instead of relying on the agent planner.

Important implementation note:
- In the manual DAG, `datasource.read` and `sql.execute` should run in parallel as two source nodes.
- They should both feed their `dataset_ref` outputs into one `python.code` node.
- `python.code` should output a compact city-level summary table, and `llm.answer` should read that summary table as its grounded input.

Actual graph:

```text
read_campaign_csv(datasource.read) -----------\
                                               -> build_city_summary(python.code) -> answer_exec(llm.answer)
aggregate_city_week(sql.execute) -------------/
```

### Before You Start
1. Upload the CSV file `coffee_city_campaign_calendar_q4_2025.csv` and keep its file datasource id.
2. Create the PostgreSQL datasource for `retail_ops` and keep its database datasource id.
3. Open `/workflows`.
4. Add the four nodes below.

### Node 1: Campaign CSV
- Node id: `read_campaign_csv`
- Node type: `datasource.read`
- Purpose: load the weekly campaign calendar file

Parameters:

```text
datasource_id = {{campaign_csv_datasource_id}}
limit = 60
```

### Node 2: Aggregated SQL
- Node id: `aggregate_city_week`
- Node type: `sql.execute`
- Purpose: aggregate store daily facts to city-week level

Parameters:

```text
datasource_id = {{retail_ops_postgres_datasource_id}}
limit = 80
query =
SELECT
  DATE_TRUNC('week', sdo.ops_date)::date AS week_start,
  s.city,
  SUM(sdo.revenue) AS revenue,
  SUM(sdo.orders) AS orders,
  ROUND(SUM(sdo.revenue) / NULLIF(SUM(sdo.orders), 0), 2) AS avg_ticket,
  SUM(sdo.new_members) AS new_members,
  ROUND(SUM(sdo.repeated_orders)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS repeat_rate,
  ROUND(SUM(sdo.stockout_orders)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS stockout_rate,
  ROUND(SUM(sdo.bad_reviews)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS bad_review_rate,
  ROUND(SUM(sdo.delivery_orders)::numeric / NULLIF(SUM(sdo.orders), 0), 4) AS delivery_share
FROM store_daily_ops sdo
JOIN stores s ON sdo.store_id = s.store_id
WHERE sdo.ops_date BETWEEN DATE '2025-11-03' AND DATE '2025-12-28'
GROUP BY 1, 2
ORDER BY week_start, city;
```

### Node 3: Cross-Source Join And City Summary
- Node id: `build_city_summary`
- Node type: `python.code`
- Purpose:
  - normalize `week_start`
  - join the CSV campaign context with the aggregated SQL data on `city + week_start`
  - roll the joined weekly rows up to a compact city summary table

Why the output should be city-level:
- `llm.answer` works best when the grounded dataset preview contains all important rows.
- A 6-city summary is more stable than a 48-row city-week table for final narrative generation.

Parameters:

```python
data = json.load(sys.stdin)
frames = load_dataset_refs(data)

campaign_df = None
ops_df = None

for df in frames:
    probe = {str(col).strip().lower() for col in df.columns}
    if {"campaign_name", "hero_product", "discount_rule", "channel_focus", "ops_owner"}.issubset(probe):
        campaign_df = df.copy()
    elif {"revenue", "orders", "avg_ticket", "new_members", "repeat_rate", "stockout_rate", "bad_review_rate", "delivery_share"}.issubset(probe):
        ops_df = df.copy()

if campaign_df is None or ops_df is None:
    raise ValueError("Expected one campaign CSV dataset and one aggregated SQL dataset.")

campaign_df.columns = [str(c).strip().lower() for c in campaign_df.columns]
ops_df.columns = [str(c).strip().lower() for c in ops_df.columns]

campaign_df["city"] = campaign_df["city"].astype(str).str.strip()
ops_df["city"] = ops_df["city"].astype(str).str.strip()
campaign_df["week_start"] = pd.to_datetime(campaign_df["week_start"]).dt.strftime("%Y-%m-%d")
ops_df["week_start"] = pd.to_datetime(ops_df["week_start"]).dt.strftime("%Y-%m-%d")

joined = campaign_df.merge(
    ops_df,
    on=["city", "week_start"],
    how="inner",
    validate="one_to_one",
)

if joined.empty:
    raise ValueError("The campaign CSV and SQL result did not join on city + week_start.")

joined = joined.sort_values(["city", "week_start"]).reset_index(drop=True)
first_week_revenue = joined.groupby("city")["revenue"].transform("first")
joined["revenue_growth_vs_first_week"] = (
    (joined["revenue"] / first_week_revenue) - 1
).round(4)

latest_context = (
    joined.sort_values(["city", "week_start"])
    .groupby("city", as_index=False)
    .tail(1)[
        [
            "city",
            "week_start",
            "campaign_name",
            "hero_product",
            "discount_rule",
            "channel_focus",
            "ops_owner",
            "city_tier",
            "store_count",
        ]
    ]
    .rename(
        columns={
            "week_start": "latest_week_start",
            "campaign_name": "latest_campaign_name",
            "hero_product": "latest_hero_product",
            "discount_rule": "latest_discount_rule",
            "channel_focus": "latest_channel_focus",
            "ops_owner": "latest_ops_owner",
        }
    )
)

city_rollup = (
    joined.groupby("city", as_index=False)
    .agg(
        total_revenue=("revenue", "sum"),
        total_orders=("orders", "sum"),
        total_new_members=("new_members", "sum"),
        avg_repeat_rate=("repeat_rate", "mean"),
        avg_stockout_rate=("stockout_rate", "mean"),
        avg_bad_review_rate=("bad_review_rate", "mean"),
        avg_delivery_share=("delivery_share", "mean"),
        revenue_growth_vs_first_week=("revenue_growth_vs_first_week", "last"),
    )
)

city_rollup["avg_ticket"] = (city_rollup["total_revenue"] / city_rollup["total_orders"]).round(2)
city_rollup = city_rollup.merge(latest_context, on="city", how="left")

for col in [
    "avg_repeat_rate",
    "avg_stockout_rate",
    "avg_bad_review_rate",
    "avg_delivery_share",
    "revenue_growth_vs_first_week",
]:
    city_rollup[col] = city_rollup[col].astype(float).round(4)

city_rollup["total_revenue"] = city_rollup["total_revenue"].astype(int)
city_rollup["total_orders"] = city_rollup["total_orders"].astype(int)
city_rollup["total_new_members"] = city_rollup["total_new_members"].astype(int)
city_rollup["store_count"] = city_rollup["store_count"].astype(int)

city_rollup = city_rollup.sort_values("total_revenue", ascending=False).reset_index(drop=True)
emit_dataframe(city_rollup)
```

### Node 4: Final Narrative
- Node id: `answer_exec`
- Node type: `llm.answer`
- Purpose: turn the grounded city summary table into a concise executive answer

Parameters:

```text
question =
Write a concise English executive review for Geneva judges using only the provided city summary table.

Structure:
1. One headline sentence.
2. Three bullets on leaders in revenue, growth, and member acquisition.
3. Two bullets on operational risks, especially stockout and fulfillment risk.
4. One bullet naming the most balanced city.
5. Three concrete next-quarter actions.

Always mention exact city names and numeric evidence from the table when available.
```

### Edge Wiring

Create exactly these three edges:

```text
read_campaign_csv.dataset_ref -> build_city_summary.dataset_ref
aggregate_city_week.dataset_ref -> build_city_summary.dataset_ref
build_city_summary.dataset_ref -> answer_exec.dataset_ref
```

### How To Build It In The UI
1. Add `datasource.read`, `sql.execute`, `python.code`, and `llm.answer`.
2. Rename the nodes to the ids shown above so the graph stays readable.
3. Fill the two datasource ids first.
4. Paste the SQL into `aggregate_city_week.query`.
5. Paste the Python code into `build_city_summary.code`.
6. Paste the narrative instruction into `answer_exec.question`.
7. Draw the three edges exactly as listed above.
8. Save the workflow.
9. Run the workflow.

### Expected Output Shape
- `read_campaign_csv` returns one file `dataset_ref`
- `aggregate_city_week` returns one SQL result `dataset_ref`
- `build_city_summary` returns one city-level summary `dataset_ref` with about 6 rows
- `answer_exec` returns one grounded English answer

### What Good Output Should Mention
The final answer should usually surface most of these:
- Zurich leads total revenue but has the strongest stockout risk
- Amsterdam leads growth and member acquisition
- London has the highest delivery dependence and the clearest fulfillment risk
- Geneva is the most balanced operator
- Paris leads average ticket
- Milan leads loyalty and review quality

### Common Failure Modes
- If `python.code` receives only one input, the cross-source join was not actually wired.
- If `python.code` outputs 40+ rows instead of a compact city summary, `llm.answer` may not see all key cities in preview.
- If the join is empty, the two `week_start` fields were not normalized to the same format.
- If `llm.answer` produces vague text without numbers, the upstream summary table was probably too noisy or too sparse.

## Notes For Review
- If the workflow does not use `python.code`, it probably did not complete a real cross-source merge
- If the workflow skips SQL aggregation and feeds raw daily rows into the artifact, the story becomes noisy and less judge-friendly
- If the final dataset is reduced to a city total only, the dashboard and video lose most of the trend story
- If an artifact node is missing `dataset_ref`, the DAG is not wired correctly
- If `python.code` outputs only prose instead of tabular JSON or `dataset_ref`, downstream artifacts will fail
