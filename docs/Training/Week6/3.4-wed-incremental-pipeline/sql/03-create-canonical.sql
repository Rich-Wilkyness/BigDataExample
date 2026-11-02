-- Run in Richard's warehouse, database dev.
-- One intended canonical row per (station_id, snapshot_timestamp).
-- Matching landing column order also retains batch provenance.
CREATE TABLE public.richard_citibike_station_snapshot_canonical (
    LIKE public.richard_citibike_station_snapshot_landing
);

-- Expect zero rows before implementing the acceptance step.
SELECT COUNT(*) AS canonical_rows
FROM public.richard_citibike_station_snapshot_canonical;

-- TODO: Build batch-scoped canonical acceptance separately.
-- Deduplicate replayed landing input before writing canonical.
-- Define the policy for conflicting values at the same business key.
-- Do not advance a completed checkpoint until downstream Gold/checks succeed.


-- 1. Use equality comparisons between the canonical row (c) and incoming landing row (l):
-- 2. Both fields must match because the business key is station + capture timestamp. A station’s observation at a different timestamp should remain a separate row.
-- NOT EXISTS means: insert this incoming observation only when canonical has no matching key.
INSERT INTO public.richard_citibike_station_snapshot_canonical
SELECT DISTINCT l.*
FROM public.richard_citibike_station_snapshot_landing AS l
WHERE l.batch_id = 'manual_20261016T1550_1555_v2'
  AND NOT EXISTS (
      SELECT 1
      FROM public.richard_citibike_station_snapshot_canonical AS c
      WHERE c.station_id = l.station_id
        AND c.snapshot_timestamp = l.snapshot_timestamp
  );