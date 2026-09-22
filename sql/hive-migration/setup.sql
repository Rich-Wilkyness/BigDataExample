\set ON_ERROR_STOP on

-- PostgreSQL 18 / psql
-- This script resets only the three schemas in week3_hive_migration.
DROP SCHEMA IF EXISTS gold CASCADE;
DROP SCHEMA IF EXISTS silver CASCADE;
DROP SCHEMA IF EXISTS bronze CASCADE;

CREATE SCHEMA bronze;
CREATE SCHEMA silver;
CREATE SCHEMA gold;

CREATE TABLE bronze.sales_raw (
    bronze_row_id BIGINT PRIMARY KEY,
    order_number TEXT NOT NULL,
    order_date TEXT,
    expected_receiving_date TEXT,
    shipping_date TEXT,
    order_status TEXT,
    customer_id TEXT,
    customer_company TEXT,
    customer_contact TEXT,
    employee_id TEXT,
    employee_name TEXT,
    office_id TEXT,
    office_city TEXT,
    product_number TEXT NOT NULL,
    product_name TEXT,
    product_category TEXT,
    source_product_category_code TEXT,
    unit_price TEXT,
    quantity TEXT,
    source_file TEXT NOT NULL,
    ingested_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE silver.sales_clean (
    order_number INTEGER NOT NULL,
    order_line_number SMALLINT NOT NULL CHECK (order_line_number > 0),
    order_date DATE NOT NULL,
    expected_receiving_date DATE NOT NULL,
    shipping_date DATE,
    order_status TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    office_id INTEGER NOT NULL,
    product_number TEXT NOT NULL,
    product_name TEXT NOT NULL,
    product_category TEXT NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    sales_amount NUMERIC(14, 2) NOT NULL,
    shipping_days INTEGER,
    PRIMARY KEY (order_number, order_line_number),
    CHECK (sales_amount = quantity * unit_price)
);

CREATE TABLE gold.dim_customer (
    customer_key BIGINT PRIMARY KEY,
    customer_id INTEGER NOT NULL UNIQUE,
    company TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    city_and_state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE gold.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year SMALLINT NOT NULL,
    quarter SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    day_of_month SMALLINT NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
    day_of_week TEXT NOT NULL
);

CREATE TABLE gold.dim_office (
    office_key BIGINT PRIMARY KEY,
    office_id INTEGER NOT NULL UNIQUE,
    city TEXT NOT NULL,
    phone TEXT NOT NULL,
    address_1 TEXT NOT NULL,
    address_2 TEXT,
    state_or_region TEXT,
    country TEXT NOT NULL,
    postal_code TEXT NOT NULL
);

CREATE TABLE gold.dim_employee (
    employee_key BIGINT PRIMARY KEY,
    employee_id INTEGER NOT NULL UNIQUE,
    employee_name TEXT NOT NULL,
    badge_code TEXT NOT NULL,
    email TEXT NOT NULL,
    job_title TEXT NOT NULL,
    office_key BIGINT NOT NULL REFERENCES gold.dim_office(office_key)
);

CREATE TABLE gold.dim_product_category (
    category_key BIGINT PRIMARY KEY,
    product_category TEXT NOT NULL UNIQUE
);

CREATE TABLE gold.dim_product (
    product_key BIGINT PRIMARY KEY,
    product_number TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category_key BIGINT NOT NULL REFERENCES gold.dim_product_category(category_key),
    product_scale TEXT NOT NULL,
    product_manufacturer TEXT NOT NULL,
    length NUMERIC(12, 2),
    width NUMERIC(12, 2),
    height NUMERIC(12, 2)
);

CREATE TABLE gold.dim_order_status (
    status_key BIGINT PRIMARY KEY,
    order_status TEXT NOT NULL UNIQUE
);

CREATE TABLE gold.fact_sales (
    sales_key BIGINT PRIMARY KEY,
    order_number INTEGER NOT NULL,
    order_line_number SMALLINT NOT NULL CHECK (order_line_number > 0),
    order_date_key INTEGER NOT NULL REFERENCES gold.dim_date(date_key),
    product_key BIGINT NOT NULL REFERENCES gold.dim_product(product_key),
    customer_key BIGINT NOT NULL REFERENCES gold.dim_customer(customer_key),
    employee_key BIGINT NOT NULL REFERENCES gold.dim_employee(employee_key),
    status_key BIGINT NOT NULL REFERENCES gold.dim_order_status(status_key),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    sales_amount NUMERIC(14, 2) NOT NULL,
    shipping_days INTEGER,
    UNIQUE (order_number, order_line_number),
    CHECK (sales_amount = quantity * unit_price)
);

\copy bronze.sales_raw FROM '/tmp/week3_hive_migration_data/bronze/sales_raw.csv' WITH (FORMAT csv, HEADER true)
\copy silver.sales_clean FROM '/tmp/week3_hive_migration_data/silver/sales_clean.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_customer FROM '/tmp/week3_hive_migration_data/gold/dim_customer.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_date FROM '/tmp/week3_hive_migration_data/gold/dim_date.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_office FROM '/tmp/week3_hive_migration_data/gold/dim_office.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_employee FROM '/tmp/week3_hive_migration_data/gold/dim_employee.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_product_category FROM '/tmp/week3_hive_migration_data/gold/dim_product_category.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_product FROM '/tmp/week3_hive_migration_data/gold/dim_product.csv' WITH (FORMAT csv, HEADER true)
\copy gold.dim_order_status FROM '/tmp/week3_hive_migration_data/gold/dim_order_status.csv' WITH (FORMAT csv, HEADER true)
\copy gold.fact_sales FROM '/tmp/week3_hive_migration_data/gold/fact_sales.csv' WITH (FORMAT csv, HEADER true)

ANALYZE bronze.sales_raw;
ANALYZE silver.sales_clean;
ANALYZE gold.dim_customer;
ANALYZE gold.dim_date;
ANALYZE gold.dim_office;
ANALYZE gold.dim_employee;
ANALYZE gold.dim_product_category;
ANALYZE gold.dim_product;
ANALYZE gold.dim_order_status;
ANALYZE gold.fact_sales;
