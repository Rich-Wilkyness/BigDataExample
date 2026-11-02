-- One-time migration for Richard's existing dev database, 2026-10-17.
-- Preflight: owner matches; targets absent; no active workflow or loader;
-- no explicit source grants or bound dependent views were observed.
-- Existing gold.dim_* / gold.fact_* classroom tables remain untouched.
-- Run the WHOLE transaction once, never individual statements.
-- Data API BatchExecuteStatement submits the enclosed statements together
-- without BEGIN/COMMIT because that API supplies the transaction boundary.
-- Original tables are retained as dated backups; do not use them for analytics.
BEGIN;

LOCK TABLE public.richard_citibike_pipeline_checkpoint, public.richard_citibike_accepted_batch, public.richard_citibike_station_snapshot_landing, public.richard_citibike_station_snapshot_canonical, public.richard_citibike_dim_station, public.richard_citibike_dim_date, public.richard_citibike_fact_station_snapshot;

CREATE TABLE gold.incremental_dim_station (LIKE public.richard_citibike_dim_station INCLUDING DEFAULTS);

INSERT INTO gold.incremental_dim_station SELECT * FROM public.richard_citibike_dim_station;

CREATE TABLE gold.incremental_dim_date (LIKE public.richard_citibike_dim_date INCLUDING DEFAULTS);

INSERT INTO gold.incremental_dim_date SELECT * FROM public.richard_citibike_dim_date;

CREATE TABLE gold.incremental_fact_station_snapshot (LIKE public.richard_citibike_fact_station_snapshot INCLUDING DEFAULTS);

INSERT INTO gold.incremental_fact_station_snapshot SELECT * FROM public.richard_citibike_fact_station_snapshot;

CREATE PROCEDURE public.sp_richard_verify_gold_migration_20261017() LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT COUNT(*) FROM gold.incremental_dim_station) <> (SELECT COUNT(*) FROM public.richard_citibike_dim_station) OR EXISTS (SELECT * FROM gold.incremental_dim_station EXCEPT SELECT * FROM public.richard_citibike_dim_station) OR EXISTS (SELECT * FROM public.richard_citibike_dim_station EXCEPT SELECT * FROM gold.incremental_dim_station) THEN
        RAISE EXCEPTION 'Gold migration content mismatch: dim_station';
    END IF;
    IF (SELECT COUNT(*) FROM gold.incremental_dim_date) <> (SELECT COUNT(*) FROM public.richard_citibike_dim_date) OR EXISTS (SELECT * FROM gold.incremental_dim_date EXCEPT SELECT * FROM public.richard_citibike_dim_date) OR EXISTS (SELECT * FROM public.richard_citibike_dim_date EXCEPT SELECT * FROM gold.incremental_dim_date) THEN
        RAISE EXCEPTION 'Gold migration content mismatch: dim_date';
    END IF;
    IF (SELECT COUNT(*) FROM gold.incremental_fact_station_snapshot) <> (SELECT COUNT(*) FROM public.richard_citibike_fact_station_snapshot) OR EXISTS (SELECT * FROM gold.incremental_fact_station_snapshot EXCEPT SELECT * FROM public.richard_citibike_fact_station_snapshot) OR EXISTS (SELECT * FROM public.richard_citibike_fact_station_snapshot EXCEPT SELECT * FROM gold.incremental_fact_station_snapshot) THEN
        RAISE EXCEPTION 'Gold migration content mismatch: fact_station_snapshot';
    END IF;
END;
$$;

CALL public.sp_richard_verify_gold_migration_20261017();

DROP PROCEDURE public.sp_richard_verify_gold_migration_20261017();

CREATE OR REPLACE PROCEDURE public.sp_richard_accept_citibike_batch(p_batch_id character varying(64), p_window_start timestamp without time zone, p_window_end timestamp without time zone, p_expected_checkpoint timestamp without time zone, p_expected_rows bigint, p_force_failure boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO pg_catalog
AS $_$
DECLARE
    v_checkpoint TIMESTAMP;
    v_checkpoint_rows BIGINT;
    v_accepted_rows BIGINT;
    v_logical_rows BIGINT;
    v_accepted RECORD;
BEGIN
    -- Lock before reading warehouse state; concurrent calls wait or fail safely.
    LOCK TABLE public.richard_citibike_pipeline_checkpoint,
        public.richard_citibike_accepted_batch,
        public.richard_citibike_station_snapshot_landing,
        public.richard_citibike_station_snapshot_canonical,
        gold.incremental_dim_station,
        gold.incremental_dim_date,
        gold.incremental_fact_station_snapshot;

    IF p_batch_id IS NULL OR p_batch_id !~ '^[A-Za-z0-9_-]{1,64}$' THEN
        RAISE EXCEPTION 'Invalid batch ID';
    END IF;
    IF p_window_start IS NULL OR p_window_end IS NULL
       OR p_expected_checkpoint IS NULL OR p_expected_rows IS NULL
       OR p_window_end <= p_window_start
       OR p_window_start > p_expected_checkpoint
       OR p_window_end <= p_expected_checkpoint OR p_expected_rows <= 0
       OR p_force_failure IS NULL THEN
        RAISE EXCEPTION 'Invalid window, prior checkpoint, row count or failure flag';
    END IF;

    SELECT COUNT(*), MAX(last_completed_utc)
    INTO v_checkpoint_rows, v_checkpoint
    FROM public.richard_citibike_pipeline_checkpoint
    WHERE pipeline_name = 'richard-citibike';
    IF v_checkpoint_rows <> 1 THEN
        RAISE EXCEPTION 'Expected exactly one pipeline checkpoint row';
    END IF;

    SELECT COUNT(*) INTO v_accepted_rows
    FROM public.richard_citibike_accepted_batch
    WHERE batch_id = p_batch_id;
    IF v_accepted_rows > 1 THEN
        RAISE EXCEPTION 'Duplicate accepted batch IDs';
    END IF;
    IF v_accepted_rows = 1 THEN
        SELECT * INTO v_accepted
        FROM public.richard_citibike_accepted_batch WHERE batch_id = p_batch_id;
        IF v_accepted.window_start <> p_window_start
           OR v_accepted.window_end <> p_window_end
           OR v_accepted.checkpoint_before <> p_expected_checkpoint
           OR v_accepted.logical_rows <> p_expected_rows
           OR v_checkpoint < p_window_end THEN
            RAISE EXCEPTION 'Accepted batch context or checkpoint does not match';
        END IF;
        IF p_force_failure THEN
            RAISE EXCEPTION 'Controlled failure requested for an already accepted batch';
        END IF;
        RAISE INFO 'Batch % was already accepted; no writes performed', p_batch_id;
        RETURN;
    END IF;
    IF v_checkpoint <> p_expected_checkpoint THEN
        RAISE EXCEPTION 'Stale prior checkpoint: expected %, found %',
            p_expected_checkpoint, v_checkpoint;
    END IF;

    -- Remove exact landing replays; conflicting copies of a key are rejected.
    CREATE TEMP TABLE richard_accept_input AS
    SELECT DISTINCT *
    FROM public.richard_citibike_station_snapshot_landing
    WHERE batch_id = p_batch_id;

    SELECT COUNT(*) INTO v_logical_rows FROM richard_accept_input;
    IF v_logical_rows <> p_expected_rows THEN
        RAISE EXCEPTION 'Logical landing rows: expected %, found %',
            p_expected_rows, v_logical_rows;
    END IF;
    IF EXISTS (
        SELECT 1 FROM richard_accept_input
        WHERE station_id IS NULL OR TRIM(station_id) = ''
           OR snapshot_timestamp IS NULL
           OR snapshot_timestamp < p_window_start OR snapshot_timestamp >= p_window_end
           OR station_name IS NULL OR TRIM(station_name) = ''
           OR bikes_available IS NULL OR bikes_available < 0
           OR ebikes_available IS NULL OR ebikes_available < 0
           OR docks_available IS NULL OR docks_available < 0
           OR capacity IS NULL OR capacity < 0
           OR is_empty IS NULL OR is_full IS NULL OR is_operational IS NULL
    ) THEN
        RAISE EXCEPTION 'Invalid landing keys, window, metadata or measures';
    END IF;
    IF EXISTS (
        SELECT 1 FROM richard_accept_input
        GROUP BY station_id, snapshot_timestamp HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Conflicting landing values for a business key';
    END IF;

    -- Insert-only canonical policy: the first accepted observation is retained.
    INSERT INTO public.richard_citibike_station_snapshot_canonical
    SELECT i.* FROM richard_accept_input AS i
    WHERE NOT EXISTS (
        SELECT 1 FROM public.richard_citibike_station_snapshot_canonical AS c
        WHERE c.station_id = i.station_id AND c.snapshot_timestamp = i.snapshot_timestamp
    );

    -- Only stations touched by this batch need Type 1 dimension updates.
    -- Use their latest canonical observation, so an old overlap cannot regress them.
    CREATE TEMP TABLE richard_accept_station AS
    SELECT c.station_id, c.station_name, c.capacity
    FROM public.richard_citibike_station_snapshot_canonical AS c
    WHERE EXISTS (
        SELECT 1 FROM richard_accept_input AS i WHERE i.station_id = c.station_id
    )
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY c.station_id ORDER BY c.snapshot_timestamp DESC
    ) = 1;

    UPDATE gold.incremental_dim_station
    SET station_name = i.station_name, capacity = i.capacity
    FROM richard_accept_station AS i
    WHERE incremental_dim_station.station_id = i.station_id;

    INSERT INTO gold.incremental_dim_station (station_id, station_name, capacity)
    SELECT i.station_id, i.station_name, i.capacity FROM richard_accept_station AS i
    WHERE NOT EXISTS (
        SELECT 1 FROM gold.incremental_dim_station AS s
        WHERE s.station_id = i.station_id
    );

    INSERT INTO gold.incremental_dim_date
        (snapshot_date, calendar_year, calendar_month, day_of_month)
    SELECT DISTINCT CAST(i.snapshot_timestamp AS DATE),
        EXTRACT(YEAR FROM i.snapshot_timestamp),
        EXTRACT(MONTH FROM i.snapshot_timestamp),
        EXTRACT(DAY FROM i.snapshot_timestamp)
    FROM richard_accept_input AS i
    WHERE NOT EXISTS (
        SELECT 1 FROM gold.incremental_dim_date AS d
        WHERE d.snapshot_date = CAST(i.snapshot_timestamp AS DATE)
    );

    INSERT INTO gold.incremental_fact_station_snapshot (
        station_id, snapshot_timestamp, snapshot_date,
        bikes_available, ebikes_available, docks_available,
        capacity_at_capture, utilization_pct, is_empty, is_full, is_operational, batch_id
    )
    SELECT c.station_id, c.snapshot_timestamp, CAST(c.snapshot_timestamp AS DATE),
        c.bikes_available, c.ebikes_available, c.docks_available,
        c.capacity, c.utilization_pct, c.is_empty, c.is_full, c.is_operational, c.batch_id
    FROM public.richard_citibike_station_snapshot_canonical AS c
    WHERE EXISTS (
        SELECT 1 FROM richard_accept_input AS i
        WHERE i.station_id = c.station_id AND i.snapshot_timestamp = c.snapshot_timestamp
    ) AND NOT EXISTS (
        SELECT 1 FROM gold.incremental_fact_station_snapshot AS f
        WHERE f.station_id = c.station_id AND f.snapshot_timestamp = c.snapshot_timestamp
    );

    -- Global integrity guards are intentionally conservative for this small lab.
    IF EXISTS (
        SELECT 1 FROM public.richard_citibike_station_snapshot_canonical
        GROUP BY station_id, snapshot_timestamp HAVING COUNT(*) > 1
    ) OR EXISTS (
        SELECT 1 FROM gold.incremental_fact_station_snapshot
        GROUP BY station_id, snapshot_timestamp HAVING COUNT(*) > 1
    ) OR EXISTS (
        SELECT 1 FROM gold.incremental_dim_station
        GROUP BY station_id HAVING COUNT(*) > 1
    ) OR EXISTS (
        SELECT 1 FROM gold.incremental_dim_date
        GROUP BY snapshot_date HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate canonical or Gold keys';
    END IF;
    IF EXISTS (
        SELECT 1 FROM gold.incremental_fact_station_snapshot AS f
        WHERE NOT EXISTS (
            SELECT 1 FROM gold.incremental_dim_station AS s
            WHERE s.station_id = f.station_id
        ) OR NOT EXISTS (
            SELECT 1 FROM gold.incremental_dim_date AS d
            WHERE d.snapshot_date = f.snapshot_date
        )
    ) THEN
        RAISE EXCEPTION 'Missing fact dimension references';
    END IF;
    IF EXISTS (
        SELECT 1 FROM gold.incremental_dim_date AS d
        WHERE d.calendar_year IS NULL OR d.calendar_month IS NULL OR d.day_of_month IS NULL
           OR d.calendar_year <> EXTRACT(YEAR FROM CAST(d.snapshot_date AS TIMESTAMP))
           OR d.calendar_month <> EXTRACT(MONTH FROM CAST(d.snapshot_date AS TIMESTAMP))
           OR d.day_of_month <> EXTRACT(DAY FROM CAST(d.snapshot_date AS TIMESTAMP))
    ) THEN
        RAISE EXCEPTION 'Invalid date dimension attributes';
    END IF;

    -- Ensure the complete canonical projection is represented in facts, and
    -- that there are no extra or mismatched fact rows. EXCEPT compares nulls too.
    IF EXISTS (
        SELECT station_id, snapshot_timestamp, CAST(snapshot_timestamp AS DATE),
            bikes_available, ebikes_available, docks_available, capacity,
            utilization_pct, is_empty, is_full, is_operational, batch_id
        FROM public.richard_citibike_station_snapshot_canonical
        EXCEPT
        SELECT station_id, snapshot_timestamp, snapshot_date,
            bikes_available, ebikes_available, docks_available, capacity_at_capture,
            utilization_pct, is_empty, is_full, is_operational, batch_id
        FROM gold.incremental_fact_station_snapshot
    ) OR EXISTS (
        SELECT station_id, snapshot_timestamp, snapshot_date,
            bikes_available, ebikes_available, docks_available, capacity_at_capture,
            utilization_pct, is_empty, is_full, is_operational, batch_id
        FROM gold.incremental_fact_station_snapshot
        EXCEPT
        SELECT station_id, snapshot_timestamp, CAST(snapshot_timestamp AS DATE),
            bikes_available, ebikes_available, docks_available, capacity,
            utilization_pct, is_empty, is_full, is_operational, batch_id
        FROM public.richard_citibike_station_snapshot_canonical
    ) THEN
        RAISE EXCEPTION 'Canonical and fact contents do not agree';
    END IF;

    INSERT INTO public.richard_citibike_accepted_batch (
        batch_id, window_start, window_end, checkpoint_before, logical_rows
    ) VALUES (
        p_batch_id, p_window_start, p_window_end, p_expected_checkpoint, v_logical_rows
    );
    UPDATE public.richard_citibike_pipeline_checkpoint
    SET last_completed_utc = p_window_end, updated_at = GETDATE()
    WHERE pipeline_name = 'richard-citibike';

    -- Exercise rollback after actual ledger/checkpoint writes, before commit.
    IF p_force_failure THEN
        RAISE EXCEPTION 'Controlled failure before commit; acceptance must roll back';
    END IF;

    DROP TABLE richard_accept_station;
    DROP TABLE richard_accept_input;
    RAISE INFO 'Accepted batch % with % logical rows through %',
        p_batch_id, v_logical_rows, p_window_end;
END;
$_$
;

ALTER TABLE public.richard_citibike_dim_station RENAME TO richard_citibike_dim_station_pre_gold_20261017;

ALTER TABLE public.richard_citibike_dim_date RENAME TO richard_citibike_dim_date_pre_gold_20261017;

ALTER TABLE public.richard_citibike_fact_station_snapshot RENAME TO richard_citibike_fact_station_snapshot_pre_gold_20261017;

COMMIT;
