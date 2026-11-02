-- Run in Richard's warehouse, database dev.
-- Clock: UTC capture timestamp encoded in Bronze filenames.
-- Initial boundary intentionally starts at the first new manual test window;
-- the old October 9 capture is outside this incremental project (no backfill).
CREATE TABLE public.richard_citibike_pipeline_checkpoint (
    pipeline_name VARCHAR(64) NOT NULL,
    last_completed_utc TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT GETDATE()
);

-- Setup only: this does not certify completion of the 15:50-15:55 batch.
-- Run setup with one writer; Redshift does not enforce unique/primary keys.
INSERT INTO public.richard_citibike_pipeline_checkpoint (
    pipeline_name, last_completed_utc
)
SELECT 'richard-citibike', TIMESTAMP '2026-10-16 15:50:00'
WHERE NOT EXISTS (
    SELECT 1 FROM public.richard_citibike_pipeline_checkpoint
    WHERE pipeline_name = 'richard-citibike'
);

SELECT pipeline_name, last_completed_utc, updated_at
FROM public.richard_citibike_pipeline_checkpoint;

-- TODO: Acceptance must assert exactly one checkpoint row, serialize writers,
-- validate the expected prior boundary and batch context, and only advance
-- progress after repeat-safe canonical/Gold writes and quality checks succeed.
