-- Developed in the hands-on session; run one acceptance at a time.
-- Sequential replay guard only; this does not lock concurrent writers.
INSERT INTO gold.incremental_fact_station_snapshot (
    station_id, snapshot_timestamp, snapshot_date,
    bikes_available, ebikes_available, docks_available,
    capacity_at_capture, utilization_pct,
    is_empty, is_full, is_operational, batch_id
)
SELECT
    c.station_id, c.snapshot_timestamp, CAST(c.snapshot_timestamp AS DATE),
    c.bikes_available, c.ebikes_available, c.docks_available,
    c.capacity, c.utilization_pct,
    c.is_empty, c.is_full, c.is_operational, c.batch_id
FROM public.richard_citibike_station_snapshot_canonical AS c
WHERE NOT EXISTS (
    SELECT 1
    FROM gold.incremental_fact_station_snapshot AS f
    WHERE f.station_id = c.station_id
      AND f.snapshot_timestamp = c.snapshot_timestamp
);
