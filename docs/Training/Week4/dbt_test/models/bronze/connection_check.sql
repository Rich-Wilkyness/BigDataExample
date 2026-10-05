{{ config(materialized='table') }}

SELECT
    1 AS id,
    'dbt is connected' AS message