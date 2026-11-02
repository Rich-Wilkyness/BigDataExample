-- One-time repair only, discovered during live acceptance testing.
-- The initial DynamicFrame int columns were staged as null BIGINT fields;
-- the corrected loader casts these columns to long and has reloaded this batch.
-- Execute all four statements as one transaction, never as separate deletes.
-- Run first with TRUE and verify rollback; repeat with FALSE for recovery.
BEGIN;
DELETE FROM public.richard_citibike_station_snapshot_landing
WHERE batch_id = 'manual_20261016T1550_1555_v2'
  AND (bikes_available IS NULL OR ebikes_available IS NULL
       OR docks_available IS NULL OR capacity IS NULL);
DELETE FROM public.richard_citibike_station_snapshot_canonical
WHERE batch_id = 'manual_20261016T1550_1555_v2'
  AND (bikes_available IS NULL OR ebikes_available IS NULL
       OR docks_available IS NULL OR capacity IS NULL);
DELETE FROM gold.incremental_fact_station_snapshot
WHERE batch_id = 'manual_20261016T1550_1555_v2'
  AND (bikes_available IS NULL OR ebikes_available IS NULL
       OR docks_available IS NULL OR capacity_at_capture IS NULL);
CALL public.sp_richard_accept_citibike_batch(
    CAST('manual_20261016T1550_1555_v2' AS VARCHAR),
    TIMESTAMP '2026-10-16 15:50:00', TIMESTAMP '2026-10-16 15:55:00',
    TIMESTAMP '2026-10-16 15:50:00', CAST(2518 AS BIGINT), TRUE
);
COMMIT;
