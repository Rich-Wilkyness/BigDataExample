-- Richard follow-along reconstruction, not the instructor's recovered SQL.
-- Run in Richard's dev database. These are new lab objects, not replacements
-- for public.citibike_station_snapshot or the existing gold star schema.
CREATE SCHEMA IF NOT EXISTS citibike_v2_lab;

-- Column order matches the eleven-column Glue backfill/load contract.
CREATE TABLE IF NOT EXISTS citibike_v2_lab.station_snapshot (
    station_id VARCHAR(256) NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,
    station_name VARCHAR(1024),
    bikes_available INTEGER,
    ebikes_available INTEGER,
    docks_available INTEGER,
    capacity INTEGER,
    utilization_pct DOUBLE PRECISION,
    is_empty BOOLEAN,
    is_full BOOLEAN,
    is_operational BOOLEAN
);

CREATE TABLE IF NOT EXISTS citibike_v2_lab.station_snapshot_landing (
    station_id VARCHAR(256) NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,
    station_name VARCHAR(1024),
    bikes_available INTEGER,
    ebikes_available INTEGER,
    docks_available INTEGER,
    capacity INTEGER,
    utilization_pct DOUBLE PRECISION,
    is_empty BOOLEAN,
    is_full BOOLEAN,
    is_operational BOOLEAN,
    batch_id VARCHAR(64)
);
-- IF NOT EXISTS does not repair the columns of an existing incompatible table.

CREATE TABLE IF NOT EXISTS citibike_v2_lab.accepted_batch (
    batch_id VARCHAR(64) NOT NULL,
    start_at_utc TIMESTAMP NOT NULL,
    end_before_utc TIMESTAMP NOT NULL,
    station_rows BIGINT NOT NULL,
    accepted_at_utc TIMESTAMP NOT NULL DEFAULT GETDATE()
);

-- Ordinary view: reads accepted detail data; it stores no refreshable rows.
-- This minimal Gold example is separate from the learner-owned star schema.
CREATE OR REPLACE VIEW citibike_v2_lab.station_availability_summary AS
SELECT snapshot_timestamp,
       COUNT(*) AS operational_stations,
       SUM(bikes_available) AS bikes_available,
       SUM(docks_available) AS docks_available,
       SUM(CASE WHEN is_empty THEN 1 ELSE 0 END) AS empty_stations,
       SUM(CASE WHEN is_full THEN 1 ELSE 0 END) AS full_stations
FROM citibike_v2_lab.station_snapshot
WHERE is_operational = TRUE
GROUP BY snapshot_timestamp;

-- Inspect BEFORE the one-time historical append loader. Expected: zero rows.
SELECT COUNT(*) AS historical_destination_rows
FROM citibike_v2_lab.station_snapshot;
