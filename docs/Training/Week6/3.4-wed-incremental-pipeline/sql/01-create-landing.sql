-- Run in Richard's Redshift warehouse, database dev.
-- Types and column order follow the learner-supplied existing table schema.
-- Landing permits replayed observations; later acceptance must deduplicate them.
CREATE TABLE public.richard_citibike_station_snapshot_landing (
    station_id VARCHAR(65535),
    snapshot_timestamp TIMESTAMP,
    station_name VARCHAR(65535),
    bikes_available BIGINT,
    ebikes_available BIGINT,
    docks_available BIGINT,
    capacity BIGINT,
    utilization_pct DOUBLE PRECISION,
    is_empty BOOLEAN,
    is_full BOOLEAN,
    is_operational BOOLEAN,
    batch_id VARCHAR(64) NOT NULL
);

-- Before loading, expect zero rows in this new table.
SELECT COUNT(*) AS landing_rows
FROM public.richard_citibike_station_snapshot_landing;
