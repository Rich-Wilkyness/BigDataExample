-- One-time cleanup in Richard's workgroup richard-citibike-wg, database dev.
-- Removes the five explicitly retired tables, including their stored rows.
-- Prerequisites: verify migrated Gold content, inspect procedure/view dependencies,
-- and confirm the Richard workflow and Glue jobs are idle.
-- The older manual richard-citibike-silver-to-redshift job is retired by this cleanup;
-- its saved script still references the removed snapshot/stage tables.
-- Execute this complete transaction, or submit the six inner statements together
-- using Redshift Data API BatchExecuteStatement (which supplies the transaction).
-- RESTRICT prevents removal of any remaining bound dependent objects.
BEGIN;

CREATE OR REPLACE VIEW gold.station_availability_summary AS
SELECT
    snapshot_timestamp,
    COUNT(*) AS operational_stations,
    SUM(bikes_available) AS bikes_available,
    SUM(docks_available) AS docks_available,
    SUM(CASE WHEN is_empty THEN 1 ELSE 0 END) AS empty_stations,
    SUM(CASE WHEN is_full THEN 1 ELSE 0 END) AS full_stations
FROM gold.incremental_fact_station_snapshot
WHERE is_operational = TRUE
GROUP BY snapshot_timestamp;

DROP TABLE public.richard_citibike_fact_station_snapshot_pre_gold_20261017 RESTRICT;
DROP TABLE public.richard_citibike_dim_station_pre_gold_20261017 RESTRICT;
DROP TABLE public.richard_citibike_dim_date_pre_gold_20261017 RESTRICT;
DROP TABLE public.citibike_station_snapshot_stage RESTRICT;
DROP TABLE public.citibike_station_snapshot RESTRICT;

COMMIT;
