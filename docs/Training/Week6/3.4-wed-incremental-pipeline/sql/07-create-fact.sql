-- Run in Richard's warehouse, database dev.
-- Fact grain: one station at one UTC capture timestamp.
-- station_id and snapshot_date refer to the station/date dimensions logically.
-- Dimension existence and key uniqueness must be validated during acceptance.
CREATE TABLE gold.incremental_fact_station_snapshot (
    station_id VARCHAR(65535) NOT NULL,
    snapshot_timestamp TIMESTAMP NOT NULL,
    snapshot_date DATE NOT NULL,
    bikes_available BIGINT,
    ebikes_available BIGINT,
    docks_available BIGINT,
    capacity_at_capture BIGINT,
    utilization_pct DOUBLE PRECISION,
    is_empty BOOLEAN,
    is_full BOOLEAN,
    is_operational BOOLEAN,
    batch_id VARCHAR(64) NOT NULL
);

-- Check the actual date-dimension values before populating the fact.
SELECT snapshot_date, calendar_year, calendar_month, day_of_month
FROM gold.incremental_dim_date;

SELECT COUNT(*) AS fact_rows
FROM gold.incremental_fact_station_snapshot;
