# Week 3 Data Warehousing Homework Database

This PostgreSQL 18 setup creates a small, self-contained medallion warehouse for `docs/Training/Week2/4.2_Thur_HW.md`. It is homework infrastructure, not the future notebook-based Bronze → Silver → Gold lab.

## Create and populate the database

Run these commands from the repository root while `big-data-example-postgres` is healthy:

```bash
docker exec -i big-data-example-postgres psql -U bigdata -d bigdata < sql/week3-homework/create-database.sql
docker exec -i big-data-example-postgres psql -U bigdata -d week3_hw < sql/week3-homework/setup.sql
docker exec -i big-data-example-postgres psql -U bigdata -d week3_hw < sql/week3-homework/verify.sql
```

Connect interactively with:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d week3_hw
```

Useful commands after the `week3_hw=#` prompt include:

```text
\dn
\dt bronze.*
\dt silver.*
\dt gold.*
SELECT * FROM gold.fact_sales ORDER BY transaction_id;
```

## Reset the homework data

The reset sequence removes and recreates only the `bronze`, `silver`, and `gold` schemas inside `week3_hw`. It does not remove the database, Docker container, or named volume.

```bash
docker exec -i big-data-example-postgres psql -U bigdata -d week3_hw < sql/week3-homework/reset.sql
docker exec -i big-data-example-postgres psql -U bigdata -d week3_hw < sql/week3-homework/setup.sql
docker exec -i big-data-example-postgres psql -U bigdata -d week3_hw < sql/week3-homework/verify.sql
```

## Expected layer counts

| Table | Expected rows |
| --- | ---: |
| `bronze.sales_transactions` | 11 |
| `silver.sales_transactions` | 6 |
| `silver.rejected_sales` | 5 |
| `gold.dim_product` | 4 |
| `gold.dim_date` | 7 |
| `gold.dim_customer` | 4 |
| `gold.fact_sales` | 6 |

Bronze deliberately contains inconsistent capitalization, whitespace, an invalid date and price, a negative quantity, a duplicate transaction ID, an unsupported currency, and a missing price. Silver retains six valid transactions and records five rejected rows with reasons. Gold publishes a small star schema and includes two customer dimension versions that demonstrate SCD Type 2 history.
