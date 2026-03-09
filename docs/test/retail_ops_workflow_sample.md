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

## Notes For Review
- If the workflow does not use `python.code`, it probably did not complete a real cross-source merge
- If the workflow skips SQL aggregation and feeds raw daily rows into the artifact, the story becomes noisy and less judge-friendly
- If the final dataset is reduced to a city total only, the dashboard and video lose most of the trend story
- If an artifact node is missing `dataset_ref`, the DAG is not wired correctly
- If `python.code` outputs only prose instead of tabular JSON or `dataset_ref`, downstream artifacts will fail
