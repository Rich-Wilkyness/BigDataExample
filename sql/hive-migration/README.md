# Hive migration PostgreSQL source

This setup loads the lesson CSV fixtures into a dedicated PostgreSQL database named `week3_hive_migration`. It does not modify `bigdata`, `week3_hw`, or `week3_medallion_lab`.

The database contains one Bronze table, one Silver table, and eight Gold tables. Spark can read these tables from PostgreSQL over JDBC before writing them to Hive.

## Load or reset the source database

Start the repository PostgreSQL service, then run the loader from the repository root:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml up -d
./scripts/load-hive-migration-postgres.sh
```

Rerunning the loader drops and recreates only the `bronze`, `silver`, and `gold` schemas inside `week3_hive_migration`.

## Inspect the result

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d week3_hive_migration
```

At the `week3_hive_migration=#` prompt:

```text
\conninfo
\dn
\dt bronze.*
\dt silver.*
\dt gold.*
SELECT COUNT(*) FROM gold.fact_sales;
```

## Spark JDBC connection

When Spark runs in another container on the PostgreSQL Compose network, use the Compose service name `postgres:5432`. When Spark runs directly on the host, use `127.0.0.1:5432` or the configured `POSTGRES_PORT`.

```text
jdbc:postgresql://postgres:5432/week3_hive_migration
```

A separately started Spark container must join the `big-data-example_default` Docker network before it can resolve `postgres`. The Hive container must also be reachable from Spark on a shared network before Spark can write to it.

The database user is `bigdata`. Read the password from the ignored `infra/postgres/.env` file; do not place it in source code.
