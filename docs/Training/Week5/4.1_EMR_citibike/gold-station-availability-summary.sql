-- CREATE OR REPLACE VIEW gold.station_availability_summary AS
-- SELECT
--     snapshot_timestamp,
--     COUNT(*) AS operational_stations,
--     SUM(bikes_available) AS bikes_available,
--     SUM(docks_available) AS docks_available,
--     SUM(CASE WHEN is_empty THEN 1 ELSE 0 END) AS empty_stations,
--     SUM(CASE WHEN is_full THEN 1 ELSE 0 END) AS full_stations
-- FROM public.citibike_station_snapshot
-- WHERE is_operational = TRUE
-- GROUP BY snapshot_timestamp;

-- creates the schema
-- performs gold aggregate transformations

-- Current silver:
-- station_id | snapshot_timestamp | station_name | bikes_available | ebikes_available | docks_available | capacity | utilization_pct | is_empty | is_full | is_operational
-- 0b613329-b8c8-4b8c-ad40-79952aa41157 | 2026-10-09 02:41:15 | 1 Ave & E 110 St | 17 | 10 | 1 | 25 | 68 | false | false | true

    -- "station_id",
    -- "snapshot_timestamp",
    -- "station_name",
    -- "bikes_available",
    -- "ebikes_available",
    -- "docks_available",
    -- "capacity",
    -- "utilization_pct",
    -- "is_empty",
    -- "is_full",
    -- "is_operational",

-- Star
    -- Dim:
        -- dim_date:
            -- "date_id",
            -- "year",
            -- "month",
            -- "day",
            -- "day_of_week"

        -- dim_station: These describe the station, where fact expresses the condition of the station at a particular moment
            -- "station_id",
            -- "station_name",
            -- "capacity"


    -- Fact:
        -- fact_station_snapshot
            -- "station_id",
            -- "snapshot_ts_id",
            -- "bikes_available",
            -- "ebikes_available",
            -- "docks_available",
            -- "utilization_pct",
            -- "is_empty",
            -- "is_full",
            -- "is_operational"

CREATE TABLE gold.dim_date(
    date_id INTEGER PRIMARY KEY,
    calendar_date DATE NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    --  Sunday = 0 through Saturday = 6.    
    day_of_week INTEGER NOT NULL,
    hour_of_day INTEGER NOT NULL
);
INSERT INTO gold.dim_date (
    date_id,
    calendar_date,
    year,
    month,
    day,
    day_of_week,
    hour_of_day
)
WITH localized AS (
    SELECT
        CONVERT_TIMEZONE(
            'UTC',
            'America/New_York',
            snapshot_timestamp
        ) AS local_timestamp
    FROM public.citibike_station_snapshot
    WHERE snapshot_timestamp IS NOT NULL
)
SELECT DISTINCT
    CAST(TO_CHAR(local_timestamp, 'YYYYMMDDHH24') AS INTEGER),
    CAST(local_timestamp AS DATE),
    EXTRACT(YEAR FROM local_timestamp),
    EXTRACT(MONTH FROM local_timestamp),
    EXTRACT(DAY FROM local_timestamp),
    EXTRACT(DOW FROM local_timestamp),
    EXTRACT(HOUR FROM local_timestamp)
FROM localized;


-- if a single station updates, this wont work, but we are assuming it stays as is
CREATE TABLE gold.dim_station(
    station_id VARCHAR(50) PRIMARY KEY,
    station_name TEXT NOT NULL,
    capacity INTEGER NOT NULL
);
INSERT INTO gold.dim_station (
    station_id,
    station_name,
    capacity
)
SELECT DISTINCT
    station_id,
    station_name,
    CAST(capacity AS INTEGER) AS capacity
FROM public.citibike_station_snapshot;



CREATE TABLE gold.fact_station_snapshot (
    station_id VARCHAR(50),
    snapshot_timestamp TIMESTAMP NOT NULL,
    date_id INTEGER NOT NULL REFERENCES gold.dim_date(date_id),
    bikes_available INTEGER NOT NULL,
    ebikes_available INTEGER NOT NULL,
    docks_available INTEGER NOT NULL,
    utilization_pct DECIMAL(10,2),
    is_empty BOOLEAN NOT NULL,
    is_full BOOLEAN NOT NULL,
    is_operational BOOLEAN NOT NULL,
    PRIMARY KEY (station_id, snapshot_timestamp)
);
INSERT INTO gold.fact_station_snapshot (
    station_id,
    snapshot_timestamp,
    date_id,
    bikes_available,
    ebikes_available,
    docks_available,
    utilization_pct,
    is_empty,
    is_full,
    is_operational
)
SELECT
    station_id,
    snapshot_timestamp,
    CAST(TO_CHAR(CONVERT_TIMEZONE('UTC', 'America/New_York', snapshot_timestamp), 'YYYYMMDDHH24') AS INTEGER) AS date_id,
    bikes_available,
    ebikes_available,
    docks_available,
    utilization_pct,
    is_empty,
    is_full,
    is_operational
FROM public.citibike_station_snapshot;


-- check joins:
SELECT
    s.station_name,
    d.calendar_date,
    d.hour_of_day,
    f.bikes_available,
    f.utilization_pct
FROM gold.fact_station_snapshot AS f
JOIN gold.dim_station AS s
    ON f.station_id = s.station_id
JOIN gold.dim_date AS d
    ON f.date_id = d.date_id
LIMIT 10;