\set ON_ERROR_STOP on

-- PostgreSQL 18 / psql
\conninfo

\echo 'Migration layer row counts'
SELECT 'bronze.sales_raw' AS table_name, COUNT(*) AS row_count
FROM bronze.sales_raw
UNION ALL
SELECT 'silver.sales_clean', COUNT(*)
FROM silver.sales_clean
UNION ALL
SELECT 'gold.dim_customer', COUNT(*)
FROM gold.dim_customer
UNION ALL
SELECT 'gold.dim_date', COUNT(*)
FROM gold.dim_date
UNION ALL
SELECT 'gold.dim_employee', COUNT(*)
FROM gold.dim_employee
UNION ALL
SELECT 'gold.dim_office', COUNT(*)
FROM gold.dim_office
UNION ALL
SELECT 'gold.dim_order_status', COUNT(*)
FROM gold.dim_order_status
UNION ALL
SELECT 'gold.dim_product', COUNT(*)
FROM gold.dim_product
UNION ALL
SELECT 'gold.dim_product_category', COUNT(*)
FROM gold.dim_product_category
UNION ALL
SELECT 'gold.fact_sales', COUNT(*)
FROM gold.fact_sales
ORDER BY table_name;

\echo 'Layer reconciliation'
SELECT
    (SELECT COUNT(*) FROM bronze.sales_raw) AS bronze_rows,
    (SELECT COUNT(*) FROM bronze.sales_raw WHERE order_date IS NULL OR order_date = '') AS bronze_orphans,
    (SELECT COUNT(*) FROM silver.sales_clean) AS silver_rows,
    (SELECT COUNT(*) FROM gold.fact_sales) AS fact_rows,
    (SELECT SUM(sales_amount) FROM silver.sales_clean) AS silver_sales_amount,
    (SELECT SUM(sales_amount) FROM gold.fact_sales) AS fact_sales_amount;

\echo 'Fact grain violations: expected 0 rows'
SELECT
    order_number,
    order_line_number,
    COUNT(*) AS copies
FROM gold.fact_sales
GROUP BY
    order_number,
    order_line_number
HAVING COUNT(*) > 1;

\echo 'Sales amount violations: expected 0 rows'
SELECT sales_key
FROM gold.fact_sales
WHERE sales_amount <> quantity * unit_price;

\echo 'Automated fixture checks'
DO $$
BEGIN
    IF current_database() <> 'week3_hive_migration' THEN
        RAISE EXCEPTION 'Wrong database: %', current_database();
    END IF;

    IF (SELECT COUNT(*) FROM bronze.sales_raw) <> 2996 THEN
        RAISE EXCEPTION 'Unexpected Bronze row count';
    END IF;

    IF (SELECT COUNT(*) FROM bronze.sales_raw WHERE order_date IS NULL OR order_date = '') <> 193 THEN
        RAISE EXCEPTION 'Unexpected Bronze orphan count';
    END IF;

    IF (SELECT COUNT(*) FROM silver.sales_clean) <> 2803
        OR (SELECT COUNT(*) FROM gold.fact_sales) <> 2803 THEN
        RAISE EXCEPTION 'Unexpected Silver or fact row count';
    END IF;

    IF (SELECT SUM(sales_amount) FROM silver.sales_clean)
        <> (SELECT SUM(sales_amount) FROM gold.fact_sales) THEN
        RAISE EXCEPTION 'Silver and Gold sales totals do not reconcile';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM gold.fact_sales
        GROUP BY order_number, order_line_number
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate Gold fact grain found';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM gold.fact_sales
        WHERE sales_amount <> quantity * unit_price
    ) THEN
        RAISE EXCEPTION 'Invalid Gold sales amount found';
    END IF;
END
$$;

\echo 'All automated fixture checks passed.'
