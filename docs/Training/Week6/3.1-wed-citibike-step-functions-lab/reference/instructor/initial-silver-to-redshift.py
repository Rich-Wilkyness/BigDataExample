
import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions

from pyspark.context import SparkContext
from pyspark.sql.functions import col

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
spark.conf.set("spark.sql.session.timeZone", "UTC")

job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# 1. Read Silver Parquet using Glue's DynamicFrame API
silver = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": [
            "s3://citi-bike-nyc-pipeline/silver/citibike/glue_station_status/"
        ],
        "recurse": True
    },
    format="parquet",
    transformation_ctx="silver_source"
)

print("Silver schema:")
silver.printSchema()

# 2. Select and cast fields to match Redshift
df = silver.toDF().select(
    col("station_id").cast("string").alias("station_id"),
    col("snapshot_timestamp").cast("timestamp").alias("snapshot_timestamp"),
    col("station_name").cast("string").alias("station_name"),
    col("bikes_available").cast("int").alias("bikes_available"),
    col("ebikes_available").cast("int").alias("ebikes_available"),
    col("docks_available").cast("int").alias("docks_available"),
    col("capacity").cast("int").alias("capacity"),
    col("utilization_pct").cast("double").alias("utilization_pct"),
    col("is_empty").cast("boolean").alias("is_empty"),
    col("is_full").cast("boolean").alias("is_full"),
    col("is_operational").cast("boolean").alias("is_operational")
)

df = df.filter(
    col("station_id").isNotNull()
    & col("snapshot_timestamp").isNotNull()
)

# Limit the first demonstration to 100 rows
df = df.limit(100)

print("Rows to load:", df.count())

# 3. Convert back to Glue DynamicFrame
gold = DynamicFrame.fromDF(df, glueContext, "gold_records")

# 4. Load Redshift using Glue's native connector
glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=gold,
    catalog_connection="citibike-redshift-connection",
    connection_options={
        "database": "dev",
        "dbtable": "public.citibike_station_snapshot"
    },
    redshift_tmp_dir=(
        "s3://citi-bike-nyc-pipeline/redshift-temp/citibike/"
    ),
    transformation_ctx="redshift_sink"
)

job.commit()
print("Redshift load completed successfully.")

