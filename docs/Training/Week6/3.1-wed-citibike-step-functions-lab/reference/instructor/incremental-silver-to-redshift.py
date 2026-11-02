"""Load ONE immutable Silver v2 batch to Redshift landing (AWS Glue PySpark).
Required: --JOB_NAME --BATCH_ID. Bookmarks disabled.
Landing table must exist. Re-running this job appends duplicate landing rows;
MERGE SQL deduplicates by station_id and snapshot_timestamp.
"""
import re
import sys
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "BATCH_ID"])
batch_id = args["BATCH_ID"]
if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", batch_id):
    raise ValueError("Invalid BATCH_ID")
bucket = "citi-bike-nyc-pipeline"
path = f"s3://{bucket}/silver/citibike/incremental_batches_v2/batch_id={batch_id}/"
sc = SparkContext.getOrCreate()
glue = GlueContext(sc)
spark = glue.spark_session
spark.conf.set("spark.sql.session.timeZone", "UTC")
job = Job(glue)
job.init(args["JOB_NAME"], args)

# Explicit batch path, no bookmarks, no whole-history reads.
raw = spark.read.parquet(path)
cols = ["station_id", "snapshot_timestamp", "station_name", "bikes_available",
        "ebikes_available", "docks_available", "capacity", "utilization_pct",
        "is_empty", "is_full", "is_operational"]
missing = set(cols) - set(raw.columns)
if missing:
    raise RuntimeError(f"Missing Silver columns: {sorted(missing)}")
rows = raw.select(
    F.col("station_id").cast("string").alias("station_id"),
    F.col("snapshot_timestamp").cast("timestamp").alias("snapshot_timestamp"),
    F.col("station_name").cast("string").alias("station_name"),
    F.col("bikes_available").cast("int").alias("bikes_available"),
    F.col("ebikes_available").cast("int").alias("ebikes_available"),
    F.col("docks_available").cast("int").alias("docks_available"),
    F.col("capacity").cast("int").alias("capacity"),
    F.col("utilization_pct").cast("double").alias("utilization_pct"),
    F.col("is_empty").cast("boolean").alias("is_empty"),
    F.col("is_full").cast("boolean").alias("is_full"),
    F.col("is_operational").cast("boolean").alias("is_operational"),
).filter(F.col("station_id").isNotNull() & F.col("snapshot_timestamp").isNotNull())
rows = rows.dropDuplicates(["station_id", "snapshot_timestamp"])
rows = rows.withColumn("batch_id", F.lit(batch_id))
count = rows.count()
print(f"BATCH={batch_id}; REDSHIFT LANDING ROWS={count}")
if count == 0:
    raise RuntimeError("Empty batch: not loading")
glue.write_dynamic_frame.from_jdbc_conf(
    frame=DynamicFrame.fromDF(rows, glue, "batch_rows"),
    catalog_connection="citibike-redshift-connection",
    connection_options={"database": "dev", "dbtable": "public.citibike_station_snapshot_landing_v2"},
    redshift_tmp_dir=f"s3://{bucket}/redshift-temp/citibike/incremental-v2/",
    transformation_ctx="redshift_landing_batch_v2",
)
job.commit()
print("REDSHIFT LANDING LOAD COMPLETE; MERGE AND GOLD REFRESH STILL REQUIRED")

