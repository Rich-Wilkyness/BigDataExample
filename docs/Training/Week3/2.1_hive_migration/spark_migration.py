"""Migrate the training tables from PostgreSQL into the Hive container.

Run from this directory after loading the PostgreSQL environment variables:

    set -a
    source ../../../../infra/postgres/.env
    set +a
    spark-submit --packages org.postgresql:postgresql:42.7.7 spark_migration.py

The PostgreSQL package gives Spark the JDBC driver it needs to read PostgreSQL.
The script then uses the local Docker command to copy Spark-created Parquet
files into the running Hive container and Beeline to register Hive tables.

This is a local training workflow. The current Hive container has no persistent
volume, so deleting the container also deletes its Hive metadata and data.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    BinaryType,
    BooleanType,
    ByteType,
    DataType,
    DateType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    LongType,
    ShortType,
    StringType,
    TimestampNTZType,
    TimestampType,
)


# These are the ten PostgreSQL tables created by
# scripts/load-hive-migration-postgres.sh. The order keeps the Gold dimensions
# before the Gold fact table, which makes the migration easier to follow.
TABLES_TO_MIGRATE = (
    ("bronze", "sales_raw"),
    ("silver", "sales_clean"),
    ("gold", "dim_customer"),
    ("gold", "dim_date"),
    ("gold", "dim_employee"),
    ("gold", "dim_office"),
    ("gold", "dim_order_status"),
    ("gold", "dim_product"),
    ("gold", "dim_product_category"),
    ("gold", "fact_sales"),
)

# The container and path can be overridden with environment variables, but the
# defaults match the Hive container used by this lesson.
HIVE_CONTAINER = os.getenv("MIGRATION_HIVE_CONTAINER", "hive-server")
HIVE_JDBC_URL = os.getenv(
    "MIGRATION_HIVE_JDBC_URL",
    "jdbc:hive2://localhost:10000/default",
)
HIVE_WAREHOUSE_DIR = os.getenv(
    "MIGRATION_HIVE_WAREHOUSE_DIR",
    "/opt/hive/data/warehouse",
)


def require_environment_variable(name: str) -> str:
    """Return a required environment variable or explain how to provide it."""

    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Load infra/postgres/.env before running spark-submit."
        )
    return value


def validate_identifier(value: str) -> None:
    """Allow only the simple schema and table names defined in this lesson."""

    if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL or path identifier: {value!r}")


def run_command(
    command: list[str],
    *,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a host command and show useful output if it fails."""

    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout)
        if error.stderr:
            print(error.stderr)
        raise


def verify_hive_container() -> None:
    """Fail early when Docker or the expected Hive container is unavailable."""

    if shutil.which("docker") is None:
        raise RuntimeError("The docker command is not available on PATH.")

    result = run_command(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Running}}",
            HIVE_CONTAINER,
        ],
        capture_output=True,
    )
    if result.stdout.strip() != "true":
        raise RuntimeError(f"Hive container {HIVE_CONTAINER!r} is not running.")


def spark_type_to_hive(data_type: DataType) -> str:
    """Translate the Spark DataFrame type into a Hive column type."""

    if isinstance(data_type, StringType):
        return "STRING"
    if isinstance(data_type, BooleanType):
        return "BOOLEAN"
    if isinstance(data_type, ByteType):
        return "TINYINT"
    if isinstance(data_type, ShortType):
        return "SMALLINT"
    if isinstance(data_type, IntegerType):
        return "INT"
    if isinstance(data_type, LongType):
        return "BIGINT"
    if isinstance(data_type, FloatType):
        return "FLOAT"
    if isinstance(data_type, DoubleType):
        return "DOUBLE"
    if isinstance(data_type, DecimalType):
        return f"DECIMAL({data_type.precision},{data_type.scale})"
    if isinstance(data_type, DateType):
        return "DATE"
    if isinstance(data_type, (TimestampType, TimestampNTZType)):
        return "TIMESTAMP"
    if isinstance(data_type, BinaryType):
        return "BINARY"

    raise TypeError(f"No Hive mapping for Spark type {data_type.simpleString()!r}")


def build_hive_ddl(
    database: str,
    table: str,
    spark_schema,
    container_table_dir: str,
) -> str:
    """Create the Hive SQL that points a table at Spark's Parquet files."""

    validate_identifier(database)
    validate_identifier(table)

    column_definitions = ",\n    ".join(
        f"`{field.name}` {spark_type_to_hive(field.dataType)}"
        for field in spark_schema.fields
    )
    table_name = f"`{database}`.`{table}`"
    location = f"file://{container_table_dir}"

    # EXTERNAL means Hive owns the table definition, while the Parquet files
    # remain at the explicit LOCATION. Dropping the table does not delete them.
    return f"""
CREATE DATABASE IF NOT EXISTS `{database}`;
DROP TABLE IF EXISTS {table_name};
CREATE EXTERNAL TABLE {table_name} (
    {column_definitions}
)
STORED AS PARQUET
LOCATION '{location}';
""".strip()


def run_beeline(hive_sql: str) -> subprocess.CompletedProcess[str]:
    """Send Hive SQL to HiveServer2 through Beeline inside the container."""

    return run_command(
        [
            "docker",
            "exec",
            HIVE_CONTAINER,
            "beeline",
            "-u",
            HIVE_JDBC_URL,
            "--silent=true",
            "--showHeader=false",
            "--outputformat=tsv2",
            "--force=false",
            "-e",
            hive_sql,
        ],
        capture_output=True,
    )


def read_hive_row_counts() -> dict[str, int]:
    """Query every migrated Hive table and return its row count."""

    count_queries = [
        f"SELECT '{database}.{table}', COUNT(*) FROM `{database}`.`{table}`"
        for database, table in TABLES_TO_MIGRATE
    ]
    # Separate statements keep each COUNT(*) in its own small Hive/Tez job.
    # Combining all ten with UNION ALL exceeds the counter limit in this small
    # training container even though the tables themselves are small.
    result = run_beeline(";\n".join(count_queries) + ";")

    counts: dict[str, int] = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split("\t")
        if (
            len(parts) == 2
            and re.fullmatch(
                r"(?:bronze|silver|gold)\.[a-z0-9_]+",
                parts[0],
            )
        ):
            counts[parts[0]] = int(parts[1])

    expected_names = {
        f"{database}.{table}" for database, table in TABLES_TO_MIGRATE
    }
    if set(counts) != expected_names:
        print(result.stdout)
        raise RuntimeError("Could not read all migrated table counts from Beeline.")

    return counts


def main() -> None:
    """Read PostgreSQL, create Parquet files, register Hive tables, and verify."""

    # os.getenv() reads the environment inherited by this Python process. It
    # does not open .env files itself, which is why the run instructions source
    # infra/postgres/.env before spark-submit starts Python.
    postgres_host = os.getenv("MIGRATION_POSTGRES_HOST", "127.0.0.1")
    postgres_port = os.getenv(
        "MIGRATION_POSTGRES_PORT",
        os.getenv("POSTGRES_PORT", "5432"),
    )
    postgres_database = os.getenv(
        "MIGRATION_POSTGRES_DB",
        "week3_hive_migration",
    )
    postgres_user = os.getenv(
        "MIGRATION_POSTGRES_USER",
        os.getenv("POSTGRES_USER", "bigdata"),
    )
    postgres_password = require_environment_variable("POSTGRES_PASSWORD")

    jdbc_url = (
        f"jdbc:postgresql://{postgres_host}:{postgres_port}/{postgres_database}"
    )
    jdbc_properties = {
        "user": postgres_user,
        "password": postgres_password,
        "driver": "org.postgresql.Driver",
    }

    verify_hive_container()

    # getOrCreate() starts the Spark driver. No data has moved yet; Spark reads
    # and transforms data lazily until an action such as count() or write runs.
    spark = (
        SparkSession.builder
        .appName("PostgresToHiveMigration")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    postgres_counts: dict[str, int] = {}
    hive_ddl_statements: list[str] = []

    try:
        # TemporaryDirectory gives Spark a host-side staging location. Python
        # removes it automatically after the migration finishes or fails.
        with tempfile.TemporaryDirectory(
            prefix="spark_hive_migration_"
        ) as staging_dir:
            staging_root = Path(staging_dir)

            for database, table in TABLES_TO_MIGRATE:
                full_table_name = f"{database}.{table}"
                print(f"\nReading PostgreSQL table {full_table_name}...")

                # Spark JDBC turns the PostgreSQL table into a DataFrame. This
                # defines the plan; count() below is the first action that
                # actually asks PostgreSQL for all rows.
                dataframe = spark.read.jdbc(
                    url=jdbc_url,
                    table=full_table_name,
                    properties=jdbc_properties,
                )
                row_count = dataframe.count()
                postgres_counts[full_table_name] = row_count
                print(f"  PostgreSQL rows: {row_count}")
                print(f"  Spark schema: {dataframe.schema.simpleString()}")

                local_table_dir = staging_root / database / table

                # These lesson tables are small, so coalesce(1) makes one
                # Parquet data file per table. Large production tables should
                # normally retain multiple partitions for parallelism.
                (
                    dataframe.coalesce(1)
                    .write
                    .mode("overwrite")
                    .parquet(str(local_table_dir))
                )

                container_table_dir = (
                    f"{HIVE_WAREHOUSE_DIR}/{database}.db/{table}"
                )

                # Rerunning the migration replaces only this known table path.
                # The identifier validation above prevents arbitrary paths.
                validate_identifier(database)
                validate_identifier(table)
                run_command(
                    [
                        "docker",
                        "exec",
                        HIVE_CONTAINER,
                        "rm",
                        "-rf",
                        container_table_dir,
                    ]
                )
                run_command(
                    [
                        "docker",
                        "exec",
                        HIVE_CONTAINER,
                        "mkdir",
                        "-p",
                        container_table_dir,
                    ]
                )
                run_command(
                    [
                        "docker",
                        "cp",
                        f"{local_table_dir}/.",
                        f"{HIVE_CONTAINER}:{container_table_dir}",
                    ]
                )

                hive_ddl_statements.append(
                    build_hive_ddl(
                        database,
                        table,
                        dataframe.schema,
                        container_table_dir,
                    )
                )
                print(f"  Copied Parquet files to {container_table_dir}")

            # One Beeline call creates the databases and registers all ten
            # external tables in Hive's metastore.
            print("\nRegistering external tables in Hive...")
            run_beeline("\n\n".join(hive_ddl_statements))

            # The final check reads each Hive table through HiveServer2 and
            # compares it with the count Spark read from PostgreSQL.
            print("Verifying PostgreSQL and Hive row counts...")
            hive_counts = read_hive_row_counts()
            mismatches = {
                name: (postgres_counts[name], hive_counts.get(name))
                for name in postgres_counts
                if postgres_counts[name] != hive_counts.get(name)
            }
            if mismatches:
                raise RuntimeError(f"Row-count mismatches: {mismatches}")

            print("\nMigration completed successfully:")
            for name, count in postgres_counts.items():
                print(f"  {name}: {count} rows")
            print("All PostgreSQL and Hive row counts match.")
    finally:
        # Always stop Spark so its JVM, worker threads, and port 4040 are
        # released even when a database, Docker, or Hive operation fails.
        spark.stop()


if __name__ == "__main__":
    main()
