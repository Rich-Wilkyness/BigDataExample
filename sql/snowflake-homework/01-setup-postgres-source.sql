-- PostgreSQL: run against homework_db in big-data-example-postgres.
-- Synthetic, fictional teaching fixture authored for this repository; CC0-1.0.
-- One record represents a submitted sales transaction; duplicate IDs are intentional.
-- No PK / NOT NULL / positive-value constraints: retain issues for profiling.
-- Fresh setup only. An existing source.sales causes an error; nothing is reset.
\set ON_ERROR_STOP on

BEGIN;
CREATE SCHEMA IF NOT EXISTS source;

CREATE TABLE source.sales (
    transaction_id VARCHAR(20),
    transaction_date DATE,
    customer_name VARCHAR(50),
    product VARCHAR(20),
    category VARCHAR(20),
    quantity INTEGER,
    unit_price NUMERIC(10, 2),
    country VARCHAR(20)
);

INSERT INTO source.sales VALUES
    ('T001', '2026-10-01', '  Alice  ', 'Laptop', 'electronics', 1, 1200.00, ' usa '),
    ('T002', '2026-10-01', 'BOB', 'Mouse', 'Electronics', 3, 25.00, 'USA'),
    ('T003', '2026-10-01', 'Carol', 'Desk', ' furniture ', 1, 450.00, 'Canada'),
    ('T003', '2026-10-02', ' Carol ', 'Desk', 'FURNITURE', 2, 450.00, ' canada '),
    ('T004', '2026-10-02', NULL, 'Chair', 'Furniture', 2, 125.00, 'USA'),
    ('T005', '2026-10-02', 'David', 'Monitor', 'Electronics', -2, 300.00, 'USA'),
    ('T006', '2026-10-03', 'Emma', 'Keyboard', 'electronics', 2, -75.00, 'Canada'),
    ('T007', '2026-10-03', 'Frank', 'Chair', 'Furniture', 0, 125.00, 'United States'),
    ('T008', '2026-10-03', '  Grace ', 'Notebook', 'Stationery', 5, 0.00, 'USA'),
    ('T009', '2026-10-04', 'Henry', 'Pen', ' stationery ', NULL, 2.50, 'Canada'),
    ('T010', '2026-10-04', 'Iris', 'Desk', 'Furniture', 1, NULL, 'Canada'),
    ('T011', NULL, 'Jack', 'Mouse', 'Electronics', 2, 25.00, 'USA'),
    (NULL, '2026-10-05', 'Kate', 'Laptop', 'Electronics', 1, 1200.00, 'USA'),
    ('   ', '2026-10-05', 'Leo', 'Chair', 'Furniture', 1, 125.00, 'Canada'),
    ('T012', '2026-10-05', 'Mia', 'Monitor', NULL, 2, 300.00, 'USA'),
    ('T013', '2026-10-06', 'Noah', 'Keyboard', 'Electronics', 1, 75.00, NULL),
    ('T014', '2026-10-06', '   ', 'Pen', 'Stationery', 10, 2.50, 'canada'),
    ('T015', '2026-10-06', 'Olivia', 'Laptop', 'ELECTRONICS', 1, 1200.00, 'United States'),
    ('T016', '2026-10-07', 'Peter', 'Notebook', 'stationery', 4, 8.00, 'CANADA'),
    ('T001', '2026-10-01', '  Alice  ', 'Laptop', 'electronics', 1, 1200.00, ' usa ');

COMMIT;
