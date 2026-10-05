-- Snowflake SQL, not PostgreSQL. Run in Snowsight or Snowflake CLI.
-- Requires privileges to create/use the named objects; follow class permissions.
-- Inspect any existing RAW.SALES before running. CREATE TABLE stops if it exists.
-- No warehouse creation here: select the warehouse provided for your class.
CREATE DATABASE IF NOT EXISTS DE_CLASS;
CREATE SCHEMA IF NOT EXISTS DE_CLASS.RAW;
CREATE SCHEMA IF NOT EXISTS DE_CLASS.SILVER;
CREATE SCHEMA IF NOT EXISTS DE_CLASS.GOLD;

CREATE TABLE DE_CLASS.RAW.SALES (
    transaction_id VARCHAR(20),
    transaction_date DATE,
    customer_name VARCHAR(50),
    product VARCHAR(20),
    category VARCHAR(20),
    quantity INTEGER,
    unit_price DECIMAL(10, 2),
    country VARCHAR(20)
);

CREATE STAGE IF NOT EXISTS DE_CLASS.RAW.SALES_HOMEWORK_STAGE;
