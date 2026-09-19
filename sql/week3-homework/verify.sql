\set ON_ERROR_STOP on

-- PostgreSQL 18 / psql
\echo 'Homework layer row counts'
SELECT 'bronze.sales_transactions' AS table_name, COUNT(*) AS row_count
FROM bronze.sales_transactions
UNION ALL
SELECT 'silver.sales_transactions', COUNT(*)
FROM silver.sales_transactions
UNION ALL
SELECT 'silver.rejected_sales', COUNT(*)
FROM silver.rejected_sales
UNION ALL
SELECT 'gold.dim_product', COUNT(*)
FROM gold.dim_product
UNION ALL
SELECT 'gold.dim_date', COUNT(*)
FROM gold.dim_date
UNION ALL
SELECT 'gold.dim_customer', COUNT(*)
FROM gold.dim_customer
UNION ALL
SELECT 'gold.fact_sales', COUNT(*)
FROM gold.fact_sales
ORDER BY table_name;

\echo 'Rejected Bronze rows and reasons'
SELECT
    transaction_id,
    rejection_reason
FROM silver.rejected_sales
ORDER BY rejection_id;

\echo 'Fact grain violations: expected 0 rows'
SELECT
    transaction_id,
    line_number,
    COUNT(*) AS copies
FROM gold.fact_sales
GROUP BY
    transaction_id,
    line_number
HAVING COUNT(*) > 1;

\echo 'Sales amount violations: expected 0 rows'
SELECT *
FROM gold.fact_sales
WHERE sales_amount <> quantity * unit_price;

\echo 'Homework question 3 result'
SELECT
    product.product_category,
    date_dimension.year,
    SUM(sales.sales_amount) AS total_sales_amount
FROM gold.fact_sales AS sales
JOIN gold.dim_product AS product
    ON sales.product_key = product.product_key
JOIN gold.dim_date AS date_dimension
    ON sales.date_key = date_dimension.date_key
GROUP BY
    product.product_category,
    date_dimension.year
ORDER BY
    date_dimension.year,
    total_sales_amount DESC;
