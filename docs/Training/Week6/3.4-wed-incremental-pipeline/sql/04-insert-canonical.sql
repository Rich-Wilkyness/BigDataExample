-- Reconstructs the batch-scoped query developed and executed in this session.
-- Run manually in Richard's warehouse, database dev, one acceptance at a time.
-- Current policy: keep the first accepted observation for each business key.
-- DISTINCT removes exact copies within this batch; conflicting input keys must
-- be rejected before acceptance. This is not a concurrency lock or checkpoint.
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

-- Learner reported 2,518 rows after the first insert and repeat attempt.
SELECT COUNT(*) AS canonical_rows
FROM public.richard_citibike_station_snapshot_canonical;
