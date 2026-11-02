import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
import re
from pyspark.sql.functions import col, lit

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ["JOB_NAME", "BUCKET", "BATCH_ID"])

bucket = args["BUCKET"]
batch_id = args["BATCH_ID"]

if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", batch_id):
    raise ValueError("Invalid BATCH_ID")

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
spark.conf.set("spark.sql.session.timeZone", "UTC")


job = Job(glueContext)
job.init(args['JOB_NAME'], args)


silver_path = (
    f"s3://{bucket}/silver/citibike/"
    f"incremental_batches/batch_id={batch_id}/"
)

stations = spark.read.parquet(silver_path)

stations.printSchema()
stations.show(5, truncate=False)
print(f"Silver row count: {stations.count()}")

station_snapshot = stations.select(
    col("station_id").cast("string").alias("station_id"),
    col("snapshot_timestamp").cast("timestamp").alias("snapshot_timestamp"),
    col("station_name").cast("string").alias("station_name"),
    col("bikes_available").cast("long").alias("bikes_available"),
    col("ebikes_available").cast("long").alias("ebikes_available"),
    col("docks_available").cast("long").alias("docks_available"),
    col("capacity").cast("long").alias("capacity"),
    col("utilization_pct").cast("double").alias("utilization_pct"),
    col("is_empty").cast("boolean").alias("is_empty"),
    col("is_full").cast("boolean").alias("is_full"),
    col("is_operational").cast("boolean").alias("is_operational"),
)

station_snapshot = station_snapshot.withColumn("batch_id", lit(batch_id))

invalid_keys = station_snapshot.filter(
    "station_id IS NULL OR snapshot_timestamp IS NULL"
)

duplicate_keys = (
    station_snapshot
    .groupBy("station_id", "snapshot_timestamp")
    .count()
    .filter("count > 1")
)

if invalid_keys.limit(1).count() > 0:
    raise ValueError("Station ID and snapshot timestamp must not be null.")

if duplicate_keys.limit(1).count() > 0:
    raise ValueError("Duplicate station/snapshot pairs found.")

if station_snapshot.count() == 0:
    raise ValueError("Refusing an empty landing batch.")
if station_snapshot.filter(
    "bikes_available IS NULL OR ebikes_available IS NULL "
    "OR docks_available IS NULL OR capacity IS NULL"
).limit(1).count():
    raise ValueError("Required availability/capacity measures must not be null.")

print("Station/snapshot key validation passed.")

snapshot_dyf = DynamicFrame.fromDF(
    station_snapshot,
    glueContext,
    "station_snapshot",
)
snapshot_dyf.printSchema()

redshift_temp_path = f"s3://{bucket}/redshift-temp/citibike/incremental/"

glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=snapshot_dyf,
    catalog_connection="richard-citibike-redshift-connection",
    connection_options={
        "database": "dev",
        "dbtable": "public.richard_citibike_station_snapshot_landing",
        "aws_iam_role": (
            "arn:aws:iam::866934333672:"
            "role/RichardCitiBikeRedshiftRole"
        ),
    },
    redshift_tmp_dir=redshift_temp_path,
)


print("Redshift write completed.")

job.commit()
