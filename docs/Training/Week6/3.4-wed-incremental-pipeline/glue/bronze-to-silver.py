import sys
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, input_file_name, regexp_extract,
    to_timestamp, from_unixtime, when, round as spark_round,
)

from awsglue.utils import getResolvedOptions
import re
from datetime import datetime, timedelta, timezone
import boto3


args = getResolvedOptions(
    sys.argv,
    ["BUCKET", "BATCH_ID", "WINDOW_START", "WINDOW_END", "MANIFEST_KEY"],
)

bucket = args["BUCKET"]
batch_id = args["BATCH_ID"]
window_start = args["WINDOW_START"]
window_end = args["WINDOW_END"]

# Arguments must look like: 2026-10-16T15:00:00Z
def parse_utc(value):
    return datetime.strptime(
        value, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)


start = parse_utc(window_start)
end = parse_utc(window_end)

if end <= start:
    raise ValueError("WINDOW_END must be after WINDOW_START")

if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", batch_id):
    raise ValueError("Invalid BATCH_ID")

s3 = boto3.client("s3", region_name="us-east-2")
# Preparation froze these exact inputs before either Glue job starts.
manifest_key = args["MANIFEST_KEY"]
expected_prefix = f"control/citibike/incremental/batches/{batch_id}/"
if manifest_key != expected_prefix + "manifest.json":
    raise ValueError("Manifest key does not match batch")
with s3.get_object(Bucket=bucket, Key=manifest_key)["Body"] as body:
    manifest = json.load(body)
prepared = manifest["result"]
if (manifest["version"] != 1 or prepared["batch_id"] != batch_id
        or prepared["window_start"] != window_start
        or prepared["window_end"] != window_end):
    raise ValueError("Prepared manifest does not match job arguments")
status_uris = manifest["status_uris"]
info_uri = manifest["metadata_uri"]
uri_prefix = f"s3://{bucket}/{expected_prefix}"
if (not status_uris or len(status_uris) > 128
        or any(not uri.startswith(uri_prefix + "status/station_status_") for uri in status_uris)
        or info_uri != uri_prefix + "station_information.json"):
    raise ValueError("Manifest inputs are outside this frozen batch")
print(f"BATCH_ID={batch_id}; frozen_files={len(status_uris)}; manifest={manifest_key}")
print(f"Station metadata: {info_uri}")

# Create Spark
spark = (
    SparkSession.builder.appName("CitiBikeBronzeToSilver")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
base = f"s3://{bucket}"

status_raw = (
    spark.read.option("multiLine", "true")
    .json(status_uris)
    .withColumn("source_file", input_file_name())
)
status_raw.printSchema()
status = status_raw.select(
    explode(col("data.stations")).alias("station"), col("source_file")
)
status = (
    status.withColumn(
        "snapshot_string",
        regexp_extract(col("source_file"), r"station_status_(\d{8}T\d{6}Z)", 1),
    )
    .withColumn(
        "snapshot_timestamp",
        to_timestamp(col("snapshot_string"), "yyyyMMdd'T'HHmmss'Z'"),
    )
    .select(
        col("station.station_id").cast("string").alias("station_id"),
        col("snapshot_timestamp"),
        col("station.num_bikes_available").cast("int").alias("bikes_available"),
        col("station.num_ebikes_available").cast("int").alias("ebikes_available"),
        col("station.num_bikes_disabled").cast("int").alias("bikes_disabled"),
        col("station.num_docks_available").cast("int").alias("docks_available"),
        col("station.num_docks_disabled").cast("int").alias("docks_disabled"),
        col("station.is_installed").cast("boolean").alias("is_installed"),
        col("station.is_renting").cast("boolean").alias("is_renting"),
        col("station.is_returning").cast("boolean").alias("is_returning"),
        col("station.last_reported").cast("long").alias("last_reported_epoch"),
        col("station.legacy_id").alias("legacy_id"),
    )
    .withColumn(
        "last_reported_timestamp", to_timestamp(from_unixtime(col("last_reported_epoch")))
    )
)

# Collapse identical observations.
status = status.dropDuplicates()

# Different values for the same business key require investigation.
conflicting_keys = (
    status.groupBy("station_id", "snapshot_timestamp")
    .count()
    .filter(col("count") > 1)
)

if conflicting_keys.limit(1).count():
    raise RuntimeError("Conflicting station observations in this batch")

info_raw = (
    spark.read.option("multiLine", "true")
    .json(info_uri)
)
info_raw.printSchema()
info = (
    info_raw.select(explode(col("data.stations")).alias("station"))
    .select(
        col("station.station_id").cast("string").alias("station_id"),
        col("station.name").cast("string").alias("station_name"),
        col("station.short_name").cast("string").alias("short_name"),
        col("station.lat").cast("double").alias("latitude"),
        col("station.lon").cast("double").alias("longitude"),
        col("station.region_id").cast("int").alias("region_id"),
        col("station.capacity").cast("int").alias("capacity"),
        col("station.station_type").alias("station_type"),
        col("station.has_kiosk").alias("has_kiosk"),
    )
    .dropDuplicates(["station_id"])
)

silver = (
    status.join(info, on="station_id", how="left")
    .withColumn(
        "utilization_pct",
        when(col("capacity") > 0,
             spark_round(col("bikes_available") / col("capacity") * 100, 2)),
    )
    .withColumn("is_empty", col("bikes_available") == 0)
    .withColumn("is_full", col("docks_available") == 0)
    .withColumn("is_operational",
                col("is_installed") & col("is_renting") & col("is_returning"))
)
silver.printSchema()
print(f"SILVER RECORD COUNT: {silver.count()}")
silver.select(
    "station_id", "station_name", "snapshot_timestamp", "last_reported_timestamp",
    "capacity", "bikes_available", "ebikes_available", "docks_available",
    "utilization_pct", "is_empty", "is_full", "is_operational",
).show(20, truncate=False)

output_path = f"{base}/silver/citibike/incremental_batches/batch_id={batch_id}/"
silver.write.mode("errorifexists").parquet(output_path)
print(f"Silver dataset written to {output_path}")

# Verify the published Parquet, rather than only the pre-write DataFrame.
published = spark.read.parquet(output_path)
published_count = published.count()
invalid_keys = published.filter(
    col("station_id").isNull()
    | (col("station_id") == "")
    | col("snapshot_timestamp").isNull()
).count()
duplicate_keys = published.groupBy("station_id", "snapshot_timestamp").count().filter(
    col("count") > 1
).count()
unmatched_metadata = published.filter(col("station_name").isNull()).count()
negative_counts = published.filter(
    (col("bikes_available") < 0)
    | (col("docks_available") < 0)
    | (col("capacity") < 0)
).count()
print(
    f"SILVER READBACK: rows={published_count}, invalid_keys={invalid_keys}, "
    f"duplicate_keys={duplicate_keys}, unmatched_metadata={unmatched_metadata}, "
    f"negative_counts={negative_counts}"
)
if (published_count != prepared["expected_rows"] or published_count == 0
        or invalid_keys or duplicate_keys or unmatched_metadata or negative_counts):
    raise RuntimeError("Silver read-back failed; inspect the printed quality counts.")

spark.stop()
