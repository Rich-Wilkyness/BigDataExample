from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    explode,
    input_file_name,
    regexp_extract,
    to_timestamp,
    from_unixtime,
    when,
    round as spark_round
)

spark = (
    SparkSession.builder
    .appName("CitiBikeBronzeToSilver")
    .getOrCreate()
)

spark.conf.set("spark.sql.session.timeZone", "UTC")

BUCKET = "citi-bike-nyc-pipeline"

STATUS_PATH = (
    f"s3://{BUCKET}/bronze/citibike/station_status/"
)

INFO_PATH = (
    f"s3://{BUCKET}/bronze/citibike/station_information/"
)

OUTPUT_PATH = (
    f"s3://{BUCKET}/silver/citibike/glue_station_status/"
)


# =========================================================
# STATION STATUS
# =========================================================

status_raw = (
    spark.read
    .option("multiLine", "true")
    .json(STATUS_PATH)
    .withColumn("source_file", input_file_name())
)

print("RAW STATUS SCHEMA")
status_raw.printSchema()


# One JSON document contains an array of stations.
# Convert each station into an individual Spark row.

status = (
    status_raw
    .select(
        explode(col("data.stations")).alias("station"),
        col("source_file")
    )
)


# =========================================================
# Extract snapshot timestamp from our S3 filename
#
# station_status_20261007T204500Z.json
# =========================================================

status = (
    status
    .withColumn(
        "snapshot_string",
        regexp_extract(
            col("source_file"),
            r"station_status_(\d{8}T\d{6}Z)",
            1
        )
    )
    .withColumn(
        "snapshot_timestamp",
        to_timestamp(
            col("snapshot_string"),
            "yyyyMMdd'T'HHmmss'Z'"
        )
    )
)


# =========================================================
# Flatten the Citi Bike status structure
# =========================================================

status = (
    status
    .select(
        col("station.station_id").alias("station_id"),

        col("snapshot_timestamp"),

        col("station.num_bikes_available")
            .alias("bikes_available"),

        col("station.num_ebikes_available")
            .alias("ebikes_available"),

        col("station.num_bikes_disabled")
            .alias("bikes_disabled"),

        col("station.num_docks_available")
            .alias("docks_available"),

        col("station.num_docks_disabled")
            .alias("docks_disabled"),

        col("station.is_installed")
            .cast("boolean")
            .alias("is_installed"),

        col("station.is_renting")
            .cast("boolean")
            .alias("is_renting"),

        col("station.is_returning")
            .cast("boolean")
            .alias("is_returning"),

        col("station.last_reported")
            .alias("last_reported_epoch"),

        col("station.legacy_id")
            .alias("legacy_id")
    )
    .withColumn(
        "last_reported_timestamp",
        to_timestamp(
            from_unixtime(col("last_reported_epoch"))
        )
    )
)


# =========================================================
# STATION INFORMATION
# =========================================================

info_raw = (
    spark.read
    .option("multiLine", "true")
    .json(INFO_PATH)
)

print("RAW STATION INFORMATION SCHEMA")
info_raw.printSchema()


info = (
    info_raw
    .select(
        explode(col("data.stations")).alias("station")
    )
    .select(
        col("station.station_id")
            .alias("station_id"),

        col("station.name")
            .alias("station_name"),

        col("station.short_name")
            .alias("short_name"),

        col("station.lat")
            .alias("latitude"),

        col("station.lon")
            .alias("longitude"),

        col("station.region_id")
            .alias("region_id"),

        col("station.capacity")
            .alias("capacity"),

        col("station.station_type")
            .alias("station_type"),

        col("station.has_kiosk")
            .alias("has_kiosk")
    )

    # We ingest station_information repeatedly,
    # so keep only one metadata record per station.
    .dropDuplicates(["station_id"])
)


# =========================================================
# JOIN STATUS + STATION METADATA
# =========================================================

silver = (
    status
    .join(
        info,
        on="station_id",
        how="left"
    )
)


# =========================================================
# DERIVED BUSINESS COLUMNS
# =========================================================

silver = (
    silver

    # Percentage of usable station capacity occupied by bikes.
    .withColumn(
        "utilization_pct",
        when(
            col("capacity") > 0,
            spark_round(
                col("bikes_available") /
                col("capacity") * 100,
                2
            )
        )
    )

    # Useful operational flags.
    .withColumn(
        "is_empty",
        col("bikes_available") == 0
    )

    .withColumn(
        "is_full",
        col("docks_available") == 0
    )

    .withColumn(
        "is_operational",
        col("is_installed") &
        col("is_renting") &
        col("is_returning")
    )
)


# =========================================================
# VALIDATION
# =========================================================

print("SILVER SCHEMA")
silver.printSchema()

record_count = silver.count()

print(
    f"SILVER RECORD COUNT: {record_count}"
)

print("SAMPLE SILVER RECORDS")

silver.select(
    "station_id",
    "station_name",
    "snapshot_timestamp",
    "capacity",
    "bikes_available",
    "ebikes_available",
    "docks_available",
    "utilization_pct",
    "is_empty",
    "is_full",
    "is_operational"
).show(
    20,
    truncate=False
)


# =========================================================
# WRITE SILVER
# =========================================================

(
    silver.write
    .mode("append")
    .parquet(OUTPUT_PATH)
)

print(
    f"Silver dataset written to {OUTPUT_PATH}"
)

spark.stop()
