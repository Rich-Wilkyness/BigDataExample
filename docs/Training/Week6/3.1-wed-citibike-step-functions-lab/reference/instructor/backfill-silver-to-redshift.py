"""One-time Citi Bike Silver v2 -> Redshift Serverless staging backfill.

Run with Glue bookmarks DISABLED. Destination table must exist and be empty.
Do not schedule this job or run it concurrently with other loaders.
"""
import sys
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.window import Window

BUCKET = "citi-bike-nyc-pipeline"
SILVER_PATH = f"s3://{BUCKET}/silver/citibike/station_snapshots_v2/"
REDSHIFT_CONNECTION = "citibike-redshift-connection"
REDSHIFT_DATABASE = "dev"
REDSHIFT_TABLE = "public.citibike_station_snapshot_v2"
REDSHIFT_TEMP = f"s3://{BUCKET}/redshift-temp/citibike/backfill-v2/"

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext.getOrCreate()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
spark.conf.set("spark.sql.session.timeZone", "UTC")
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

print(f"Reading Silver v2: {SILVER_PATH}")
source = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [SILVER_PATH], "recurse": True},
    format="parquet",
    transformation_ctx="silver_v2_backfill_source",
)
raw = source.toDF()
required = [
    "station_id", "snapshot_timestamp", "station_name", "bikes_available",
    "ebikes_available", "docks_available", "capacity", "utilization_pct",
    "is_empty", "is_full", "is_operational",
]
missing = [c for c in required if c not in raw.columns]
if missing:
    raise ValueError(f"Silver v2 is missing required columns: {missing}")

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

# Backfill v2 is expected to be unique already; this provides an additional guard.
# For conflicting duplicate records, prefer the row with the most non-null fields,
# then use stable column ordering as a deterministic tie-breaker.
score = sum(F.when(F.col(c).isNotNull(), 1).otherwise(0) for c in required[2:])
rows = rows.withColumn("_completeness", score)
window = Window.partitionBy("station_id", "snapshot_timestamp").orderBy(
    F.col("_completeness").desc(),
    *[F.col(c).asc_nulls_last() for c in required[2:]],
)
rows = (rows.withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1)
        .drop("_rank", "_completeness"))

rows = rows.cache()
count = rows.count()
print(f"BACKFILL ROW COUNT: {count}")
if count == 0:
    raise RuntimeError("No valid Silver v2 rows found; refusing an empty backfill")

stats = rows.agg(
    F.min("snapshot_timestamp").alias("earliest"),
    F.max("snapshot_timestamp").alias("latest"),
    F.countDistinct("station_id").alias("stations"),
).first()
print(f"Earliest snapshot: {stats['earliest']}")
print(f"Latest snapshot: {stats['latest']}")
print(f"Distinct stations: {stats['stations']}")
print("Rows by snapshot date:")
rows.groupBy(F.to_date("snapshot_timestamp").alias("snapshot_date")) \
    .count().orderBy("snapshot_date").show(100, truncate=False)

print(f"Writing {count} rows to {REDSHIFT_DATABASE}.{REDSHIFT_TABLE}")
# IMPORTANT: This connector appends. Create and verify an EMPTY target table
# before the first run; do not rerun without clearing it in a controlled manner.
glue_context.write_dynamic_frame.from_jdbc_conf(
    frame=DynamicFrame.fromDF(rows, glue_context, "redshift_backfill_v2_rows"),
    catalog_connection=REDSHIFT_CONNECTION,
    connection_options={"database": REDSHIFT_DATABASE, "dbtable": REDSHIFT_TABLE},
    redshift_tmp_dir=REDSHIFT_TEMP,
    transformation_ctx="redshift_backfill_v2_sink",
)
job.commit()
rows.unpersist()
print("Silver v2 -> Redshift v2 historical backfill completed.")

