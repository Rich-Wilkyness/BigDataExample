-- Read-only Redshift checks. Compare counts with the actual published Silver.
SELECT COUNT(*) AS rows, MIN(snapshot_timestamp) AS first_snapshot,
       MAX(snapshot_timestamp) AS last_snapshot
FROM citibike_v2_lab.station_snapshot;

SELECT station_id, snapshot_timestamp, COUNT(*) AS occurrences
FROM citibike_v2_lab.station_snapshot
GROUP BY station_id, snapshot_timestamp HAVING COUNT(*) > 1;

SELECT COUNT(*) AS invalid_keys FROM citibike_v2_lab.station_snapshot
WHERE station_id IS NULL OR station_id = '' OR snapshot_timestamp IS NULL;

SELECT batch_id, COUNT(*) AS unaccepted_landing_rows
FROM citibike_v2_lab.station_snapshot_landing GROUP BY batch_id;

SELECT * FROM citibike_v2_lab.accepted_batch ORDER BY accepted_at_utc DESC;
SELECT * FROM citibike_v2_lab.station_availability_summary
ORDER BY snapshot_timestamp DESC LIMIT 20;

-- Check operational rows against the sum reported by the Gold view.
SELECT (SELECT COUNT(*) FROM citibike_v2_lab.station_snapshot
        WHERE is_operational = TRUE) AS detail_operational_rows,
       (SELECT SUM(operational_stations)
        FROM citibike_v2_lab.station_availability_summary) AS gold_station_rows;
