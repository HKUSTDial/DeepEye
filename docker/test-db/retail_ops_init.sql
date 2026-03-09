BEGIN;

DROP TABLE IF EXISTS store_daily_ops CASCADE;
DROP TABLE IF EXISTS stores CASCADE;

CREATE TABLE stores (
  store_id INTEGER PRIMARY KEY,
  city VARCHAR(40) NOT NULL,
  store_code VARCHAR(20) UNIQUE NOT NULL,
  store_name VARCHAR(120) NOT NULL,
  store_format VARCHAR(20) NOT NULL,
  store_weight NUMERIC(6,4) NOT NULL
);

CREATE TABLE store_daily_ops (
  ops_date DATE NOT NULL,
  store_id INTEGER NOT NULL REFERENCES stores(store_id),
  orders INTEGER NOT NULL,
  revenue NUMERIC(12,2) NOT NULL,
  new_members INTEGER NOT NULL,
  repeated_orders INTEGER NOT NULL,
  stockout_orders INTEGER NOT NULL,
  bad_reviews INTEGER NOT NULL,
  delivery_orders INTEGER NOT NULL,
  PRIMARY KEY (ops_date, store_id)
);

CREATE INDEX idx_stores_city ON stores(city);
CREATE INDEX idx_store_daily_ops_date ON store_daily_ops(ops_date);
CREATE INDEX idx_store_daily_ops_store_id ON store_daily_ops(store_id);

INSERT INTO stores (store_id, city, store_code, store_name, store_format, store_weight) VALUES
(1, 'Zurich', 'ZRH-01', 'Zurich Central Station', 'flagship', 1.22),
(2, 'Zurich', 'ZRH-02', 'Zurich Financial District', 'business', 1.12),
(3, 'Zurich', 'ZRH-03', 'Zurich University Quarter', 'campus', 1.02),
(4, 'Zurich', 'ZRH-04', 'Zurich Old Town', 'heritage', 0.96),
(5, 'Zurich', 'ZRH-05', 'Zurich Riverside', 'neighborhood', 0.88),
(6, 'Zurich', 'ZRH-06', 'Zurich West Mall', 'mall', 0.80),
(7, 'Amsterdam', 'AMS-01', 'Amsterdam Zuid', 'flagship', 1.22),
(8, 'Amsterdam', 'AMS-02', 'Amsterdam Central', 'commute', 1.12),
(9, 'Amsterdam', 'AMS-03', 'Amsterdam Science Park', 'campus', 1.02),
(10, 'Amsterdam', 'AMS-04', 'Amsterdam Canal Belt', 'heritage', 0.96),
(11, 'Amsterdam', 'AMS-05', 'Amsterdam East', 'neighborhood', 0.88),
(12, 'Amsterdam', 'AMS-06', 'Amsterdam Arena District', 'mall', 0.80),
(13, 'London', 'LON-01', 'London City', 'flagship', 1.22),
(14, 'London', 'LON-02', 'London Canary Wharf', 'business', 1.12),
(15, 'London', 'LON-03', 'London King''s Cross', 'commute', 1.02),
(16, 'London', 'LON-04', 'London Covent Garden', 'heritage', 0.96),
(17, 'London', 'LON-05', 'London South Bank', 'neighborhood', 0.88),
(18, 'London', 'LON-06', 'London Stratford', 'mall', 0.80),
(19, 'Geneva', 'GVA-01', 'Geneva Cornavin', 'flagship', 1.22),
(20, 'Geneva', 'GVA-02', 'Geneva Banking District', 'business', 1.12),
(21, 'Geneva', 'GVA-03', 'Geneva Old Town', 'heritage', 1.02),
(22, 'Geneva', 'GVA-04', 'Geneva Lakeside', 'premium', 0.96),
(23, 'Geneva', 'GVA-05', 'Geneva Nations', 'office', 0.88),
(24, 'Geneva', 'GVA-06', 'Geneva Plainpalais', 'neighborhood', 0.80),
(25, 'Paris', 'PAR-01', 'Paris Opera', 'flagship', 1.22),
(26, 'Paris', 'PAR-02', 'Paris La Defense', 'business', 1.12),
(27, 'Paris', 'PAR-03', 'Paris Latin Quarter', 'campus', 1.02),
(28, 'Paris', 'PAR-04', 'Paris Le Marais', 'heritage', 0.96),
(29, 'Paris', 'PAR-05', 'Paris Rive Gauche', 'neighborhood', 0.88),
(30, 'Paris', 'PAR-06', 'Paris Les Halles', 'mall', 0.80),
(31, 'Milan', 'MIL-01', 'Milan Centrale', 'flagship', 1.22),
(32, 'Milan', 'MIL-02', 'Milan Porta Nuova', 'business', 1.12),
(33, 'Milan', 'MIL-03', 'Milan Bocconi', 'campus', 1.02),
(34, 'Milan', 'MIL-04', 'Milan Brera', 'heritage', 0.96),
(35, 'Milan', 'MIL-05', 'Milan Navigli', 'neighborhood', 0.88),
(36, 'Milan', 'MIL-06', 'Milan CityLife', 'mall', 0.80);

WITH city_week_targets AS (
  SELECT *
  FROM (
    VALUES
      ('Zurich', DATE '2025-11-03', 142000.00, 5200, 620, 0.5600, 0.0700, 0.0220, 0.3500),
      ('Zurich', DATE '2025-11-10', 148000.00, 5400, 650, 0.5700, 0.0800, 0.0210, 0.3600),
      ('Zurich', DATE '2025-11-17', 151000.00, 5480, 680, 0.5700, 0.0800, 0.0230, 0.3700),
      ('Zurich', DATE '2025-11-24', 157000.00, 5660, 710, 0.5800, 0.0900, 0.0220, 0.3600),
      ('Zurich', DATE '2025-12-01', 160000.00, 5790, 750, 0.5800, 0.0900, 0.0240, 0.3800),
      ('Zurich', DATE '2025-12-08', 166000.00, 5940, 780, 0.5900, 0.1000, 0.0250, 0.3900),
      ('Zurich', DATE '2025-12-15', 171000.00, 6120, 800, 0.6000, 0.1100, 0.0240, 0.4000),
      ('Zurich', DATE '2025-12-22', 176000.00, 6280, 830, 0.6000, 0.1200, 0.0250, 0.4100),
      ('Amsterdam', DATE '2025-11-03', 118000.00, 5100, 780, 0.4700, 0.0400, 0.0200, 0.4200),
      ('Amsterdam', DATE '2025-11-10', 125000.00, 5300, 860, 0.4800, 0.0400, 0.0210, 0.4300),
      ('Amsterdam', DATE '2025-11-17', 133000.00, 5550, 920, 0.4900, 0.0500, 0.0200, 0.4400),
      ('Amsterdam', DATE '2025-11-24', 141000.00, 5840, 980, 0.5000, 0.0500, 0.0210, 0.4500),
      ('Amsterdam', DATE '2025-12-01', 148000.00, 6050, 1040, 0.5200, 0.0500, 0.0220, 0.4600),
      ('Amsterdam', DATE '2025-12-08', 156000.00, 6330, 1100, 0.5300, 0.0600, 0.0220, 0.4700),
      ('Amsterdam', DATE '2025-12-15', 166000.00, 6680, 1180, 0.5500, 0.0600, 0.0210, 0.4700),
      ('Amsterdam', DATE '2025-12-22', 175000.00, 7020, 1260, 0.5600, 0.0600, 0.0210, 0.4800),
      ('London', DATE '2025-11-03', 126000.00, 5000, 650, 0.4200, 0.0300, 0.0320, 0.6300),
      ('London', DATE '2025-11-10', 129000.00, 5080, 690, 0.4200, 0.0400, 0.0340, 0.6400),
      ('London', DATE '2025-11-17', 131000.00, 5150, 720, 0.4300, 0.0400, 0.0350, 0.6500),
      ('London', DATE '2025-11-24', 133000.00, 5220, 740, 0.4300, 0.0400, 0.0370, 0.6600),
      ('London', DATE '2025-12-01', 136000.00, 5300, 770, 0.4400, 0.0500, 0.0390, 0.6700),
      ('London', DATE '2025-12-08', 138000.00, 5380, 790, 0.4400, 0.0500, 0.0410, 0.6800),
      ('London', DATE '2025-12-15', 141000.00, 5460, 810, 0.4500, 0.0500, 0.0430, 0.6900),
      ('London', DATE '2025-12-22', 145000.00, 5560, 840, 0.4600, 0.0500, 0.0460, 0.7100),
      ('Geneva', DATE '2025-11-03', 112000.00, 5100, 590, 0.5500, 0.0200, 0.0170, 0.3800),
      ('Geneva', DATE '2025-11-10', 116000.00, 5210, 620, 0.5500, 0.0200, 0.0180, 0.3900),
      ('Geneva', DATE '2025-11-17', 119000.00, 5310, 640, 0.5600, 0.0200, 0.0170, 0.3900),
      ('Geneva', DATE '2025-11-24', 123000.00, 5420, 660, 0.5600, 0.0300, 0.0180, 0.4000),
      ('Geneva', DATE '2025-12-01', 126000.00, 5510, 690, 0.5600, 0.0300, 0.0190, 0.4100),
      ('Geneva', DATE '2025-12-08', 130000.00, 5630, 710, 0.5700, 0.0300, 0.0190, 0.4100),
      ('Geneva', DATE '2025-12-15', 134000.00, 5750, 740, 0.5700, 0.0300, 0.0200, 0.4200),
      ('Geneva', DATE '2025-12-22', 138000.00, 5870, 760, 0.5800, 0.0300, 0.0200, 0.4200),
      ('Paris', DATE '2025-11-03', 130000.00, 4300, 480, 0.5000, 0.0300, 0.0190, 0.3400),
      ('Paris', DATE '2025-11-10', 131000.00, 4320, 500, 0.5000, 0.0300, 0.0190, 0.3400),
      ('Paris', DATE '2025-11-17', 132000.00, 4340, 520, 0.5100, 0.0300, 0.0200, 0.3500),
      ('Paris', DATE '2025-11-24', 133000.00, 4370, 540, 0.5100, 0.0400, 0.0210, 0.3500),
      ('Paris', DATE '2025-12-01', 134000.00, 4390, 560, 0.5200, 0.0400, 0.0210, 0.3600),
      ('Paris', DATE '2025-12-08', 136000.00, 4420, 580, 0.5200, 0.0400, 0.0220, 0.3600),
      ('Paris', DATE '2025-12-15', 137000.00, 4450, 600, 0.5300, 0.0400, 0.0220, 0.3700),
      ('Paris', DATE '2025-12-22', 139000.00, 4480, 620, 0.5300, 0.0500, 0.0230, 0.3700),
      ('Milan', DATE '2025-11-03', 104000.00, 4900, 430, 0.6000, 0.0200, 0.0130, 0.2800),
      ('Milan', DATE '2025-11-10', 107000.00, 4990, 450, 0.6000, 0.0200, 0.0140, 0.2900),
      ('Milan', DATE '2025-11-17', 109000.00, 5050, 470, 0.6100, 0.0300, 0.0140, 0.2900),
      ('Milan', DATE '2025-11-24', 112000.00, 5140, 490, 0.6100, 0.0300, 0.0150, 0.3000),
      ('Milan', DATE '2025-12-01', 115000.00, 5230, 510, 0.6200, 0.0300, 0.0150, 0.3000),
      ('Milan', DATE '2025-12-08', 118000.00, 5320, 530, 0.6200, 0.0300, 0.0160, 0.3100),
      ('Milan', DATE '2025-12-15', 121000.00, 5410, 550, 0.6300, 0.0400, 0.0170, 0.3100),
      ('Milan', DATE '2025-12-22', 124000.00, 5520, 580, 0.6400, 0.0400, 0.0180, 0.3200)
  ) AS t (
    city,
    week_start,
    total_revenue,
    total_orders,
    total_new_members,
    repeat_rate,
    stockout_rate,
    bad_review_rate,
    delivery_share
  )
),
day_profile AS (
  SELECT *
  FROM (
    VALUES
      (1, 0.90, 0.98),
      (2, 0.94, 0.99),
      (3, 0.97, 1.00),
      (4, 1.00, 1.00),
      (5, 1.08, 1.02),
      (6, 1.15, 1.05),
      (7, 0.96, 1.01)
  ) AS d (iso_dow, day_weight, ticket_weight)
),
weekly_targets AS (
  SELECT
    city,
    week_start,
    CAST(ROUND(total_revenue * 100) AS BIGINT) AS total_revenue_cents,
    total_orders,
    total_new_members,
    CAST(ROUND(total_orders * repeat_rate) AS INTEGER) AS total_repeated_orders,
    CAST(ROUND(total_orders * stockout_rate) AS INTEGER) AS total_stockout_orders,
    CAST(ROUND(total_orders * bad_review_rate) AS INTEGER) AS total_bad_reviews,
    CAST(ROUND(total_orders * delivery_share) AS INTEGER) AS total_delivery_orders
  FROM city_week_targets
),
base_rows AS (
  SELECT
    wt.city,
    wt.week_start,
    gs.ops_date::date AS ops_date,
    s.store_id,
    s.store_weight,
    dp.day_weight,
    dp.ticket_weight,
    (s.store_weight * dp.day_weight) AS volume_weight,
    (s.store_weight * dp.day_weight * dp.ticket_weight) AS revenue_weight
  FROM weekly_targets wt
  JOIN stores s ON s.city = wt.city
  CROSS JOIN LATERAL generate_series(
    wt.week_start,
    wt.week_start + INTERVAL '6 day',
    INTERVAL '1 day'
  ) AS gs(ops_date)
  JOIN day_profile dp ON dp.iso_dow = EXTRACT(ISODOW FROM gs.ops_date)::INTEGER
),
weighted_rows AS (
  SELECT
    br.*,
    wt.total_revenue_cents,
    wt.total_orders,
    wt.total_new_members,
    wt.total_repeated_orders,
    wt.total_stockout_orders,
    wt.total_bad_reviews,
    wt.total_delivery_orders,
    SUM(br.volume_weight) OVER (PARTITION BY br.city, br.week_start) AS total_volume_weight,
    SUM(br.revenue_weight) OVER (PARTITION BY br.city, br.week_start) AS total_revenue_weight
  FROM base_rows br
  JOIN weekly_targets wt USING (city, week_start)
),
allocations AS (
  SELECT
    wr.*,
    FLOOR(wr.total_orders * wr.volume_weight / wr.total_volume_weight)::INTEGER AS orders_base,
    (wr.total_orders * wr.volume_weight / wr.total_volume_weight)
      - FLOOR(wr.total_orders * wr.volume_weight / wr.total_volume_weight) AS orders_frac,
    FLOOR(wr.total_new_members * wr.volume_weight / wr.total_volume_weight)::INTEGER AS members_base,
    (wr.total_new_members * wr.volume_weight / wr.total_volume_weight)
      - FLOOR(wr.total_new_members * wr.volume_weight / wr.total_volume_weight) AS members_frac,
    FLOOR(wr.total_repeated_orders * wr.volume_weight / wr.total_volume_weight)::INTEGER AS repeated_base,
    (wr.total_repeated_orders * wr.volume_weight / wr.total_volume_weight)
      - FLOOR(wr.total_repeated_orders * wr.volume_weight / wr.total_volume_weight) AS repeated_frac,
    FLOOR(wr.total_stockout_orders * wr.volume_weight / wr.total_volume_weight)::INTEGER AS stockout_base,
    (wr.total_stockout_orders * wr.volume_weight / wr.total_volume_weight)
      - FLOOR(wr.total_stockout_orders * wr.volume_weight / wr.total_volume_weight) AS stockout_frac,
    FLOOR(wr.total_bad_reviews * wr.volume_weight / wr.total_volume_weight)::INTEGER AS bad_base,
    (wr.total_bad_reviews * wr.volume_weight / wr.total_volume_weight)
      - FLOOR(wr.total_bad_reviews * wr.volume_weight / wr.total_volume_weight) AS bad_frac,
    FLOOR(wr.total_delivery_orders * wr.volume_weight / wr.total_volume_weight)::INTEGER AS delivery_base,
    (wr.total_delivery_orders * wr.volume_weight / wr.total_volume_weight)
      - FLOOR(wr.total_delivery_orders * wr.volume_weight / wr.total_volume_weight) AS delivery_frac,
    FLOOR(wr.total_revenue_cents * wr.revenue_weight / wr.total_revenue_weight)::BIGINT AS revenue_base_cents,
    (wr.total_revenue_cents * wr.revenue_weight / wr.total_revenue_weight)
      - FLOOR(wr.total_revenue_cents * wr.revenue_weight / wr.total_revenue_weight) AS revenue_frac
  FROM weighted_rows wr
),
remainders AS (
  SELECT
    a.*,
    a.total_orders - SUM(a.orders_base) OVER (PARTITION BY a.city, a.week_start) AS orders_remainder,
    a.total_new_members - SUM(a.members_base) OVER (PARTITION BY a.city, a.week_start) AS members_remainder,
    a.total_repeated_orders - SUM(a.repeated_base) OVER (PARTITION BY a.city, a.week_start) AS repeated_remainder,
    a.total_stockout_orders - SUM(a.stockout_base) OVER (PARTITION BY a.city, a.week_start) AS stockout_remainder,
    a.total_bad_reviews - SUM(a.bad_base) OVER (PARTITION BY a.city, a.week_start) AS bad_remainder,
    a.total_delivery_orders - SUM(a.delivery_base) OVER (PARTITION BY a.city, a.week_start) AS delivery_remainder,
    a.total_revenue_cents - SUM(a.revenue_base_cents) OVER (PARTITION BY a.city, a.week_start) AS revenue_remainder
  FROM allocations a
),
ranked AS (
  SELECT
    r.*,
    ROW_NUMBER() OVER (PARTITION BY r.city, r.week_start ORDER BY r.orders_frac DESC, r.ops_date, r.store_id) AS orders_rank,
    ROW_NUMBER() OVER (PARTITION BY r.city, r.week_start ORDER BY r.members_frac DESC, r.ops_date, r.store_id) AS members_rank,
    ROW_NUMBER() OVER (PARTITION BY r.city, r.week_start ORDER BY r.repeated_frac DESC, r.ops_date, r.store_id) AS repeated_rank,
    ROW_NUMBER() OVER (PARTITION BY r.city, r.week_start ORDER BY r.stockout_frac DESC, r.ops_date, r.store_id) AS stockout_rank,
    ROW_NUMBER() OVER (PARTITION BY r.city, r.week_start ORDER BY r.bad_frac DESC, r.ops_date, r.store_id) AS bad_rank,
    ROW_NUMBER() OVER (PARTITION BY r.city, r.week_start ORDER BY r.delivery_frac DESC, r.ops_date, r.store_id) AS delivery_rank,
    ROW_NUMBER() OVER (PARTITION BY r.city, r.week_start ORDER BY r.revenue_frac DESC, r.ops_date, r.store_id) AS revenue_rank
  FROM remainders r
)
INSERT INTO store_daily_ops (
  ops_date,
  store_id,
  orders,
  revenue,
  new_members,
  repeated_orders,
  stockout_orders,
  bad_reviews,
  delivery_orders
)
SELECT
  ops_date,
  store_id,
  orders_base + CASE WHEN orders_rank <= orders_remainder THEN 1 ELSE 0 END AS orders,
  ROUND(
    (revenue_base_cents + CASE WHEN revenue_rank <= revenue_remainder THEN 1 ELSE 0 END)::NUMERIC / 100,
    2
  ) AS revenue,
  members_base + CASE WHEN members_rank <= members_remainder THEN 1 ELSE 0 END AS new_members,
  repeated_base + CASE WHEN repeated_rank <= repeated_remainder THEN 1 ELSE 0 END AS repeated_orders,
  stockout_base + CASE WHEN stockout_rank <= stockout_remainder THEN 1 ELSE 0 END AS stockout_orders,
  bad_base + CASE WHEN bad_rank <= bad_remainder THEN 1 ELSE 0 END AS bad_reviews,
  delivery_base + CASE WHEN delivery_rank <= delivery_remainder THEN 1 ELSE 0 END AS delivery_orders
FROM ranked
ORDER BY ops_date, store_id;

COMMIT;
