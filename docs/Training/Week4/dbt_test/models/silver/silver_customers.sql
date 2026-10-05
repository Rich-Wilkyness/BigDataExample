{{ config(materialized='table') }}

SELECT
    customer_id,
    INITCAP(TRIM(name)) AS customer_name
FROM {{ ref('bronze_customers') }}
-- `ref()` identifies the upstream dbt model.
-- dbt run --select +silver_customers
    -- The leading `+` includes upstream models, so dbt builds `bronze_customers` before `silver_customers`