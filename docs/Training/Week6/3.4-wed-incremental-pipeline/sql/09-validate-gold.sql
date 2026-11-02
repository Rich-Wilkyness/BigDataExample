-- Run in Richard's warehouse, database dev.
-- Expected totals apply to the initial single-capture dataset only.
SELECT 'fact_rows' AS check_name, COUNT(*) AS observed
FROM gold.incremental_fact_station_snapshot
UNION ALL
SELECT 'station_rows', COUNT(*) FROM gold.incremental_dim_station
UNION ALL
SELECT 'date_rows', COUNT(*) FROM gold.incremental_dim_date
UNION ALL
SELECT 'duplicate_fact_keys', COUNT(*)
FROM (
    SELECT station_id, snapshot_timestamp
    FROM gold.incremental_fact_station_snapshot
    GROUP BY station_id, snapshot_timestamp
    HAVING COUNT(*) > 1
) AS duplicate_facts
UNION ALL
SELECT 'duplicate_station_keys', COUNT(*)
FROM (
    SELECT station_id
    FROM gold.incremental_dim_station
    GROUP BY station_id
    HAVING COUNT(*) > 1
) AS duplicate_stations
UNION ALL
SELECT 'duplicate_date_keys', COUNT(*)
FROM (
    SELECT snapshot_date
    FROM gold.incremental_dim_date
    GROUP BY snapshot_date
    HAVING COUNT(*) > 1
) AS duplicate_dates
UNION ALL
SELECT 'missing_station_references', COUNT(*)
FROM gold.incremental_fact_station_snapshot AS f
WHERE NOT EXISTS (
    SELECT 1 FROM gold.incremental_dim_station AS s
    WHERE s.station_id = f.station_id
)
UNION ALL
SELECT 'missing_date_references', COUNT(*)
FROM gold.incremental_fact_station_snapshot AS f
WHERE NOT EXISTS (
    SELECT 1 FROM gold.incremental_dim_date AS d
    WHERE d.snapshot_date = f.snapshot_date
)
UNION ALL
SELECT 'invalid_fact_measures', COUNT(*)
FROM gold.incremental_fact_station_snapshot
WHERE bikes_available IS NULL OR bikes_available < 0
   OR ebikes_available IS NULL OR ebikes_available < 0
   OR docks_available IS NULL OR docks_available < 0
   OR capacity_at_capture IS NULL OR capacity_at_capture < 0
   OR (capacity_at_capture > 0 AND utilization_pct IS NULL)
UNION ALL
SELECT 'invalid_station_attributes', COUNT(*)
FROM gold.incremental_dim_station
WHERE station_name IS NULL OR TRIM(station_name) = ''
   OR capacity IS NULL OR capacity < 0
ORDER BY check_name;

-- Expect 2026-10-16, 2026, 10, 16 for the first loaded capture.
SELECT snapshot_date, calendar_year, calendar_month, day_of_month
FROM gold.incremental_dim_date
ORDER BY snapshot_date;
