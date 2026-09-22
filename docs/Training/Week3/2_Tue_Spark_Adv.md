
# Tuesday: Advanced Spark

## PostgreSQL-to-Hive migration with Spark

### Goal

Move the Bronze, Silver, and Gold training tables from PostgreSQL into the `hive-server` container by using Spark as the processing engine.

```text
PostgreSQL tables
      ↓ Spark JDBC read
Spark DataFrames
      ↓ Spark Parquet write
Parquet files in the Hive container
      ↓ Beeline registers table metadata
Hive Bronze, Silver, and Gold tables
```

The PostgreSQL database remains the source for this exercise. The Hive tables are derived copies that can be recreated by rerunning the migration.

### Important paths

| Purpose | Repository-relative path |
| --- | --- |
| Generated Bronze, Silver, and Gold CSV files | `docs/Training/Week3/2.1_hive_migration/tmp/data/` |
| Spark migration program | `docs/Training/Week3/2.1_hive_migration/spark_migration.py` |
| PostgreSQL CSV loader | `scripts/load-hive-migration-postgres.sh` |
| PostgreSQL setup SQL | `sql/hive-migration/` |
| Local PostgreSQL environment file | `infra/postgres/.env` |

### Step 1: Start at the repository root

These commands assume the terminal is at the `BigDataExample` repository root:

```bash
pwd
```

Expected ending:

```text
/VSCodeProjects/BigDataExample
```

If the terminal is currently in the migration directory, return to the repository root with:

```bash
cd ../../../..
```

### Step 2: Start PostgreSQL

```bash
docker compose \
  --env-file infra/postgres/.env \
  -f infra/postgres/compose.yml \
  up -d
```

Confirm that PostgreSQL is healthy:

```bash
docker ps --filter name=big-data-example-postgres
```

The expected container name is `big-data-example-postgres`.

### Step 3: Generate and load the PostgreSQL data

Regenerate the CSV fixtures when a fresh copy is needed:

```bash
python scripts/generate-hive-migration-csvs.py
```

Load the ten CSV files into the isolated `week3_hive_migration` PostgreSQL database:

```bash
./scripts/load-hive-migration-postgres.sh
```

This creates:

- One Bronze table: `bronze.sales_raw`
- One Silver table: `silver.sales_clean`
- Eight Gold tables: seven dimensions and `gold.fact_sales`

The loader recreates only the `bronze`, `silver`, and `gold` schemas inside `week3_hive_migration`. It does not reset `week3_hw` or `week3_medallion_lab`.

### Step 4: Start HiveServer2

Check whether the Hive container already exists:

```bash
docker ps -a --filter name=hive-server
```

If it exists but is stopped, start it:

```bash
docker start hive-server
```

If it does not exist, create it:

```bash
docker run -d \
  --name hive-server \
  -p 10000:10000 \
  -p 10002:10002 \
  -e SERVICE_NAME=hiveserver2 \
  apache/hive:4.0.1
```

The ports have different jobs:

| Port | Purpose |
| ---: | --- |
| `10000` | HiveServer2 JDBC/Beeline connections |
| `10002` | HiveServer2 web interface |

Confirm both containers are running:

```bash
docker ps --filter name=big-data-example-postgres
docker ps --filter name=hive-server
```

### Step 5: Load the PostgreSQL environment variables

The Spark script uses `os.getenv()` to read values from its process environment. `os.getenv()` does not open `.env` files itself, so the terminal must export the values before starting `spark-submit`.

From the repository root:

```bash
set -a
source infra/postgres/.env
set +a
```

- `set -a` tells Zsh to export variables assigned afterward.
- `source infra/postgres/.env` reads the PostgreSQL variables into the current shell.
- `set +a` turns automatic exporting back off.
- Exported variables are inherited by `spark-submit`, which passes them to the Python process.
- The password stays in the ignored local `.env` file instead of being hardcoded in Python.

### Step 6: Run the Spark migration

From the repository root:

```bash
spark-submit \
  --packages org.postgresql:postgresql:42.7.7 \
  docs/Training/Week3/2.1_hive_migration/spark_migration.py
```

`--packages org.postgresql:postgresql:42.7.7` downloads or reuses the PostgreSQL JDBC driver. JDBC stands for Java Database Connectivity. Spark runs on the JVM, so this driver provides the code Spark needs to communicate with PostgreSQL.

The same command can be run from inside `docs/Training/Week3/2.1_hive_migration/`, but the environment file then needs a path relative to that directory:

```bash
set -a
source ../../../../infra/postgres/.env
set +a

spark-submit \
  --packages org.postgresql:postgresql:42.7.7 \
  spark_migration.py
```

### What `spark_migration.py` does

For each of the ten source tables, the program performs these steps:

1. `spark.read.jdbc(...)` creates a lazy DataFrame plan for reading the PostgreSQL table.
2. `dataframe.count()` is an action that executes the JDBC read and records the PostgreSQL row count.
3. `dataframe.coalesce(1)` reduces this small training table to one output partition.
4. `dataframe.write.parquet(...)` materializes the DataFrame as a Parquet file in a temporary host directory.
5. `docker cp` copies the Parquet files into the Hive container's warehouse directory.
6. Beeline creates the matching Hive database and registers an external table pointing to those files.
7. Hive counts every destination table and the script compares those counts with PostgreSQL.
8. A mismatch raises an error; matching counts produce a success summary.
9. `spark.stop()` releases the Spark JVM, worker threads, temporary resources, and Spark UI port.

`coalesce(1)` is reasonable for these small fixtures because it makes the files easy to inspect. Large production tables should normally keep multiple partitions so Spark can write in parallel.

### Expected verification result

The final summary should contain:

```text
bronze.sales_raw: 2996 rows
silver.sales_clean: 2803 rows
gold.dim_customer: 122 rows
gold.dim_date: 245 rows
gold.dim_employee: 23 rows
gold.dim_office: 7 rows
gold.dim_order_status: 3 rows
gold.dim_product: 109 rows
gold.dim_product_category: 7 rows
gold.fact_sales: 2803 rows
All PostgreSQL and Hive row counts match.
```

### Step 7: Open Beeline and inspect Hive

Run this command at the Mac terminal prompt:

```bash
docker exec -it hive-server \
  beeline -u 'jdbc:hive2://localhost:10000/default'
```

After the prompt changes to this form, the terminal is inside Beeline:

```text
0: jdbc:hive2://localhost:10000/default>
```

Enter Hive SQL at the Beeline prompt:

```sql
SHOW DATABASES;
SHOW TABLES IN bronze;
SHOW TABLES IN silver;
SHOW TABLES IN gold;

SELECT COUNT(*) AS fact_rows
FROM gold.fact_sales;

SELECT SUM(sales_amount) AS total_sales
FROM gold.fact_sales;
```

Expected fact results:

```text
fact_rows  = 2803
total_sales = 1644043.79
```

Exit Beeline with:

```text
!quit
```

### Terminal commands compared with Beeline commands

| Prompt | Run here | Examples |
| --- | --- | --- |
| Mac terminal ending in `%` | Operating-system and Docker commands | `spark-submit`, `docker exec`, `cd`, `source` |
| Beeline ending in `>` | Hive SQL and Beeline commands | `SHOW DATABASES;`, `SELECT ...;`, `!quit` |

Do not enter `beeline -u ...` after already reaching the Beeline prompt. Hive will try to parse the word `beeline` as SQL. A `. . . >` prompt means Hive is waiting for the rest of an unfinished statement, usually because the statement has not reached a semicolon.

### Rerunning the migration

The migration is designed to be repeatable for this lesson. It replaces only the ten known table directories inside the Hive container, drops and recreates those external-table definitions, and verifies the counts again. It does not delete the PostgreSQL source tables.

### Current limitation: Hive persistence

The current `hive-server` quick-start container uses an embedded metastore and has no mounted persistent volume. Restarting the same container retains its writable layer, but deleting and recreating the container removes the Hive metadata and migrated files. A later production-style setup would use persistent warehouse storage and a shared external metastore.

### ETL or ELT?

This exercise is closest to ETL because Spark extracts tables from PostgreSQL, changes their storage representation to Parquet, and then loads them into Hive. An ELT version would first load raw source data into the destination system and perform most transformations there.
