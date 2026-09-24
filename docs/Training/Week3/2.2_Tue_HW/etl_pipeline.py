"""Read Bronze sales from PostgreSQL, clean them, and load Hive Silver."""

import os
import subprocess

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


# RUN THIS FILE:
# set -a makes variables loaded by source available to child processes such as spark-submit.
#  set -a
#  source infra/postgres/.env
#  set +a

#  spark-submit \
#  --packages org.postgresql:postgresql:42.7.7 \
#  docs/Training/Week3/2.2_Tue_HW/etl_pipeline.py


# CHECK HIVE CONTAINER:
#  docker ps --filter name=hive-server
#  docker exec hive-server beeline \
#    -u jdbc:hive2://localhost:10000/default \
#    -e "USE silver; SHOW TABLES; SELECT COUNT(*) FROM silver.sales_hw;"


# The password comes from infra/postgres/.env instead of this file.
postgres_password = os.getenv("POSTGRES_PASSWORD")
if not postgres_password:
    raise RuntimeError("Export the variables in infra/postgres/.env before spark-submit")

jdbc_url = "jdbc:postgresql://127.0.0.1:5432/week3_hive_migration"
jdbc_properties = {
    "user": os.getenv("POSTGRES_USER", "bigdata"),
    "password": postgres_password,
    "driver": "org.postgresql.Driver",
}

spark = SparkSession.builder.appName("TuesdayETLHomework").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# Extract the raw PostgreSQL table through JDBC.
source = spark.read.jdbc(
    url=jdbc_url,
    table="bronze.sales_raw",
    properties=jdbc_properties,
)

# Select the PostgreSQL columns that we want to preview before cleaning.
source_view = source.select(
    "order_number",
    "order_date",
    "order_status",
    "customer_id",
    "product_number",
    "unit_price",
    "quantity",
)
print("\nSOURCE DATA")
# Show 10 Bronze rows without shortening long values.
source_view.show(10, truncate=False)
# Show the column names and data types Spark received through JDBC.
source_view.printSchema()

source_count = source.count()
# Count a baseline set of missing required values in the raw source.
source_invalid_count = source.filter(
    F.col("order_date").isNull()
    | (F.trim("order_date") == "")
    | F.col("order_status").isNull()
    | (F.trim("order_status") == "")
    | F.col("customer_id").isNull()
    | (F.trim("customer_id") == "")
).count()

# Transformations:
# 1. Trim and standardize text.
# 2. Convert strings into dates and numbers.
# 3. Remove duplicate order/product rows.
# 4. Remove rows with missing or invalid required values.
cleaned = (
    source.select(
        "bronze_row_id",
        # col() creates a Spark expression that refers to a named DataFrame column.
        F.col("order_number")
            # cast() converts the value to the requested Spark data type.
            .cast("int")
            # alias() names the output of this expression.
            .alias("order_number"),
        # Trim whitespace, then parse the string using the expected year-month-day format.
        # A value that cannot be parsed becomes NULL and is removed by the later filter.
        F.to_date(
            F.trim("order_date"), "yyyy-MM-dd")
            .alias("order_date"),
        # lower() normalizes the text, and initcap() capitalizes the first letter of each word.
        F.initcap(
            F.lower(
                F.trim("order_status")))
                .alias("order_status"),
        # expr() lets us write a Spark SQL expression as a string.
        # try_cast converts valid IDs to integers and produces NULL for malformed IDs
        # instead of stopping the entire job with a conversion error.
        F.expr(
            "try_cast(trim(customer_id) AS INT)")
            .alias("customer_id"),
        F.trim("product_number")
            .alias("product_number"),
        F.col("unit_price")
            .cast("decimal(12,2)")
            .alias("unit_price"),
        F.col("quantity")
            .cast("int")
            .alias("quantity"),
    )
    # Keep one row for each order/product key and discard additional matching rows.
    # If matching rows contain different non-key values, Spark does not guarantee which one it keeps.
    .dropDuplicates(["order_number", "product_number"])
    # Keep only rows whose required fields passed the quality rules.
    .filter(
        F.col("order_date").isNotNull()
        & (F.length("order_status") > 0)
        & F.col("customer_id").isNotNull()
        & (F.col("unit_price") > 0)
        & (F.col("quantity") > 0)
    )
    # withColumn() returns a DataFrame with a new or replaced column; it does not create a table.
    .withColumn(
        "sales_amount",
        (F.col("quantity") * F.col("unit_price")).cast("decimal(14,2)"),
    )
    .withColumn("processed_at", F.current_timestamp())
    # Ask Spark to reuse this cleaned result. cache() is lazy; the count() below materializes it.
    .cache()
)

# count() is an action: it executes the lazy transformations and returns the cleaned row count.
cleaned_count = cleaned.count()
# Verify that none of the invalid values targeted by the filter remain. This should be zero.
cleaned_invalid_count = cleaned.filter(
    F.col("order_date").isNull()
    | (F.length("order_status") == 0)
    | F.col("customer_id").isNull()
    | (F.col("unit_price") <= 0)
    | (F.col("quantity") <= 0)
).count()


print("\nCLEANED DATA")
cleaned.orderBy("order_number", "product_number").show(10, truncate=False)
cleaned.printSchema()

print("VALIDATION")
print(f"Source rows:          {source_count}")
print(f"Cleaned rows:         {cleaned_count}")
print(f"Invalid source rows:  {source_invalid_count}")
print(f"Invalid cleaned rows: {cleaned_invalid_count}")

# Spark writes the cleaned data as Parquet.
# Overwrite makes reruns repeatable.
# coalesce(1) reduces this small result to one output partition and therefore one data file.
# A production-scale pipeline would usually retain multiple partitions for parallel writes.
parquet_dir = "/tmp/spark_etl_homework_sales_hw"
cleaned.coalesce(1).write.mode("overwrite").parquet(parquet_dir)

# Local Spark and Hive use separate filesystems, so Docker copies the Parquet
# file into the Hive container before Beeline registers the table.
# subprocess.run() asks Python to launch an operating-system command.
# This differs from SQLAlchemy text(), which represents a SQL statement for a database connection.
hive_dir = "/opt/hive/data/warehouse/silver.db/sales_hw"
subprocess.run(
    # Remove only the previous Hive data directory so a rerun cannot leave stale Parquet files.
    ["docker", "exec", "hive-server", "rm", "-rf", hive_dir],
    check=True,
)
subprocess.run(
    ["docker", "exec", "hive-server", "mkdir", "-p", hive_dir],
    check=True,
)
subprocess.run(
    ["docker", "cp", f"{parquet_dir}/.", f"hive-server:{hive_dir}"],
    check=True,
)

hive_sql = f"""
CREATE DATABASE IF NOT EXISTS silver;
DROP TABLE IF EXISTS silver.sales_hw;
CREATE EXTERNAL TABLE silver.sales_hw (
    bronze_row_id BIGINT,
    order_number INT,
    order_date DATE,
    order_status STRING,
    customer_id INT,
    product_number STRING,
    unit_price DECIMAL(12,2),
    quantity INT,
    sales_amount DECIMAL(14,2),
    processed_at TIMESTAMP
)
STORED AS PARQUET
LOCATION 'file://{hive_dir}';
SELECT COUNT(*) AS hive_rows FROM silver.sales_hw;
"""

# We do not need Docker's -it flags because this command is non-interactive.
# -u supplies Beeline's JDBC connection URL.
# --silent=true reduces informational output so the query results are easier to see.
# --showHeader=true displays column names in query results.
# -e executes the Hive SQL supplied by the next argument.
# check=True is a Python option, not a Beeline option. It stops the pipeline if the command fails.
subprocess.run(
    [
        "docker",
        "exec",
        "hive-server",
        "beeline",
        "-u",
        "jdbc:hive2://localhost:10000/default",
        "--silent=true",
        "--showHeader=true",
        "-e",
        hive_sql,
    ],
    check=True,
)

print("HIVE WRITE COMPLETED: silver.sales_hw")
spark.stop()
