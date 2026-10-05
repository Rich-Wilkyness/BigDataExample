# Snowflake homework: PostgreSQL source setup

This starter supplies a small source dataset for [Friday homework Part 1](../5.1_Fri_HW.md). Profiling queries, Silver cleaning rules, and Gold transformations remain learner work.

## What exists where?

```text
PostgreSQL container                       Your Mac / Snowflake
homework_db.source.sales -- CSV export --> data/raw/snowflake-homework/sales.csv
                                          │ upload to internal stage
                                          ▼
                                          DE_CLASS.RAW.SALES_HOMEWORK_STAGE
                                          │ COPY INTO
                                          ▼
                                          DE_CLASS.RAW.SALES
                                          │ your transformation
                                          ▼
                                          DE_CLASS.SILVER.<your_table>
```

PostgreSQL database `homework_db` and schema `source` hold the source. Snowflake database `DE_CLASS` and schemas `RAW`, `SILVER`, and `GOLD` hold the homework pipeline. Creating one does not create the other. `CREATE WAREHOUSE`, stages, and dynamic tables are Snowflake features; run their SQL in Snowflake.

## Dataset contract

- **Origin:** 20 fictional sales records authored for this repository, with no real personal data; CC0-1.0. The canonical fixture is the `INSERT` in [PostgreSQL setup SQL](../../../../sql/snowflake-homework/01-setup-postgres-source.sql).
- **Grain:** one submitted sales transaction per input record. Repeated IDs include an exact duplicate and a changed transaction version; deciding which to keep belongs to the Silver exercise.
- **Columns:** the eight fields from the lecture's SALES table, in the same order. Date values are valid `DATE` values or NULL; this starter avoids invalid date text that would be rejected during typed loading.
- **Intentional issues:** duplicates, NULLs, a blank ID/name, surrounding whitespace, inconsistent capitalization/country labels, and negative/zero quantities or prices. A blank string and NULL are different values.
- **Constraints:** no primary key, non-NULL, or positive-value constraint removes these issues before you can inspect them. The data is not silently cleaned.
- **Reproduction:** seed a fresh `source.sales` with the setup SQL, then export the explicit eight-column query below. Export ordering is repeatable for these records; identical duplicates remain identical.
- **Generated CSV:** local output under gitignored `data/raw/`. The fixture SQL, not a private export, is the committed source of truth.

## Checkpoint 1: connect to the right PostgreSQL database

Run in your Mac terminal:

```bash
docker exec -it big-data-example-postgres psql -X -U bigdata -d homework_db
```

Inside psql:

```text
\conninfo
\dn
\d source.sales
```

`\conninfo` should show `homework_db`, not `bigdata` or `sample_database`. `\d source.sales` should show eight columns. Try one small query:

```sql
SELECT * FROM source.sales LIMIT 5;
```

Exit with `\q` before running Mac shell commands.

## Checkpoint 2: fresh setup or export

Commands below assume the repository root:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample
```

The source was set up during this assistance session once verification succeeded. Do not rerun this fresh-setup command against an existing table. For a new environment with the container and `homework_db` already present:

```bash
docker exec -i big-data-example-postgres psql -X -v ON_ERROR_STOP=1 -U bigdata -d homework_db < sql/snowflake-homework/01-setup-postgres-source.sql
```

The setup uses a transaction and deliberately fails if `source.sales` already exists; it does not truncate or replace existing work.

To export the source again:

```bash
mkdir -p data/raw/snowflake-homework
docker exec big-data-example-postgres psql -X -v ON_ERROR_STOP=1 -U bigdata -d homework_db -c "\copy (SELECT transaction_id, transaction_date, customer_name, product, category, quantity, unit_price, country FROM source.sales ORDER BY transaction_id NULLS LAST, transaction_date NULLS LAST) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)" > data/raw/snowflake-homework/sales.csv
```

`TO STDOUT` streams the CSV out of the container. The shell's `>` writes it on your Mac at the repository path and overwrites that generated export. You do not need to copy a container-local `/tmp` file. PostgreSQL CSV represents NULL with an unquoted empty field by default; whitespace-only fields remain whitespace. Source: [psql client-side copy](https://www.postgresql.org/docs/current/app-psql.html).

## Checkpoint 3: prepare and load Snowflake RAW

In Snowsight, use the class role and warehouse. Check existing objects before running [Snowflake setup SQL](../../../../sql/snowflake-homework/02-setup-snowflake-raw.sql); it creates the database/schemas if absent and a fresh typed RAW table. If `DE_CLASS.RAW.SALES` already exists, inspect its schema and rows instead of replacing it.

Upload the exported Mac file to `DE_CLASS.RAW.SALES_HOMEWORK_STAGE` using Snowsight's stage upload action. Then run in Snowflake:

```sql
LIST @DE_CLASS.RAW.SALES_HOMEWORK_STAGE;
```

Use the exact filename returned by `LIST`. For a browser upload named `sales.csv`:

```sql
COPY INTO DE_CLASS.RAW.SALES
FROM @DE_CLASS.RAW.SALES_HOMEWORK_STAGE
FILES = ('sales.csv')
FILE_FORMAT = (
    TYPE = CSV
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    EMPTY_FIELD_AS_NULL = TRUE
    TRIM_SPACE = FALSE
)
ON_ERROR = 'ABORT_STATEMENT';

SELECT COUNT(*) FROM DE_CLASS.RAW.SALES;
SELECT * FROM DE_CLASS.RAW.SALES LIMIT 5;
```

The expected initial count is **20**, with the intentional issues still present. `TRIM_SPACE = FALSE` preserves whitespace for your cleaning exercise. The matching column order matters; skipping a CSV header does not map fields by name. Stop and inspect the load result if counts differ. Do not use `FORCE = TRUE` simply to rerun a successful load. Source: [Snowflake COPY INTO](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table).

If you prefer Snowflake CLI, Friday's [connection and upload notes](../5_Fri_Snowflake_Adv.md#checkpoint-1-configure-snowflake-cli-authentication) explain it. CLI auto-compression can change the staged name to `sales.csv.gz`; match `FILES` to `LIST`.

## Your next checkpoint

Once RAW has 20 rows, begin Part 1's profiling in Snowflake. Start with the assignment's `COUNT(*)`, then write the distinct-ID, duplicate, NULL, quantity/price, date-range, and category/country queries yourself. Keep the source/RAW data unchanged and save your profiling SQL.

## Verification boundary

On 2026-10-05, PostgreSQL setup committed successfully, `\conninfo` confirmed `homework_db`, table inspection confirmed the eight supplied columns, and `COUNT(*)` returned 20. The Mac CSV was checked for its header, 20 records, valid-or-missing dates, and preserved duplicates, empty/whitespace fields, and negative values. README links, code fences, and shell syntax passed checks.

PostgreSQL setup and exported CSV are verified separately from Snowflake execution. Upload, COPY results, permissions, and RAW row count need to be checked in your Snowflake account before claiming the load is complete. No Silver or Gold transformation is supplied here.
