-- Apply once as an authorized database owner in Richard's dev database.
-- Preparation can read the checkpoint; only warehouse acceptance moves it.
CREATE USER "IAMR:RichardCitiBikePrepareBatchRole" PASSWORD DISABLE;
GRANT USAGE ON SCHEMA public TO "IAMR:RichardCitiBikePrepareBatchRole";
GRANT SELECT ON TABLE public.richard_citibike_pipeline_checkpoint
TO "IAMR:RichardCitiBikePrepareBatchRole";
