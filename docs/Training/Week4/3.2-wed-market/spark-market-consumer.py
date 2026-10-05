import json
import os
import time
from datetime import datetime, timezone

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    to_timestamp,
    current_timestamp,
    lit,
    unix_millis
)
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    StringType,
    DoubleType,
    IntegerType
)


# ============================================================
# Configuration
# ============================================================

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "market_ticks"

OUTPUT_FILE = "/tmp/spark-market.jsonl"
CHECKPOINT_DIR = "/tmp/spark-market-checkpoint"

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
        col("partition").alias("kafka_partition"),
        col("offset").alias("kafka_offset"),
        col("timestamp").alias("kafka_broker_ts"),
        col("value").cast("string").alias("json")
    )
    .withColumn(
        "data",
        from_json(col("json"), schema)
    )
    .select(
        "kafka_partition",
        "kafka_offset",
        "kafka_broker_ts",
        "data.*"
    )
)


# ============================================================
# Microbatch processing
# ============================================================

def process_batch(batch_df, batch_id):

    if batch_df.isEmpty():
        return

    # --------------------------------------------------------
    # ONE timestamp is deliberately assigned to this batch.
    #
    # This makes the microbatch behavior obvious in the
    # dashboard: many records will acquire approximately the
    # same processing timestamp.
    # --------------------------------------------------------

    batch_processed_ts = datetime.now(timezone.utc)

    processed = (
        batch_df
        .withColumn(
            "processed_ts",
            lit(batch_processed_ts)
        )
        .withColumn(
            "engine",
            lit("spark")
        )
        .withColumn(
            "batch_id",
            lit(int(batch_id))
        )
        .withColumn(
            "exchange_timestamp",
            to_timestamp("exchange_ts")
        )
        .withColumn(
            "kafka_timestamp",
            to_timestamp("kafka_ts")
        )
        .withColumn(
            "processing_latency_ms",
            unix_millis(
                col("processed_ts")
            )
            -
            unix_millis(
                col("kafka_timestamp")
            )
        )
        .withColumn(
            "end_to_end_latency_ms",
            unix_millis(
                col("processed_ts")
            )
            -
            unix_millis(
                col("exchange_timestamp")
            )
        )
    )

    # Sort only for human-readable demo output.
    rows = (
        processed
        .orderBy("sequence")
        .collect()
    )

    # --------------------------------------------------------
    # Append this microbatch to the dashboard feed
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "a",
        buffering=1
    ) as f:

        for row in rows:

            record = row.asDict()

            # Convert Spark/Python datetime objects to strings.

            for field in [
                "kafka_broker_ts",
                "processed_ts",
                "exchange_timestamp",
                "kafka_timestamp"
            ]:

                if record.get(field) is not None:
                    record[field] = (
                        record[field].isoformat()
                    )

            f.write(
                json.dumps(
                    record,
                    default=str
                )
                + "\n"
            )

    count = len(rows)

    if count:

        first_sequence = rows[0]["sequence"]
        last_sequence = rows[-1]["sequence"]

        print(
            f"\n"
            f"SPARK MICRO-BATCH {batch_id}\n"
            f"Records: {count}\n"
            f"Sequence: "
            f"{first_sequence} -> {last_sequence}\n"
            f"Processed: "
            f"{batch_processed_ts.isoformat()}\n"
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
print(f"Output: {OUTPUT_FILE}")
print()
print(
    "Watch for groups of records appearing every "
    "2 seconds."
)
print()


query = (
    ticks.writeStream
    .foreachBatch(process_batch)
    .option(
        "checkpointLocation",
        CHECKPOINT_DIR
    )
    .trigger(
        processingTime=TRIGGER_INTERVAL
    )
    .start()
)


query.awaitTermination()


