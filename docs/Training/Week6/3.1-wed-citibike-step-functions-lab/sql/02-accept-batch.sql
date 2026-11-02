-- Lab reconstruction: atomic acceptance of ONE loaded incremental batch.
-- SECURITY INVOKER means the caller needs permissions on the underlying tables.
-- No COMMIT/TRUNCATE inside: a failure must roll back merge and acceptance together.
CREATE OR REPLACE PROCEDURE citibike_v2_lab.sp_accept_batch(
    p_batch_id VARCHAR(64), p_start_at VARCHAR(20), p_end_before VARCHAR(20)
)
AS $$
DECLARE
    v_start TIMESTAMP;
    v_end TIMESTAMP;
    v_rows BIGINT;
    v_bad BIGINT;
BEGIN
    IF p_batch_id IS NULL OR p_start_at IS NULL OR p_end_before IS NULL THEN
        RAISE EXCEPTION 'Batch and interval must be supplied';
    END IF;
    v_start := CAST(p_start_at AS TIMESTAMP);
    v_end := CAST(p_end_before AS TIMESTAMP);
    IF v_end <= v_start THEN
        RAISE EXCEPTION 'End must be after start';
    END IF;

    -- One acceptance transaction at a time; Glue/S3 still require one active writer.
    LOCK TABLE citibike_v2_lab.accepted_batch;
    LOCK TABLE citibike_v2_lab.station_snapshot;
    LOCK TABLE citibike_v2_lab.station_snapshot_landing;
    IF EXISTS (SELECT 1 FROM citibike_v2_lab.accepted_batch
               WHERE batch_id = p_batch_id) THEN
        IF EXISTS (SELECT 1 FROM citibike_v2_lab.accepted_batch
                   WHERE batch_id = p_batch_id
                     AND (start_at_utc <> v_start OR end_before_utc <> v_end)) THEN
            RAISE EXCEPTION 'Batch ID was already accepted with a different interval';
        END IF;
        -- A loader replay may append duplicate landing rows after acceptance.
        DELETE FROM citibike_v2_lab.station_snapshot_landing
        WHERE batch_id = p_batch_id;
        RETURN;
    END IF;

    CREATE TEMP TABLE pending_citibike_batch AS
    SELECT DISTINCT station_id, snapshot_timestamp, station_name,
           bikes_available, ebikes_available, docks_available, capacity,
           utilization_pct, is_empty, is_full, is_operational
    FROM citibike_v2_lab.station_snapshot_landing
    WHERE batch_id = p_batch_id;

    SELECT COUNT(*) INTO v_rows FROM pending_citibike_batch;
    IF v_rows = 0 THEN
        RAISE EXCEPTION 'No landing rows for the requested batch';
    END IF;
    SELECT COUNT(*) INTO v_bad
    FROM pending_citibike_batch
    WHERE station_id IS NULL OR station_id = '' OR snapshot_timestamp IS NULL
       OR snapshot_timestamp < v_start OR snapshot_timestamp >= v_end
       OR bikes_available < 0 OR docks_available < 0 OR capacity < 0;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'Invalid keys, interval, or counts in landing batch';
    END IF;
    SELECT COUNT(*) INTO v_bad FROM (
        SELECT station_id, snapshot_timestamp
        FROM pending_citibike_batch
        GROUP BY station_id, snapshot_timestamp HAVING COUNT(*) > 1
    ) conflicts;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'Conflicting values for the same station snapshot';
    END IF;

    -- Exact duplicate landing rows were removed by DISTINCT. Conflicts fail above.
    -- All eleven source columns are in the same order as the target table.
    MERGE INTO citibike_v2_lab.station_snapshot
    USING pending_citibike_batch AS incoming
    ON station_snapshot.station_id = incoming.station_id
       AND station_snapshot.snapshot_timestamp = incoming.snapshot_timestamp
    REMOVE DUPLICATES;

    SELECT COUNT(*) INTO v_bad FROM (
        SELECT station_id, snapshot_timestamp
        FROM citibike_v2_lab.station_snapshot
        GROUP BY station_id, snapshot_timestamp HAVING COUNT(*) > 1
    ) duplicate_keys;
    IF v_bad > 0 THEN
        RAISE EXCEPTION 'Accepted detail contains duplicate station snapshot keys';
    END IF;

    -- The Gold view reads this table automatically. A physical Gold model would
    -- need its own reviewed refresh before this acceptance marker is inserted.
    INSERT INTO citibike_v2_lab.accepted_batch
        (batch_id, start_at_utc, end_before_utc, station_rows)
    VALUES (p_batch_id, v_start, v_end, v_rows);
    DELETE FROM citibike_v2_lab.station_snapshot_landing
    WHERE batch_id = p_batch_id;
    DROP TABLE pending_citibike_batch;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;
