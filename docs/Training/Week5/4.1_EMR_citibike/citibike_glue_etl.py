import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, input_file_name, regexp_extract,
    to_timestamp, from_unixtime, when, round as spark_round,
)

from awsglue.utils import getResolvedOptions

bucket = getResolvedOptions(sys.argv, ["BUCKET"])["BUCKET"]
spark = (
    SparkSession.builder.appName("CitiBikeBronzeToSilver")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
base = f"s3://{bucket}"

status_raw = (
    spark.read.option("multiLine", "true")
    .json(f"{base}/bronze/citibike/station_status/")
    .withColumn("source_file", input_file_name())
)
status_raw.printSchema()
status = status_raw.select(
    # col("data.stations") selects the array. explode(...) produces a row for each item. 
    # .alias("station") names the resulting column, which still contains a nested station object.
    # if the file contains 2,519 stations, how many rows would you expect immediately after flattening that array?
    # 2,519 rows
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
        col("station.station_id").alias("station_id"),
        col("snapshot_timestamp"),
        col("station.num_bikes_available").alias("bikes_available"),
        col("station.num_ebikes_available").alias("ebikes_available"),
        col("station.num_bikes_disabled").alias("bikes_disabled"),
        col("station.num_docks_available").alias("docks_available"),
        col("station.num_docks_disabled").alias("docks_disabled"),
        col("station.is_installed").cast("boolean").alias("is_installed"),
        col("station.is_renting").cast("boolean").alias("is_renting"),
        col("station.is_returning").cast("boolean").alias("is_returning"),
        col("station.last_reported").alias("last_reported_epoch"),
        col("station.legacy_id").alias("legacy_id"),
    )
    .withColumn(
        "last_reported_timestamp", to_timestamp(from_unixtime(col("last_reported_epoch")))
    )
)

info_raw = (
    spark.read.option("multiLine", "true")
    .json(f"{base}/bronze/citibike/station_information/")
)
info_raw.printSchema()
info = (
    info_raw.select(explode(col("data.stations")).alias("station"))
    .select(
        col("station.station_id").alias("station_id"),
        col("station.name").alias("station_name"),
        col("station.short_name").alias("short_name"),
        col("station.lat").alias("latitude"),
        col("station.lon").alias("longitude"),
        col("station.region_id").alias("region_id"),
        col("station.capacity").alias("capacity"),
        col("station.station_type").alias("station_type"),
        col("station.has_kiosk").alias("has_kiosk"),
    )
    .dropDuplicates(["station_id"])
)

silver = (
    # status contains changing values, such as available bikes. 
    # info contains station details, such as name and capacity

    # A left join keeps every status row, even if no matching metadata exists. 
    # For an unmatched station, the added metadata columns are null.
    # If status has 2,519 rows and info has at most one matching row per station, how many rows should this left join produce?
    # 2,519, Multiple matches could multiply the joined rows.
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

output_path = f"{base}/silver/citibike/glue_station_status/"
silver.write.mode("overwrite").parquet(output_path)
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
if published_count == 0 or invalid_keys or duplicate_keys or negative_counts:
    raise RuntimeError("Silver read-back failed; inspect the printed quality counts.")

spark.stop()