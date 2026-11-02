"""Citi Bike Bronze -> Silver v2 historical backfill (AWS Glue 5 / PySpark).

Run as a ONE-TIME backfill with Glue bookmarks disabled. The output prefix is
replaced on each run. Keep the old Silver prefix untouched.

Optional Glue job argument:
  --CUTOFF_UTC 2026-10-13T20:30:00Z

The cutoff is EXCLUSIVE, based on the UTC timestamp embedded in S3 filenames.
For a consistent backfill, stop/avoid concurrent writes to the relevant input
prefixes while running, or use a frozen snapshot of the input objects.
"""

import re
import sys
from datetime import datetime, timezone

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

def optional_arg(name):
    flag = f"--{name}"
    if flag not in sys.argv:
        return None
    index = sys.argv.index(flag)
    if index + 1 >= len(sys.argv):
        raise ValueError(f"Missing value for {flag}")
    return sys.argv[index + 1]

cutoff_arg = optional_arg("CUTOFF_UTC")
cutoff = None
if cutoff_arg:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", cutoff_arg):
        raise ValueError("CUTOFF_UTC must be YYYY-MM-DDTHH:MM:SSZ")
    cutoff = datetime.strptime(cutoff_arg, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

sc = SparkContext.getOrCreate()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
spark.conf.set("spark.sql.session.timeZone", "UTC")
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

BUCKET = "citi-bike-nyc-pipeline"
STATUS_PATH = f"s3://{BUCKET}/bronze/citibike/station_status/"
INFO_PATH = f"s3://{BUCKET}/bronze/citibike/station_information/"
OUTPUT_PATH = f"s3://{BUCKET}/silver/citibike/station_snapshots_v2/"

# Filename timestamps are UTC. Avoid relying on object modification dates.
STATUS_PATTERN = r"station_status_(\d{8}T\d{6}Z)\.json"
INFO_PATTERN = r"station_information_(\d{8}T\d{6}Z)\.json"
TIMESTAMP_FORMAT = "yyyyMMdd'T'HHmmss'Z'"


def read_documents(path, pattern):
    docs = (
        spark.read.option("multiLine", "true")
        .json(path)
        .withColumn("source_file", F.input_file_name())
        .withColumn("filename_timestamp_text", F.regexp_extract("source_file", pattern, 1))
        .withColumn("file_timestamp", F.to_timestamp("filename_timestamp_text", TIMESTAMP_FORMAT))
    )
    docs = docs.filter(F.col("file_timestamp").isNotNull())
    if cutoff:
        # Compare parsed UTC timestamps; exclusive cutoff.
        docs = docs.filter(F.col("file_timestamp") < F.lit(cutoff.replace(tzinfo=None)))
    return docs


print(f"STATUS INPUT: {STATUS_PATH}")
print(f"INFO INPUT: {INFO_PATH}")
print(f"SILVER OUTPUT: {OUTPUT_PATH}")
print(f"EXCLUSIVE CUTOFF UTC: {cutoff_arg or 'NONE'}")

status_docs = read_documents(STATUS_PATH, STATUS_PATTERN)
info_docs = read_documents(INFO_PATH, INFO_PATTERN)

status = (
    status_docs
    .select(F.explode("data.stations").alias("station"),
            F.col("file_timestamp").alias("snapshot_timestamp"),
            "source_file")
    .select(
        F.col("station.station_id").cast("string").alias("station_id"),
        "snapshot_timestamp", "source_file",
        F.col("station.num_bikes_available").cast("int").alias("bikes_available"),
        F.col("station.num_ebikes_available").cast("int").alias("ebikes_available"),
        F.col("station.num_bikes_disabled").cast("int").alias("bikes_disabled"),
        F.col("station.num_docks_available").cast("int").alias("docks_available"),
        F.col("station.num_docks_disabled").cast("int").alias("docks_disabled"),
        F.col("station.is_installed").cast("boolean").alias("is_installed"),
        F.col("station.is_renting").cast("boolean").alias("is_renting"),
        F.col("station.is_returning").cast("boolean").alias("is_returning"),
        F.col("station.last_reported").cast("long").alias("last_reported_epoch"),
        F.col("station.legacy_id").cast("string").alias("legacy_id"),
    )
    .filter(F.col("station_id").isNotNull() & F.col("snapshot_timestamp").isNotNull())
)

# Deterministically choose one record for each logical station snapshot.
# File path breaks ties if the same snapshot appears in more than one object.
status_window = Window.partitionBy("station_id", "snapshot_timestamp").orderBy(
    F.col("source_file").desc()
)
status = (
    status.withColumn("_rn", F.row_number().over(status_window))
    .filter(F.col("_rn") == 1).drop("_rn", "source_file")
    .withColumn("last_reported_timestamp", F.to_timestamp(F.from_unixtime("last_reported_epoch")))
)

info = (
    info_docs
    .select(F.explode("data.stations").alias("station"),
            F.col("file_timestamp").alias("metadata_timestamp"),
            "source_file")
    .select(
        F.col("station.station_id").cast("string").alias("station_id"),
        F.col("station.name").cast("string").alias("station_name"),
        F.col("station.short_name").cast("string").alias("short_name"),
        F.col("station.lat").cast("double").alias("latitude"),
        F.col("station.lon").cast("double").alias("longitude"),
        F.col("station.region_id").cast("string").alias("region_id"),
        F.col("station.capacity").cast("int").alias("capacity"),
        F.col("station.station_type").cast("string").alias("station_type"),
        F.col("station.has_kiosk").cast("boolean").alias("has_kiosk"),
        "metadata_timestamp", "source_file",
    )
    .filter(F.col("station_id").isNotNull())
)

# Latest metadata as of the cutoff (not point-in-time metadata history).
info_window = Window.partitionBy("station_id").orderBy(
    F.col("metadata_timestamp").desc(), F.col("source_file").desc()
)
info = (
    info.withColumn("_rn", F.row_number().over(info_window))
    .filter(F.col("_rn") == 1)
    .drop("_rn", "metadata_timestamp", "source_file")
)

silver = (
    status.join(F.broadcast(info), on="station_id", how="left")
    .withColumn(
        "utilization_pct",
        F.when(F.col("capacity") > 0,
               F.round(F.col("bikes_available") / F.col("capacity") * 100, 2))
    )
    .withColumn("is_empty", F.col("bikes_available") == 0)
    .withColumn("is_full", F.col("docks_available") == 0)
    .withColumn("is_operational",
                F.col("is_installed") & F.col("is_renting") & F.col("is_returning"))
    .withColumn("snapshot_date", F.to_date("snapshot_timestamp"))
)

print("SILVER SCHEMA:")
silver.printSchema()
print("SILVER RECORD COUNT:", silver.count())
silver.select("station_id", "snapshot_timestamp", "station_name", "bikes_available",
              "capacity", "utilization_pct").show(20, truncate=False)

# WARNING: Overwrites the entire v2 output prefix. Never use as an incremental job.
(
    silver.write.mode("overwrite")
    .option("compression", "snappy")
    .partitionBy("snapshot_date")
    .parquet(OUTPUT_PATH)
)

job.commit()
print(f"BACKFILL COMPLETED: {OUTPUT_PATH}")

