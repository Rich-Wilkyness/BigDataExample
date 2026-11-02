-- Apply once as the procedure owner in Richard's warehouse, database dev.
-- The procedure runs with its owner's table privileges and a fixed search_path.
-- The workflow identity receives schema usage and procedure execution only.
CREATE USER "IAMR:RichardCitiBikeIncrementalWorkflowRole" PASSWORD DISABLE;
GRANT USAGE ON SCHEMA public TO "IAMR:RichardCitiBikeIncrementalWorkflowRole";
REVOKE EXECUTE ON PROCEDURE public.sp_richard_accept_citibike_batch(
    VARCHAR, TIMESTAMP, TIMESTAMP, TIMESTAMP, BIGINT, BOOLEAN
) FROM PUBLIC;
GRANT EXECUTE ON PROCEDURE public.sp_richard_accept_citibike_batch(
    VARCHAR, TIMESTAMP, TIMESTAMP, TIMESTAMP, BIGINT, BOOLEAN
) TO "IAMR:RichardCitiBikeIncrementalWorkflowRole";
