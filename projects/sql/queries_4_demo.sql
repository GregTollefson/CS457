-- CS457 / FRED Research Database
-- Read-only SQL queries for the current database and YouTube demonstration.
-- Run against PostgreSQL database fred_db. No data or schema is modified.

-- 1. List current base tables and views
SELECT table_type, table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_type, table_name;

-- 2. Show column definitions and nullability (schema structure)
SELECT table_name, ordinal_position, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('category', 'metric', 'source', 'series', 'observations')
ORDER BY table_name, ordinal_position;

-- 3. Primary keys, foreign keys and unique constraints
SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
       string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) AS columns
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu
  ON tc.constraint_catalog = kcu.constraint_catalog
 AND tc.constraint_schema = kcu.constraint_schema
 AND tc.constraint_name = kcu.constraint_name
 AND tc.table_name = kcu.table_name
WHERE tc.table_schema = 'public'
  AND tc.table_name IN ('category', 'metric', 'source', 'series', 'observations')
  AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE')
GROUP BY tc.table_name, tc.constraint_name, tc.constraint_type
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;

-- 4. Current record counts for each table
SELECT 'category' AS table_name, COUNT(*) AS row_count FROM category
UNION ALL SELECT 'metric', COUNT(*) FROM metric
UNION ALL SELECT 'source', COUNT(*) FROM source
UNION ALL SELECT 'series', COUNT(*) FROM series
UNION ALL SELECT 'observations', COUNT(*) FROM observations;

-- 5. List loaded series and their research classifications
SELECT s.series_id, s.title, c.category_code, m.metric_code, src.source_name
FROM series AS s
JOIN metric AS m ON s.metric_id = m.metric_id
JOIN category AS c ON m.category_id = c.category_id
JOIN source AS src ON s.source_id = src.source_id
ORDER BY c.category_code, m.metric_code, s.series_id;

-- 6. Show data coverage and missing values for each series
SELECT s.series_id, s.title,
       COUNT(o.date) AS observation_rows,
       MIN(o.date) AS first_date,
       MAX(o.date) AS last_date,
       COUNT(*) FILTER (WHERE o.value IS NULL) AS missing_values
FROM series AS s
LEFT JOIN observations AS o ON o.series_id = s.series_id
GROUP BY s.series_id, s.title
ORDER BY s.series_id;

-- 7. Inspect the analysis-ready research view
SELECT *
FROM electricity_research_monthly
ORDER BY date DESC
LIMIT 12;

-- 8. Verify view coverage and completeness
SELECT COUNT(*) AS months,
       MIN(date) AS first_month,
       MAX(date) AS last_month,
       COUNT(*) FILTER (WHERE electricity_price IS NULL) AS missing_electricity_price,
       COUNT(*) FILTER (WHERE utility_capacity IS NULL) AS missing_capacity,
       COUNT(*) FILTER (WHERE capacity_utilization IS NULL) AS missing_utilization,
       COUNT(*) FILTER (WHERE total_power_construction IS NULL) AS missing_total_construction,
       COUNT(*) FILTER (WHERE private_power_construction IS NULL) AS missing_private_construction,
       COUNT(*) FILTER (WHERE public_power_construction IS NULL) AS missing_public_construction,
       COUNT(*) FILTER (WHERE transmission_distribution_activity IS NULL) AS missing_transmission
FROM electricity_research_monthly;

-- 9. Research example: recent price and capacity utilization
SELECT date, electricity_price, capacity_utilization
FROM electricity_research_monthly
WHERE date >= DATE '2020-01-01'
ORDER BY date;

-- 10. Referential integrity check: orphan observations (should return zero)
SELECT COUNT(*) AS orphan_observations
FROM observations AS o
LEFT JOIN series AS s ON s.series_id = o.series_id
WHERE s.series_id IS NULL;

-- 11. Duplicate series/date check (should return no rows)
SELECT series_id, date, COUNT(*) AS copies
FROM observations
GROUP BY series_id, date
HAVING COUNT(*) > 1
ORDER BY copies DESC, series_id, date;

-- 12. Before/after ingestion: natural gas series presence
-- Replace the series ID with whichever natural-gas FRED series you choose.
-- SELECT s.series_id, s.title, COUNT(o.date) AS observation_rows,
--        MIN(o.date) AS first_date, MAX(o.date) AS last_date
-- FROM series AS s
-- LEFT JOIN observations AS o ON o.series_id = s.series_id
-- WHERE s.series_id = 'YOUR_NATURAL_GAS_SERIES_ID'
-- GROUP BY s.series_id, s.title;

-- 13. Before/after ingestion: repeat query 4 and query 6 to show growth,
--     then rerun query 11 to demonstrate no duplicate observations.
