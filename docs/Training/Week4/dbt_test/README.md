# Customer pipeline: dbt with PostgreSQL

This practice project connects a loaded PostgreSQL source to a Bronze view, cleaned Silver table, and Gold summary. dbt runs on the Mac and submits SQL to the PostgreSQL container. The connection profile lives in `~/.dbt/profiles.yml`; credentials do not belong in this project.

## Data flow and grain

```text
bronze.customers                  source table loaded outside dbt
    ↓ source('raw_shop', 'customers')
dbt_dev.bronze_customers          view, same rows as the source
    ↓ ref('bronze_customers')
dbt_dev.silver_customers          table, one row per customer
    ↓ ref('silver_customers')
dbt_dev.gold_customer_summary     table, one summary row
```

The database is `dbt_test`; the model output schema is `dbt_dev`. Folder names organize models and their configuration. `models/gold/` does not automatically mean a PostgreSQL schema named `gold`.

## Prepare the PostgreSQL database and source data

The initialized dbt project needs a database to connect to and a loaded source table to read. Initialization creates project/profile files; it does not create this dataset.

From the Mac, open psql in the PostgreSQL container:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d bigdata
```

Inside psql, use `\l` to inspect databases. If `dbt_test` is absent, create it once:

```sql
CREATE DATABASE dbt_test;
```

Connect to it and inspect the active connection:

```text
\c dbt_test
\conninfo
```

Create the namespaces if needed:

```sql
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS dbt_dev;
```

For a fresh source, create and populate the two-row dataset below. If `bronze.customers` already exists, inspect it instead; do not repeat the insert into an existing populated table.

```sql
CREATE TABLE bronze.customers (
    customer_id INTEGER,
    name TEXT
);

INSERT INTO bronze.customers (customer_id, name) VALUES
    (1, '  alice  '),
    (2, 'BOB');

SELECT * FROM bronze.customers ORDER BY customer_id;
```

- The raw spaces/capitalization are deliberate; Silver should produce `Alice` and `Bob` while preserving IDs.
- One row represents one customer. Source identity is `customer_id`, not the name.
- `bronze` holds the source, while `dbt_dev` holds model outputs. A YAML source declaration describes this table but does not load it.
- Exit psql with `\q` before running dbt commands on the Mac.

## Configure and check the dbt connection

For initialization and profile setup, follow the [lecture guide's setup checkpoints](../4_Thur_Snowflake.md#checkpoint-3-initialize-the-project-with-explicit-connection-values). Use PostgreSQL at `127.0.0.1:5432`, user `bigdata`, database `dbt_test`, output schema `dbt_dev`, target `dev`, and one thread. Use the existing container password from `infra/postgres/.env`; do not create a different password during dbt initialization.

Run from the project directory on the Mac with the intended Python/dbt environment selected:

```bash
dbt debug --target dev
dbt run --select connection_check
```

`debug` checks the connection. The [connection-check model](models/bronze/connection_check.sql) verifies that dbt can create a table without depending on any source records. Inside psql connected to `dbt_test`, `SELECT * FROM dbt_dev.connection_check;` should return `(1, 'dbt is connected')`.

Once the source exists, [sources.yml](models/sources.yml) maps logical `raw_shop.customers` to physical `bronze.customers`. The [Bronze model](models/bronze/bronze_customers.sql) uses `source()` and the [Silver model](models/silver/silver_customers.sql) uses `ref()` to normalize names. Their full SQL is in those files.

## Build and test

Run from this project directory on your Mac:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample/docs/Training/Week4/dbt_test
export PYENV_VERSION=3.11.16
dbt build --select +gold_customer_summary
```

- The leading `+` includes upstream dependencies. The loaded source table must already exist.
- `dbt build` builds Bronze and Silver, runs the applicable Silver tests, and then builds Gold when those tests pass.
- The separate `connection_check` model is not an ancestor of Gold and is not selected by this command.
- Bronze defaults to a view; Silver and Gold default to tables through the folder settings in `dbt_project.yml`. A model's inline `config()` can override those settings.
- Table results reflect their last successful build. Changing the source does not automatically refresh Silver or Gold.

## Custom data test: reject blank customer names

The [custom test](tests/assert_customer_names_present.sql) returns Silver rows with null, empty, or space-only names:

```sql
SELECT
    customer_id,
    customer_name
FROM {{ ref('silver_customers') }}
WHERE customer_name IS NULL
   OR TRIM(customer_name) = ''
```

A dbt singular data test is a SQL query whose result contains violations: zero rows passes. Keep the query in `tests/` and omit the final semicolon; dbt wraps it in generated SQL. This test is discovered from its file and does not need a YAML test declaration.

- `not_null` catches null names, but an empty string is a non-null value.
- Trimming before comparing with `''` also catches names containing only ordinary spaces; it does not classify every possible Unicode whitespace character.
- Tests detect data problems; they do not repair rows or create database constraints.
- With default error severity, failed upstream tests in `dbt build` can skip dependent models. Previously created tables remain; the entire pipeline is not rolled back as one transaction.

To run just this check against the existing Silver table:

```bash
dbt test --select assert_customer_names_present
```

## Gold summary: change the grain deliberately

The [Gold model](models/gold/gold_customer_summary.sql) counts Silver rows:

```sql
{{ config(materialized='table') }}

SELECT COUNT(*) AS total_customers
FROM {{ ref('silver_customers') }}
```

- Silver has one row per customer; Gold has one row summarizing the dataset.
- `COUNT(*)` counts rows. Interpreting that as customers relies on Silver's unique and non-null ID checks.
- No `GROUP BY` means one overall aggregate row. Empty input still produces one row with a count of zero.
- Two rows produce a count of two, but that alone does not prove the source is complete. Reconcile against the expected input.

Inside psql connected to `dbt_test`:

```sql
SELECT * FROM dbt_dev.gold_customer_summary;
```

The current Alice/Bob fixture produces `total_customers = 2`.

## Generate and explore documentation

Model/column descriptions live in YAML; [the project overview](models/overview.md) supplies the documentation landing page. Source declarations and `ref()` calls supply the lineage graph.

From this project directory on your Mac:

```bash
dbt docs generate
dbt docs serve --port 8080
```

Visit `http://localhost:8080` if a browser does not open. Stop the server with **Ctrl+C**.

- `generate` compiles the project and retrieves catalog metadata; it does not build or refresh the model tables.
- For this dbt Core installation, the generated `target/index.html`, `manifest.json`, and `catalog.json` form the documentation site. Generated files are ignored by Git.
- Open `silver_customers` to inspect column descriptions and tests. Open `gold_customer_summary` and use the lineage graph to trace its upstream source and models.
- Regenerate after changing descriptions, models, or database objects; served files are a generated snapshot.
- YAML descriptions become documentation. They do not automatically become database comments without additional configuration.

Sources: [dbt data tests](https://docs.getdbt.com/docs/build/data-tests), [dbt build](https://docs.getdbt.com/reference/commands/build), and [dbt documentation commands](https://docs.getdbt.com/reference/commands/cmd-docs).
