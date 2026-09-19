\set ON_ERROR_STOP on

-- PostgreSQL 18 / psql
-- This file builds the homework dataset inside the week3_hw database.

CREATE SCHEMA bronze;
CREATE SCHEMA silver;
CREATE SCHEMA gold;

-- Bronze preserves source values as text, including invalid and inconsistent data.
CREATE TABLE bronze.sales_transactions (
    bronze_row_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id TEXT,
    transaction_date TEXT,
    product_number TEXT,
    product_name TEXT,
    category TEXT,
    customer_number TEXT,
    customer_name TEXT,
    customer_city TEXT,
    quantity TEXT,
    unit_price TEXT,
    currency TEXT,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO bronze.sales_transactions (
    transaction_id,
    transaction_date,
    product_number,
    product_name,
    category,
    customer_number,
    customer_name,
    customer_city,
    quantity,
    unit_price,
    currency
)
VALUES
    ('T100', '2025-01-15', ' P100 ', 'Laptop', ' electronics ', 'C100', 'Ana Rivera', ' New York ', '2', '900.00', 'usd'),
    ('T101', '2025-02-10', 'P200', 'Standing Desk', 'FURNITURE', 'C200', 'Marcus Lee', 'Denver', '1', '550.00', 'USD'),
    ('T102', '2025-03-05', 'P300', 'Mechanical Keyboard', 'Electronics', 'C100', 'Ana Rivera', 'New York', '3', '120.00', 'USD'),
    ('T103', 'not-a-date', 'P400', 'Office Chair', 'Furniture', 'C300', 'Priya Shah', 'Chicago', '1', 'INVALID', 'USD'),
    ('T104', '2025-04-20', 'P400', 'Office Chair', 'Furniture', 'C300', 'Priya Shah', 'Chicago', '-2', '200.00', 'USD'),
    ('T105', '2026-01-09', 'P100', 'Laptop', 'ELECTRONICS', 'C100', 'Ana Rivera', 'Miami', '1', '950.00', 'USD'),
    ('T106', '2026-02-14', 'P500', 'Webcam', ' electronics', 'C400', 'Jordan Kim', 'Seattle', '4', '80.00', 'USD'),
    ('T106', '2026-02-14', 'P500', 'Webcam', 'electronics', 'C400', 'Jordan Kim', 'Seattle', '4', '80.00', 'USD'),
    ('T107', '2026-03-01', 'P200', 'Standing Desk', 'Furniture', 'C200', 'Marcus Lee', 'Denver', '1', '550.00', 'EUR'),
    ('T108', '2026-03-15', 'P500', 'Webcam', 'Electronics', 'C400', 'Jordan Kim', 'Seattle', '2', '80.00', 'USD'),
    ('T109', '2026-03-20', 'P300', 'Mechanical Keyboard', 'Electronics', 'C400', 'Jordan Kim', 'Seattle', '1', '', 'USD');

CREATE TABLE silver.sales_transactions (
    transaction_id TEXT PRIMARY KEY,
    transaction_date DATE NOT NULL,
    product_number TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    customer_number TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_city TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    currency CHAR(3) NOT NULL CHECK (currency = 'USD'),
    sales_amount NUMERIC(14, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

CREATE TABLE silver.rejected_sales (
    rejection_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bronze_row_id BIGINT NOT NULL REFERENCES bronze.sales_transactions(bronze_row_id),
    transaction_id TEXT,
    rejection_reason TEXT NOT NULL
);

CREATE TEMP TABLE normalized_sales AS
WITH normalized AS (
    SELECT
        bronze_row_id,
        NULLIF(BTRIM(transaction_id), '') AS transaction_id,
        CASE
            WHEN BTRIM(transaction_date) ~ '^\d{4}-\d{2}-\d{2}$'
                THEN BTRIM(transaction_date)::DATE
        END AS transaction_date,
        NULLIF(BTRIM(product_number), '') AS product_number,
        NULLIF(BTRIM(product_name), '') AS product_name,
        INITCAP(LOWER(NULLIF(BTRIM(category), ''))) AS category,
        NULLIF(BTRIM(customer_number), '') AS customer_number,
        NULLIF(BTRIM(customer_name), '') AS customer_name,
        NULLIF(BTRIM(customer_city), '') AS customer_city,
        CASE
            WHEN BTRIM(quantity) ~ '^[+-]?\d+$'
                THEN BTRIM(quantity)::INTEGER
        END AS quantity,
        CASE
            WHEN BTRIM(unit_price) ~ '^[+-]?\d+(\.\d+)?$'
                THEN BTRIM(unit_price)::NUMERIC(12, 2)
        END AS unit_price,
        UPPER(NULLIF(BTRIM(currency), '')) AS currency
    FROM bronze.sales_transactions
)
SELECT
    normalized.*,
    ROW_NUMBER() OVER (
        PARTITION BY transaction_id
        ORDER BY bronze_row_id
    ) AS duplicate_rank
FROM normalized;

INSERT INTO silver.rejected_sales (
    bronze_row_id,
    transaction_id,
    rejection_reason
)
SELECT
    bronze_row_id,
    transaction_id,
    CONCAT_WS(
        '; ',
        CASE WHEN transaction_id IS NULL THEN 'missing transaction_id' END,
        CASE WHEN transaction_date IS NULL THEN 'invalid transaction_date' END,
        CASE WHEN product_number IS NULL THEN 'missing product_number' END,
        CASE WHEN product_name IS NULL THEN 'missing product_name' END,
        CASE WHEN category IS NULL THEN 'missing category' END,
        CASE WHEN customer_number IS NULL THEN 'missing customer_number' END,
        CASE WHEN customer_name IS NULL THEN 'missing customer_name' END,
        CASE WHEN customer_city IS NULL THEN 'missing customer_city' END,
        CASE WHEN quantity IS NULL THEN 'invalid quantity' END,
        CASE WHEN quantity <= 0 THEN 'quantity must be greater than zero' END,
        CASE WHEN unit_price IS NULL THEN 'invalid unit_price' END,
        CASE WHEN unit_price <= 0 THEN 'unit_price must be greater than zero' END,
        CASE WHEN currency IS DISTINCT FROM 'USD' THEN 'unsupported currency' END,
        CASE WHEN duplicate_rank > 1 THEN 'duplicate transaction_id' END
    )
FROM normalized_sales
WHERE
    transaction_id IS NULL
    OR transaction_date IS NULL
    OR product_number IS NULL
    OR product_name IS NULL
    OR category IS NULL
    OR customer_number IS NULL
    OR customer_name IS NULL
    OR customer_city IS NULL
    OR quantity IS NULL
    OR quantity <= 0
    OR unit_price IS NULL
    OR unit_price <= 0
    OR currency IS DISTINCT FROM 'USD'
    OR duplicate_rank > 1;

INSERT INTO silver.sales_transactions (
    transaction_id,
    transaction_date,
    product_number,
    product_name,
    category,
    customer_number,
    customer_name,
    customer_city,
    quantity,
    unit_price,
    currency
)
SELECT
    transaction_id,
    transaction_date,
    product_number,
    product_name,
    category,
    customer_number,
    customer_name,
    customer_city,
    quantity,
    unit_price,
    currency
FROM normalized_sales
WHERE
    transaction_id IS NOT NULL
    AND transaction_date IS NOT NULL
    AND product_number IS NOT NULL
    AND product_name IS NOT NULL
    AND category IS NOT NULL
    AND customer_number IS NOT NULL
    AND customer_name IS NOT NULL
    AND customer_city IS NOT NULL
    AND quantity > 0
    AND unit_price > 0
    AND currency = 'USD'
    AND duplicate_rank = 1;

-- Gold dimensions use surrogate keys while retaining the source business keys.
CREATE TABLE gold.dim_product (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_number TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    product_category TEXT NOT NULL
);

CREATE TABLE gold.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year SMALLINT NOT NULL,
    quarter SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    day SMALLINT NOT NULL CHECK (day BETWEEN 1 AND 31),
    day_of_week TEXT NOT NULL
);

CREATE TABLE gold.dim_customer (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_number TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    city TEXT NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE,
    is_current BOOLEAN NOT NULL,
    UNIQUE (customer_number, effective_start_date),
    CHECK (effective_end_date IS NULL OR effective_end_date >= effective_start_date),
    CHECK ((is_current AND effective_end_date IS NULL) OR (NOT is_current AND effective_end_date IS NOT NULL))
);

CREATE UNIQUE INDEX one_current_customer_record
ON gold.dim_customer (customer_number)
WHERE is_current;

CREATE TABLE gold.fact_sales (
    sales_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    line_number SMALLINT NOT NULL DEFAULT 1 CHECK (line_number > 0),
    product_key BIGINT NOT NULL REFERENCES gold.dim_product(product_key),
    customer_key BIGINT NOT NULL REFERENCES gold.dim_customer(customer_key),
    date_key INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    sales_amount NUMERIC(14, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    UNIQUE (transaction_id, line_number)
);

INSERT INTO gold.dim_product (
    product_number,
    product_name,
    product_category
)
SELECT DISTINCT
    product_number,
    product_name,
    category
FROM silver.sales_transactions
ORDER BY product_number;

INSERT INTO gold.dim_date (
    date_key,
    full_date,
    year,
    quarter,
    month,
    month_name,
    day,
    day_of_week
)
SELECT
    TO_CHAR(full_date, 'YYYYMMDD')::INTEGER,
    full_date,
    EXTRACT(YEAR FROM full_date)::SMALLINT,
    EXTRACT(QUARTER FROM full_date)::SMALLINT,
    EXTRACT(MONTH FROM full_date)::SMALLINT,
    TRIM(TO_CHAR(full_date, 'Month')),
    EXTRACT(DAY FROM full_date)::SMALLINT,
    TRIM(TO_CHAR(full_date, 'Day'))
FROM (
    SELECT DISTINCT transaction_date AS full_date
    FROM silver.sales_transactions

    UNION

    -- Included so homework question 10 can practice looking up this date.
    SELECT DATE '2026-09-15'
) AS dates
ORDER BY full_date;

-- C100 demonstrates an SCD Type 2 history: New York, then Miami.
INSERT INTO gold.dim_customer (
    customer_number,
    customer_name,
    city,
    effective_start_date,
    effective_end_date,
    is_current
)
VALUES
    ('C100', 'Ana Rivera', 'New York', DATE '2025-01-01', DATE '2025-12-31', FALSE),
    ('C100', 'Ana Rivera', 'Miami', DATE '2026-01-01', NULL, TRUE),
    ('C200', 'Marcus Lee', 'Denver', DATE '2025-01-01', NULL, TRUE),
    ('C400', 'Jordan Kim', 'Seattle', DATE '2025-01-01', NULL, TRUE);

INSERT INTO gold.fact_sales (
    transaction_id,
    line_number,
    product_key,
    customer_key,
    date_key,
    quantity,
    unit_price
)
SELECT
    sales.transaction_id,
    1,
    product.product_key,
    customer.customer_key,
    date_dimension.date_key,
    sales.quantity,
    sales.unit_price
FROM silver.sales_transactions AS sales
JOIN gold.dim_product AS product
    ON sales.product_number = product.product_number
JOIN gold.dim_date AS date_dimension
    ON sales.transaction_date = date_dimension.full_date
JOIN gold.dim_customer AS customer
    ON sales.customer_number = customer.customer_number
    AND sales.transaction_date >= customer.effective_start_date
    AND (
        customer.effective_end_date IS NULL
        OR sales.transaction_date <= customer.effective_end_date
    )
ORDER BY sales.transaction_id;
