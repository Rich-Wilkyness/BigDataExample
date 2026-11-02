-- Run each numbered section separately in Query Editor v2, database dev.
-- Assumes checkpoint is still 2026-10-16 15:50:00 and the batch is not accepted.

-- 1. Controlled failure: expect the explicit exception, not a successful CALL.
CALL public.sp_richard_accept_citibike_batch(
    'manual_20261016T1550_1555_v2',
    TIMESTAMP '2026-10-16 15:50:00',
    TIMESTAMP '2026-10-16 15:55:00',
    TIMESTAMP '2026-10-16 15:50:00',
    CAST(2518 AS BIGINT), TRUE
);

-- 2. After the failed call, expect 15:50:00 and zero accepted rows.
SELECT pipeline_name, last_completed_utc
FROM public.richard_citibike_pipeline_checkpoint;
SELECT COUNT(*) AS accepted_rows
FROM public.richard_citibike_accepted_batch
WHERE batch_id = 'manual_20261016T1550_1555_v2';
-- Also rerun 09-validate-gold.sql; previously committed manual data stays intact.

-- 3. Successful recovery: change only TRUE to FALSE.
CALL public.sp_richard_accept_citibike_batch(
    'manual_20261016T1550_1555_v2',
    TIMESTAMP '2026-10-16 15:50:00',
    TIMESTAMP '2026-10-16 15:55:00',
    TIMESTAMP '2026-10-16 15:50:00',
    CAST(2518 AS BIGINT), FALSE
);

-- 4. Expect checkpoint 15:55:00, one ledger row, unchanged Gold counts.
SELECT pipeline_name, last_completed_utc
FROM public.richard_citibike_pipeline_checkpoint;
SELECT * FROM public.richard_citibike_accepted_batch
WHERE batch_id = 'manual_20261016T1550_1555_v2';

-- 5. Rerun section 3 unchanged: expected accepted-batch no-op.
-- Do not change the expected prior boundary on this same-batch replay.
-- Verify one ledger row and rerun 09-validate-gold.sql.
