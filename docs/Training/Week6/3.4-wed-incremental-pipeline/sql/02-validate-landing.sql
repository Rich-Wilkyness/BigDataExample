-- Run in Richard's warehouse, database dev, after the first landing load.
-- Change the batch ID deliberately when validating later batches.
SELECT
    batch_id,
    COUNT(*) AS landing_rows,
    COUNT(DISTINCT station_id) AS stations,
    MIN(snapshot_timestamp) AS earliest_capture,
    MAX(snapshot_timestamp) AS latest_capture,
    SUM(CASE WHEN station_id IS NULL OR TRIM(station_id) = ''
                  OR snapshot_timestamp IS NULL THEN 1 ELSE 0 END) AS invalid_keys,
    SUM(CASE WHEN bikes_available IS NULL OR bikes_available < 0
                  OR ebikes_available IS NULL OR ebikes_available < 0
                  OR docks_available IS NULL OR docks_available < 0
                  OR capacity IS NULL OR capacity < 0
             THEN 1 ELSE 0 END) AS invalid_measures
FROM public.richard_citibike_station_snapshot_landing
WHERE batch_id = 'manual_20261016T1550_1555_v2'
GROUP BY batch_id;

-- Expect no rows for this first, unrepeated load.
-- Landing can contain replayed copies later; canonical must resolve those.
SELECT station_id, snapshot_timestamp, COUNT(*) AS copies
FROM public.richard_citibike_station_snapshot_landing
WHERE batch_id = 'manual_20261016T1550_1555_v2'
GROUP BY station_id, snapshot_timestamp
HAVING COUNT(*) > 1;
