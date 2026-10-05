import json
import os
import time
from datetime import datetime, timezone

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    StringType,
    DoubleType,
    IntegerType
)


# Keep the supplied dashboard consumers separate.

# Use ../spark-market-consumer.py as a reference for Spark setup, the input
# schema, reading market_ticks, and parsing Kafka's JSON value.

# TODO: Read continuously from Kafka and parse the JSON.
# TODO: Group by symbol and calculate the six required output columns.
# TODO: Continuously display the updated results.
# Optional bonus: use exchange_ts for event-time windows.
#
# Important: doing an aggregation only inside foreachBatch would calculate
# statistics for each separate batch. Consider how your query will maintain
# results across incoming batches.

# ============================================================
# Configuration
# ============================================================

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "market_ticks"

CHECKPOINT_DIR = "/tmp/market-aggregation-spark-checkpoint"

# Deliberately large enough that students can SEE microbatches.
TRIGGER_INTERVAL = "2 seconds"


# ============================================================
# Spark
# ============================================================

spark = (
    SparkSession.builder
    .master("local[*]")
    .appName("Spark Market Streaming Demo")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")


# ============================================================
# Input schema
# ============================================================

schema = StructType([
    StructField("sequence", LongType(), True),
    StructField("symbol", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("size", IntegerType(), True),
    StructField("side", StringType(), True),

    StructField("exchange_ts", StringType(), True),
    StructField("api_ts", StringType(), True),
    StructField("kafka_ts", StringType(), True),

    StructField("simulated_network_ms", IntegerType(), True)
])


# ============================================================
# Kafka source
# ============================================================

raw = (
    spark.readStream
    .format("kafka")
    .option(
        "kafka.bootstrap.servers",
        KAFKA_BOOTSTRAP
    )
    .option(
        "subscribe",
        KAFKA_TOPIC
    )
    .option(
        "startingOffsets",
        "latest"
    )
    .load()
)


# ============================================================
# Parse Kafka JSON
# ============================================================

ticks = (
    raw
    .select(
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
        F.col("timestamp").alias("kafka_broker_ts"),
        F.col("value").cast("string").alias("json")
    )
    .withColumn(
        "data",
        F.from_json(F.col("json"), schema)
    )
    .select(
        "kafka_partition",
        "kafka_offset",
        "kafka_broker_ts",
        "data.*"
    )
)

# ============================================================
# Aggregate
# ============================================================

market_stats = ticks.groupBy("symbol").agg(
    F.count("*").alias("number_of_trades"),
    F.avg("price").alias("average_price"),
    F.min("price").alias("minimum_price"),
    F.max("price").alias("maximum_price"),
    F.sum("size").alias("total_volume")
)


# ============================================================
# Start streaming
# ============================================================

print()
print("=" * 60)
print("SPARK STRUCTURED STREAMING")
print("=" * 60)
print()
print(f"Kafka topic: {KAFKA_TOPIC}")
print(f"Trigger: {TRIGGER_INTERVAL}")
print()
print(
    "Watch for groups of records appearing every "
    "2 seconds."
)
print()


query = (
    market_stats.writeStream
    .format("console")
    .outputMode("complete") # Display the entire accumulated result table each update
    # .foreachBatch(process_batch)
    .option(
        "checkpointLocation",
        CHECKPOINT_DIR
    )
    .option("truncate", "false") # show full table
    .trigger(
        processingTime=TRIGGER_INTERVAL
    )
    .start()
)


query.awaitTermination()

