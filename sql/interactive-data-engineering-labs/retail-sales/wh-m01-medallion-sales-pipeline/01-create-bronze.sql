-- PostgreSQL 18 / WH-M01 Stage 1
-- Bronze preserves source values as text and adds stable ingestion lineage.

CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.sales_transactions (
    bronze_row_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_batch_id TEXT NOT NULL,
    source_file_name TEXT NOT NULL,
    source_row_number INTEGER NOT NULL CHECK (source_row_number > 0),
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
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_batch_id, source_row_number)
);
