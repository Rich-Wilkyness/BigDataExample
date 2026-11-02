# Richard follow-along adaptation; see README.md and reference/provenance.json.
# The instructor source is preserved separately under reference/instructor/.
"""Citi Bike incremental Bronze -> isolated Silver batch (AWS Glue PySpark).

Required args: --JOB_NAME --BATCH_ID --START_AT_UTC --END_BEFORE_UTC
START_AT_UTC is inclusive, END_BEFORE_UTC exclusive, both UTC ISO Z.
The batch is immutable: refuses to write if batch prefix already has objects.
Uses snapshot timestamp in filename, not S3 LastModified. Late-arriving older
snapshots require an overlapping catch-up batch (Redshift MERGE deduplicates).
"""
import re
import sys
from datetime import datetime, timezone
import boto3
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window

args = getResolvedOptions(sys.argv, ["JOB_NAME", "BATCH_ID", "START_AT_UTC", "END_BEFORE_UTC", "BUCKET"])
batch_id = args["BATCH_ID"]
if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", batch_id):
    raise ValueError("BATCH_ID must contain 1-64 alphanumeric, underscore or hyphen characters")
def parse_utc(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", s):
        raise ValueError("Timestamp must be YYYY-MM-DDTHH:MM:SSZ")
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
start = parse_utc(args["START_AT_UTC"])
end = parse_utc(args["END_BEFORE_UTC"])
if end <= start:
    raise ValueError("END_BEFORE_UTC must be after START_AT_UTC")

bucket = args["BUCKET"]
status_prefix = "bronze/citibike/station_status/"
info_prefix = "bronze/citibike/station_information/"
output_prefix = f"silver/citibike/v2-lab/batches/batch_id={batch_id}/"
output_uri = f"s3://{bucket}/{output_prefix}"
s3 = boto3.client("s3", region_name="us-east-2")
if s3.list_objects_v2(Bucket=bucket, Prefix=output_prefix, MaxKeys=1).get("KeyCount", 0):
    raise RuntimeError(f"Batch output already exists; refusing overwrite: {output_uri}")

status_re = re.compile(r"station_status_(\d{8}T\d{6}Z)\.json$")
info_re = re.compile(r"station_information_(\d{8}T\d{6}Z)\.json$")
status_keys = []
latest_info_key = None
latest_info_dt = None
paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=bucket, Prefix=status_prefix):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        match = status_re.search(key)
        if match:
            ts = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            if start <= ts < end:
                status_keys.append(key)
for page in paginator.paginate(Bucket=bucket, Prefix=info_prefix):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        match = info_re.search(key)
        if match:
            ts = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            if ts < end and (latest_info_dt is None or (ts, key) > (latest_info_dt, latest_info_key)):
                latest_info_dt, latest_info_key = ts, key

print(f"BATCH_ID={batch_id}; START_AT={start}; END_BEFORE={end}")
print(f"Selected {len(status_keys)} station-status JSON objects")
print(f"Metadata file: {latest_info_key}")
if not status_keys:
    raise RuntimeError("No Bronze station-status files in requested interval. No batch written.")
if not latest_info_key:
    raise RuntimeError("No station-information file found before end boundary")

sc = SparkContext.getOrCreate()
glue = GlueContext(sc)
spark = glue.spark_session
spark.conf.set("spark.sql.session.timeZone", "UTC")
job = Job(glue)
job.init(args["JOB_NAME"], args)

# Spark accepts explicit S3 URI lists. No bookmark is needed for this immutable batch.
status_uris = [f"s3://{bucket}/{key}" for key in sorted(status_keys)]
status_docs = (spark.read.option("multiLine", "true").json(status_uris)
               .withColumn("source_file", F.input_file_name())
               .withColumn("filename_text", F.regexp_extract("source_file", r"station_status_(\d{8}T\d{6}Z)\.json", 1))
               .withColumn("snapshot_timestamp", F.to_timestamp("filename_text", "yyyyMMdd'T'HHmmss'Z'")))
status = (status_docs
    .select(F.explode("data.stations").alias("station"), "snapshot_timestamp", "source_file")
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
    .filter(F.col("station_id").isNotNull() & F.col("snapshot_timestamp").isNotNull()))
w = Window.partitionBy("station_id", "snapshot_timestamp").orderBy(F.col("source_file").desc())
status = (status.withColumn("_rn", F.row_number().over(w)).filter("_rn=1")
          .drop("_rn", "source_file")
          .withColumn("last_reported_timestamp", F.to_timestamp(F.from_unixtime("last_reported_epoch"))))

info_docs = spark.read.option("multiLine", "true").json(f"s3://{bucket}/{latest_info_key}")
info = (info_docs.select(F.explode("data.stations").alias("station"))
    .select(
        F.col("station.station_id").cast("string").alias("station_id"),
        F.col("station.name").cast("string").alias("station_name"),
        F.col("station.short_name").cast("string").alias("short_name"),
        F.col("station.lat").cast("double").alias("latitude"),
        F.col("station.lon").cast("double").alias("longitude"),
        F.col("station.region_id").cast("string").alias("region_id"),
        F.col("station.capacity").cast("int").alias("capacity"),
        F.col("station.station_type").cast("string").alias("station_type"),
        F.col("station.has_kiosk").cast("boolean").alias("has_kiosk")))
info = info.dropDuplicates(["station_id"])
silver = (status.join(F.broadcast(info), "station_id", "left")
    .withColumn("utilization_pct", F.when(F.col("capacity") > 0, F.round(F.col("bikes_available") / F.col("capacity") * 100, 2)))
    .withColumn("is_empty", F.col("bikes_available") == 0)
    .withColumn("is_full", F.col("docks_available") == 0)
    .withColumn("is_operational", F.col("is_installed") & F.col("is_renting") & F.col("is_returning"))
    .withColumn("snapshot_date", F.to_date("snapshot_timestamp")))
count = silver.count()
print(f"SILVER BATCH ROWS={count}; OUTPUT={output_uri}")
if count == 0:
    raise RuntimeError("No station rows produced; refusing empty batch")
(silver.write.mode("errorifexists").option("compression", "snappy")
 .partitionBy("snapshot_date").parquet(output_uri))
# Verify published files before any downstream loader becomes eligible.
published = spark.read.parquet(output_uri)
if published.limit(1).count() == 0:
    raise RuntimeError("Published Silver is empty")
if published.filter("station_id IS NULL OR station_id = '' OR snapshot_timestamp IS NULL").limit(1).count():
    raise RuntimeError("Published Silver has invalid keys")
if published.groupBy("station_id", "snapshot_timestamp").count().filter("count > 1").limit(1).count():
    raise RuntimeError("Published Silver has duplicate keys")
print("SILVER READBACK VALIDATION PASSED")
job.commit()
print("INCREMENTAL SILVER BATCH COMPLETE")

