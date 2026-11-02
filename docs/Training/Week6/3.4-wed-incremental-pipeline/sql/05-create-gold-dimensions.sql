-- Run in Richard's warehouse, database dev.
-- Intended station grain: one row per station ID, latest accepted attributes.
-- Population/update logic and uniqueness checks remain learner checkpoints.
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE gold.incremental_dim_station (
    station_id VARCHAR(65535) NOT NULL,
    station_name VARCHAR(65535),
    capacity BIGINT
);

-- Intended date grain: one row per UTC capture date represented in Gold.
CREATE TABLE gold.incremental_dim_date (
    snapshot_date DATE NOT NULL,
    calendar_year SMALLINT,
    calendar_month SMALLINT,
    day_of_month SMALLINT
);

SELECT COUNT(*) AS station_dimension_rows
FROM gold.incremental_dim_station;

SELECT COUNT(*) AS date_dimension_rows
FROM gold.incremental_dim_date;
