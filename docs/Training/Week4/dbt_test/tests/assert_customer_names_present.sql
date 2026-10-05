-- A singular data test returns violations: zero rows means it passes.
-- not_null alone permits empty strings; this rule also rejects whitespace-only names.
SELECT
    customer_id,
    customer_name
FROM {{ ref('silver_customers') }}
WHERE customer_name IS NULL
   OR TRIM(customer_name) = ''
