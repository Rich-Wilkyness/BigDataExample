import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, input_file_name, regexp_extract,
    to_timestamp, from_unixtime, when, round as spark_round,
)

bucket = sys.argv[1]
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

output_path = f"{base}/silver/citibike/station_status/"
silver.write.mode("overwrite").parquet(output_path)
print(f"Silver dataset written to {output_path}")
spark.stop()