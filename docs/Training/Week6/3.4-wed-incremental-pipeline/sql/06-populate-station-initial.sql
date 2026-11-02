-- Initial population only: run once against an empty station dimension.
-- This is the corrected query the learner executed; it is not repeat-safe.
-- Latest accepted attributes per station (Type 1); later acceptance must update
-- existing stations and insert new stations rather than append every station.
INSERT INTO gold.incremental_dim_station (
    station_id,
    station_name,
    capacity
)
SELECT
    c.station_id,
    c.station_name,
    c.capacity
FROM public.richard_citibike_station_snapshot_canonical AS c
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY c.station_id
    ORDER BY c.snapshot_timestamp DESC
) = 1;



-- dim_date
INSERT INTO gold.incremental_dim_date (
    snapshot_date,
    calendar_year,
    calendar_month,
    day_of_month
)
SELECT DISTINCT
    CAST(snapshot_timestamp AS DATE),
    EXTRACT(YEAR FROM snapshot_timestamp),
    EXTRACT(MONTH FROM snapshot_timestamp),
    EXTRACT(DAY FROM snapshot_timestamp)
FROM public.richard_citibike_station_snapshot_canonical;