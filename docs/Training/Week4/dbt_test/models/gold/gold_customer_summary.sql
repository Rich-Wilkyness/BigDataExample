{{ config(materialized='table') }}

-- Grain: one row summarizing the current Silver customer dataset.
-- Silver's unique/not_null ID tests establish the one-row-per-customer assumption.
SELECT
    COUNT(*) AS total_customers
FROM {{ ref('silver_customers') }}
