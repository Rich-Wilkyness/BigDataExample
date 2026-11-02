import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

# The load now has three steps:
#    - Before loading: create an empty staging table matching your destination’s structure, and clear leftover staging rows.
#    - Load: copy the incoming rows into staging.
#    - After loading: merge staging into the destination, then clear staging.

# Glue supports SQL preactions and postactions around its COPY operation. 
# The adjacent Python strings produce SQL without embedded newlines

# REMOVE DUPLICATES is Redshift’s simplified merge mode. 
# Matching station/snapshot pairs are updated; new pairs are inserted. 
# It requires matching column order and compatible types, which is why staging uses LIKE your existing table. 

# Keep Maximum concurrency = 1, since this job uses one shared staging table

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)


silver_path = (
    "s3://richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an/"
    "silver/citibike/glue_station_status/"
)

stations = spark.read.parquet(silver_path)

stations.printSchema()
stations.show(5, truncate=False)
print(f"Silver row count: {stations.count()}")

station_snapshot = stations.select(
    "station_id",
    "snapshot_timestamp",
    "station_name",
    "bikes_available",
    "ebikes_available",
    "docks_available",
    "capacity",
    "utilization_pct",
    "is_empty",
    "is_full",
    "is_operational",
)

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

print("Station/snapshot key validation passed.")

snapshot_dyf = DynamicFrame.fromDF(
    station_snapshot,
    glueContext,
    "station_snapshot",
)

redshift_temp_path = (
    "s3://richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an/"
    "redshift-temp/citibike/"
)

glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=snapshot_dyf,
    catalog_connection="richard-citibike-redshift-connection",
    connection_options={
        "database": "dev",
        "dbtable": "public.citibike_station_snapshot_stage",
        "aws_iam_role": (
            "arn:aws:iam::866934333672:"
            "role/RichardCitiBikeRedshiftRole"
        ),
        "preactions": (
            "CREATE TABLE IF NOT EXISTS "
            "public.citibike_station_snapshot_stage "
            "(LIKE public.citibike_station_snapshot); "
            "DELETE FROM public.citibike_station_snapshot_stage;"
        ),
        "postactions": (
            "BEGIN; "
            "MERGE INTO public.citibike_station_snapshot "
            "USING public.citibike_station_snapshot_stage AS incoming "
            "ON citibike_station_snapshot.station_id = incoming.station_id "
            "AND citibike_station_snapshot.snapshot_timestamp "
            "= incoming.snapshot_timestamp "
            "REMOVE DUPLICATES; "
            "DELETE FROM public.citibike_station_snapshot_stage; "
            "END;"
        ),
    },
    redshift_tmp_dir=redshift_temp_path,
)

print("Redshift write completed.")

job.commit()